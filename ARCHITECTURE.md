# SearchAssistant – Arkkitehtuurikuvaus

## RAG + Function Calling + LaTeX-renderöinti

Tämä dokumentti kuvaa, miten järjestelmä yhdistää tietokantahaun (RAG),
kielimallin (Azure OpenAI) ja deterministiset laskentafunktiot (Python)
siten, että käyttäjä saa aina matemaattisesti oikeat vastaukset ja
kaavat piirtyvät käyttöliittymässä oppikirjatasoisena matematiikkana.

---

## 1. Yleiskuva (System Overview)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Selain (Client)                          │
│  index.html ─ KaTeX auto-render ─ session sidebar ─ POST       │
└──────────┬──────────────────────────────────────────────────────┘
           │  HTTP POST /ask  { session_id, question }
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    FastAPI  (api/rag_api.py)                     │
│                                                                  │
│  1. load session summary  → sessions-taulu                       │
│  2. embed_query(q)        → BAAI/bge-m3 vektori                  │
│  3. fetch_matches()       → pgvector cosine-similarity haku      │
│  4. system_prompt         → konteksti + summary + ohjeet         │
│  5. AzureOpenAI.chat      → vastaus TAI tool_call                │
│  6. tool dispatch         → calc/surface_treatment.py            │
│  7. AzureOpenAI.chat      → lopullinen vastaus (sis. LaTeX)      │
│  8. save Q+A to messages  → messages-taulu                       │
│  9. summarize session     → LLM-kutsu #2 → sessions.summary     │
│ 10. return JSON           → { answer, sources[], session_id }    │
└──────┬──────────┬───────────────┬────────────┬───────────────────┘
       │          │               │            │
       ▼          ▼               ▼            ▼
┌──────────┐ ┌──────────────┐ ┌────────┐ ┌─────────────────────────┐
│ pgvector │ │ Azure OpenAI │ │sessions│ │ calc/surface_treatment.py│
│documents │ │ gpt-35-turbo │ │messages│ │ (Python-funktiot)        │
└──────────┘ └──────────────┘ └────────┘ └─────────────────────────┘
```

---

## 2. Komponentit

### 2.1 Tietokanta – PostgreSQL + pgvector

| Ominaisuus       | Arvo                              |
|------------------|-----------------------------------|
| Image            | `ankane/pgvector:latest`          |
| Taulu            | `public.documents`                |
| Sarakkeet        | `id, source_url, title, license, language, content, embedding (vector)` |
| Indeksi          | cosine-similarity (`<=>`)         |
| Embedding-malli  | `BAAI/bge-m3` (1024-dim)          |

Materiaalit on chunkattu (`data/chunks.jsonl`) ja indeksoitu
(`scripts/embed_and_index.py`). Kukin chunk on yksi rivi taulussa.

### 2.2 API-palvelin – FastAPI (`api/rag_api.py`)

Keskeiset reitit:

| Reitti      | Tehtävä                                    |
|-------------|--------------------------------------------|
| `GET /`     | Palauttaa `static/index.html`              |
| `POST /ask` | RAG + LLM + Function Calling + sessiomuisti |
| `GET /sessions` | Listaa aiemmat sessiot (tiivistelmät)   |
| `GET /sessions/{id}` | Hakee session historian            |
| `DELETE /sessions/{id}` | Poistaa session                  |
| `GET /search` | Pelkkä vektorihaku ilman LLM:ää          |
| `GET /test-ask` | Testireitti kovakoodatulla LaTeX-vastauksella |
| `GET /healthz` | Terveyskontrolli                         |

### 2.3 Laskentamoduuli – `calc/surface_treatment.py`

Deterministiset Python-funktiot, jotka kielimalli kutsuu
Function Calling -mekanismilla. **LLM ei laske itse.**

| Funktio                          | Kaava                                    | Palautusarvo          |
|----------------------------------|------------------------------------------|-----------------------|
| `faraday_mass_calculation`       | $m = \frac{I \cdot t \cdot M}{z \cdot F}$ | `mass_g`, `calculation_steps` (LaTeX) |
| `faraday_thickness_calculation`  | $d = \frac{m}{\rho \cdot A}$             | `thickness_um`, `calculation_steps` (LaTeX) |
| `current_density_calculation`    | $J = \frac{I}{A}$                        | `current_density_a_dm2`, `calculation_steps` (LaTeX) |

**Jokainen funktio palauttaa `dict`-objektin, joka sisältää:**
- Numeerisen tuloksen (tarkka luku)
- `calculation_steps` – valmis LaTeX-merkkijono, jossa on kaava,
  arvot sijoitettuna ja lopputulos (esim. `$$ m \approx 1.1856 \text{ g} $$`)

### 2.4 Kielimalli – Azure OpenAI

| Parametri               | Arvo                                          |
|-------------------------|-----------------------------------------------|
| Endpoint                | `https://trainer-breefie-openai.openai.azure.com/` |
| Deployment              | `gpt-35-turbo`                                |
| API-versio              | `2024-02-15-preview`                          |
| Autentikointi           | API Key (ympäristömuuttuja)                   |

### 2.5 Käyttöliittymä – `static/index.html`

| Komponentti     | Teknologia / kirjasto                      |
|-----------------|--------------------------------------------|
| Kaava-renderöinti | [KaTeX 0.16.9](https://katex.org/) auto-render |
| XSS-suojaus     | `textContent` (ei `innerHTML` vastaustekstille) |
| Tuetut erottimet | `$...$`, `$$...$$`, `\(...\)`, `\[...\]`  |
| Tyyli           | Tumma teema (CSS custom properties)         |

---

## 3. Tietovirta (Flow) – Askel askeleelta

### 3.1 Peruskysymys (ei laskentaa)

```
Käyttäjä: "Mitä on anodisointi?"

1. Selain → GET /ask?q=Mitä on anodisointi?
2. API: embed_query("Mitä on anodisointi?") → [0.023, -0.118, ...]  (1024-dim vektori)
3. API: SELECT ... FROM documents ORDER BY embedding <=> ? LIMIT 5
4. API: Kootaan system_prompt:
         "Olet pintakäsittelyn asiantuntija. LÄHTEET: [5 parasta osumaa]"
5. API → Azure OpenAI:
         messages = [system, user("Mitä on anodisointi?")]
         tools = [faraday_mass, faraday_thickness, current_density]
         tool_choice = "auto"
6. Azure OpenAI: Ei tarvitse työkaluja → palauttaa suoran tekstivastauksen
7. API → Selain:  { answer: "Anodisointi on...", sources: [...] }
8. Selain: bubble.textContent = answer
9. Selain: renderMathInElement(bubble)  → (ei kaavoja → ei muutosta)
```

### 3.2 Laskukysymys (Function Calling)

```
Käyttäjä: "Laske kuinka paljon kuparia saostuu 10A virralla 2 tunnissa"

1–4. Sama kuin yllä (embedding, pgvector-haku, kontekstin rakennus)

5. API → Azure OpenAI:
         messages = [system, user], tools = [...], tool_choice = "auto"

6. Azure OpenAI vastaa TOOL CALL:lla (ei tekstiä):
         tool_calls: [{
           name: "faraday_mass_calculation",
           arguments: { current_a: 10, time_s: 7200,
                        molar_mass: 63.546, electrons: 2 }
         }]

7. API: Suorittaa Python-funktion:
         st.faraday_mass_calculation(current_a=10, time_s=7200,
                                     molar_mass=63.546, electrons=2)
         → { mass_g: 2.371,
             calculation_steps: "Lasketaan massa...\n$$ m = ... $$" }

8. API → Azure OpenAI (2. pyyntö):
         messages = [system, user, assistant(tool_call), tool(result)]
         → Malli muotoilee lopullisen vastauksen sisällyttäen
           calculation_steps LaTeX-merkkijonon

9. API → Selain:  { answer: "Kuparia saostuu...\n$$ m ≈ 2.371 g $$",
                     sources: [...] }

10. Selain: bubble.textContent = answer
11. Selain: renderMathInElement(bubble)
           → KaTeX tunnistaa $$...$$ ja \[...\] blokit
           → Piirtää matemaattiset kaavat oppikirjamuotoon
```

---

## 4. Tietomallit

### 4.1 API Response (`AskResponse`)

```json
{
  "answer": "Kuparia saostuu...\n$$ m \\approx 2.371 \\text{ g} $$",
  "sources": [
    {
      "id": "https://example.com#c12",
      "score": 0.87,
      "content": "Faraday discovered in 1833...",
      "source_url": "https://example.com",
      "title": "LibreTexts – Electrolytic Cells",
      "license": "CC-BY",
      "language": "en"
    }
  ]
}
```

### 4.2 Laskufunktion palautusarvo (esim. `faraday_mass_calculation`)

```json
{
  "mass_g": 2.3714,
  "calculation_steps": "Lasketaan massa Faradayn lailla:\n$$ m = \\frac{I \\cdot t \\cdot M}{z \\cdot F} $$\n\nSijoitetaan arvot:\n$$ m = \\frac{10 \\cdot 7200 \\cdot 63.546}{2 \\cdot 96485} $$\n\nTulos:\n$$ m \\approx 2.3714 \\text{ g} $$"
}
```

### 4.3 OpenAI Tools -skeema (esimerkki yhdestä työkalusta)

```json
{
  "type": "function",
  "function": {
    "name": "faraday_mass_calculation",
    "description": "Laskee saostuneen aineen massan Faradayn elektrolyysilain avulla.",
    "parameters": {
      "type": "object",
      "properties": {
        "current_a":  { "type": "number",  "description": "Sähkövirta (A)" },
        "time_s":     { "type": "number",  "description": "Aika (s)" },
        "molar_mass": { "type": "number",  "description": "Moolimassa (g/mol)" },
        "electrons":  { "type": "integer", "description": "Elektronien lkm (z)" }
      },
      "required": ["current_a", "time_s", "molar_mass", "electrons"]
    }
  }
}
```

---

## 5. Uuden kaavan lisääminen (ylläpito-ohje)

Uuden laskukaavan lisääminen vaatii muutoksen **kolmeen tiedostoon**:

### Vaihe 1: Python-funktio → `calc/surface_treatment.py`

```python
def uusi_kaava(param_a: float, param_b: float) -> dict:
    """
    Kuvaus: Mitä kaava laskee.
    Kaava: X = param_a / param_b
    """
    result = param_a / param_b
    latex = f"$$ X = \\frac{{{param_a}}}{{{param_b}}} = {result:.4f} $$"
    return {"result": result, "calculation_steps": latex}
```

**Nyrkkisäännöt:**
- Parametrien nimet sisältävät yksikön: `current_a`, `time_s`, `area_dm2`
- Palauta aina `dict` jossa avain `calculation_steps` (LaTeX-merkkijono)
- Käytä `$$ ... $$` block-display-kaavoja ja `$ ... $` inline-kaavoja
- Docstring kertoo mallille mitä funktio tekee

### Vaihe 2: Tool-skeema → `api/rag_api.py` (`tools`-lista)

Lisää `tools`-listaan uusi JSON-skeema, joka kuvaa funktion
parametrit ja kuvauksen kielimallille (ks. kohta 4.3).

### Vaihe 3: Tool dispatch → `api/rag_api.py` (tool execution loop)

Lisää uusi `elif`-haara tool execution -silmukkaan:

```python
elif func_name == "uusi_kaava":
    tool_result = st.uusi_kaava(**args)
```

**Ei tarvita:**
- Dockerin uudelleenrakennusta (volume mount `./calc:/app/calc`)
- Frontendin muutoksia (KaTeX renderöi kaiken LaTeXin automaattisesti)

---

## 6. LaTeX-renderöinnin kriittinen polku (Frontend)

```
API JSON response
       │
       │  data.answer = "Teksti...\n$$ kaava $$\nLisää..."
       ▼
  bubble.textContent = data.answer
       │
       │  DOM sisältää nyt RAAKAA TEKSTIÄ,
       │  takakenoviivat (\) ovat ehjinä
       ▼
  renderMathInElement(bubble, { delimiters: [...] })
       │
       │  KaTeX skannaa tekstin, löytää erottimet,
       │  korvaa ne <span class="katex">...</span> elementeillä
       ▼
  Käyttäjä näkee oppikirjamaisen kaavan
```

**Kriittinen valinta: `textContent` vs `innerHTML`**

| Menetelmä      | Takakenoviivat | XSS-turva | KaTeX-yhteensopivuus |
|----------------|----------------|-----------|----------------------|
| `innerHTML`    | ❌ Vioittuvat   | ❌ Riski   | ❌ Ei toimi          |
| `esc()` + `innerHTML` | ❌ Muuntuvat | ✅ Turvallinen | ❌ Ei toimi    |
| **`textContent`** | **✅ Ehjinä**  | **✅ Turvallinen** | **✅ Toimii** |

---

## 7. Infrastruktuuri ja deployment

### Docker Compose -palvelut

| Palvelu    | Image                   | Portti | Volume mountit                    |
|------------|-------------------------|--------|-----------------------------------|
| `postgres` | `ankane/pgvector:latest`| 5432   | `pgdata:/var/lib/postgresql/data` |
| `api`      | `./Dockerfile` (build)  | 8000   | `model_cache`, `./static`, `./calc` |

### Ympäristömuuttujat (`.env` – EI versionhallinnassa)

```
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=...
AZURE_OPENAI_API_KEY=...
```

### Ympäristömuuttujat (`docker-compose.yaml`)

```
AZURE_OPENAI_ENDPOINT=https://....openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
AZURE_OPENAI_API_VERSION=2024-02-15-preview
EMBED_MODEL=BAAI/bge-m3
```

---

## 8. Kansiorakenne

```
.
├── api/
│   ├── rag_api.py              # FastAPI-pääsovellus (RAG + LLM + tools)
│   └── test_math.py            # Erillinen testireitti (ei käytössä)
├── calc/
│   ├── __init__.py
│   └── surface_treatment.py    # Laskentafunktiot (Faraday, virtatiheys)
├── data/
│   ├── chunks.jsonl            # Indeksoitavat tekstikappaleet
│   └── sources.jsonl           # Lähdemetatiedot
├── scripts/
│   ├── embed_and_index.py      # Vektori-indeksointiputki
│   ├── fetch_and_chunk.py      # Datan keräys ja chunkkaus
│   ├── run_pipeline.sh         # Kokonainen pipeline-ajo
│   └── suggest_sources.py      # Lähdesuosittelija
├── static/
│   └── index.html              # Käyttöliittymä (KaTeX + chat)
├── docker-compose.yaml
├── Dockerfile
├── requirements.txt
├── config.yaml / config.example.yaml
├── .env                        # Salaisuudet (gitignore)
└── .gitignore
```

---

## 9. Sessiomuisti – Progressive Summarization

### 9.1 Konsepti

Jokaisen vastauksen yhteydessä LLM tekee toisen kutsun, joka tiivistää
session tähänastisen keskustelun 2–4 lauseeksi. Tämä tiivistelmä:

- Toimii **kontekstina** seuraavalle kysymykselle (promptin osana)
- **Vektoroidaan** ja tallennetaan `sessions`-tauluun (vanhojen sessioiden haku)
- **Korvaa edellisen** tiivistelmän – ei kumuloidu, vakiopituinen

### 9.2 Tietomalli

```sql
CREATE TABLE sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    title         TEXT,                -- automaattinen otsikko (1. kysymys)
    summary       TEXT,                -- viimeisin tiivistelmä
    summary_embedding VECTOR(1024)     -- vektoroitu tiivistelmä
);

CREATE TABLE messages (
    id            SERIAL PRIMARY KEY,
    session_id    UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role          TEXT CHECK (role IN ('user','assistant')),
    content       TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### 9.3 Tiivistelmän luonti (joka vastauksella)

```
[Vanha summary] + [Uusin Q+A]
          │
          ▼
  Azure OpenAI:  "Tiivistä tämä keskustelu 2–4 lauseella.
                  Säilytä: aiheet, laskelmat, johtopäätökset."
          │
          ▼
  UPDATE sessions SET
    summary = <uusi tiivistelmä>,
    summary_embedding = embed(<uusi tiivistelmä>),
    updated_at = NOW()
```

### 9.4 Session jatkaminen (Flow)

```
1. Käyttäjä valitsee vanhan session sivupalkista
   (tai aloittaa uuden → UUID luodaan)

2. POST /ask { session_id: "abc-123", question: "Entä nikkelille?" }

3. Backend:
   a) Hakee sessions.summary → "Aiemmin laskettiin Cu-saostusta 10A/2h..."
   b) RAG-haku kysymykselle
   c) system_prompt = RAG-konteksti + summary + ohjeet
   d) Azure OpenAI → vastaus
   e) Tallenna Q+A messages-tauluun
   f) Tiivistä koko sessio → päivitä sessions.summary

4. Käyttäjä saa vastauksen, joka ottaa huomioon aiemman keskustelun
```

### 9.5 Token-budjetti

| Komponentti          | Arvio (tokeneina)     |
|----------------------|-----------------------|
| System prompt (ohje) | ~100                  |
| RAG-konteksti        | ~1500                 |
| Session-tiivistelmä  | ~200                  |
| Käyttäjän kysymys    | ~50                   |
| **Vapaana vastaukselle** | **~2100 (gpt-35-turbo 4k)** |

Tiivistelmä pysyy kompaktina koska se **korvataan** joka kierroksella,
ei lisätä.

### 9.6 Kustannus

Jokainen vastaus = **2 LLM-kutsua**:
1. Pääkysymys (RAG + summary + tools)
2. Tiivistelmäkutsu (lyhyt, ~300 tokenia)

Tiivistelmäkutsu on halpa – ~10% pääkysymyksen kustannuksesta.

---

## 10. Yhteenveto suunnitteluperiaatteista

1. **LLM ei laske** – kielimalli tunnistaa laskutarpeen ja delegoi
   sen deterministiselle Python-funktiolle (Function Calling)
2. **Kaava = data** – laskufunktiot palauttavat LaTeX-merkkijonoja,
   jotka kulkevat JSON-vastauksen mukana frontendille
3. **textContent = ehjät takakenoviivat** – frontendin DOM-manipulaatio
   käyttää `textContent`-menetelmää, joka säilyttää `\[`, `\(`, `\\frac`
   jne. muuttumattomina KaTeX-kirjaston käyttöön
4. **Volume mount = nopea kehitys** – `static/` ja `calc/` on mountattu
   suoraan konttiin, joten muutokset näkyvät ilman uudelleenrakennusta
5. **Fallback** – jos Azure OpenAI -avain puuttuu, API palaa
   yksinkertaiseen extractive-RAG-tilaan (paras osuma = vastaus)
6. **Progressive Summarization** – jokaisen vastauksen jälkeen koko
   session tiivistetään 2–4 lauseeksi, joka toimii "muistina" seuraaville
   kysymyksille ilman että token-budjetti kasvaa
