# Sukututkimus-AI-avustaja — Arkkitehtuuri ja toteutusmalli

## 1. Visio

AI-avustaja joka yhdistää sukupuudatan (GEDCOM), DNA-testitulokset ja
sukututkimuksen taustatiedon yhdeksi keskustelukäyttöliittymäksi.
Käyttäjä voi luonnollisella kielellä kysyä kysymyksiä omasta
sukupuustaan, analysoida DNA-matcheja ja saada kontekstuaalisia
päätelmiä — kaikki privaatisti omalla koneella.

---

## 2. Järjestelmäarkkitehtuuri

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SELAIN (Web UI)                            │
│  Chat-käyttöliittymä  │  Sukupuunäkymä  │  DNA-visualisoinnit     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP/WebSocket
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PYTHON BACKEND (FastAPI)                       │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐ │
│  │  Reititin    │  │  SQL-agentti │  │  RAG-haku (vektori)       │ │
│  │  (Router)    │──│  (Query)     │  │  (Semantic Search)        │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────────┘ │
│         │                 │                      │                  │
│  ┌──────▼─────────────────▼──────────────────────▼───────────────┐ │
│  │                  Kontekstin kokoaja                            │ │
│  │  SQL-tulokset + vektorihaun tulokset → LLM prompt             │ │
│  └──────────────────────────┬────────────────────────────────────┘ │
│                             │                                      │
│  ┌──────────────────────────▼────────────────────────────────────┐ │
│  │               LLM (Azure OpenAI)                              │ │
│  │  Analysoi, päättelee, vastaa luonnollisella kielellä          │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────────┐   ┌──────────────────────────┐
│  PostgreSQL         │   │  Qdrant                  │
│  + pgvector         │   │  (vektoritietokanta)     │
│                     │   │                          │
│  • henkilot         │   │  Kokoelmat:              │
│  • suhteet          │   │  • tutkimusmuistiinpanot │
│  • dna_testit       │   │  • DNA-oppaat            │
│  • dna_matchit      │   │  • paikkakuntahistoria   │
│  • segmentit        │   │  • kirkonkirjat          │
│  • lahteet          │   │  • sukunimitutkimus      │
│  • tapahtumat       │   │                          │
└─────────────────────┘   └──────────────────────────┘
```

> **Huom.** Vaihtoehtoisesti Qdrantin sijaan voidaan käyttää pelkkää
> pgvectoria (kuten nykyisessä projektissa). Qdrant on parempi jos
> kokoelmia ja metadatasuodatusta tarvitaan paljon. Tämä valinta
> tehdään toteutusvaiheessa.

---

## 3. Tietomalli (PostgreSQL)

### 3.1 Ydinentiteetit

```sql
-- Henkilöt (GEDCOM-importista)
CREATE TABLE henkilot (
    id              SERIAL PRIMARY KEY,
    gedcom_id       TEXT UNIQUE,          -- @I123@
    etunimet        TEXT,
    sukunimi        TEXT,
    syntymaaika     DATE,
    kuolinaika      DATE,
    syntymapaikka   TEXT,
    kuolinpaikka    TEXT,
    sukupuoli       CHAR(1),             -- M/F/U
    myheritage_id   TEXT,                 -- linkki MyHeritage-profiiliin
    muistiinpanot   TEXT,
    luotu           TIMESTAMPTZ DEFAULT now(),
    paivitetty      TIMESTAMPTZ DEFAULT now()
);

-- Sukulaisuussuhteet
CREATE TABLE suhteet (
    id              SERIAL PRIMARY KEY,
    henkilo_id      INT REFERENCES henkilot(id),
    sukulainen_id   INT REFERENCES henkilot(id),
    suhdetyyppi     TEXT NOT NULL,        -- 'vanhempi', 'lapsi', 'puoliso'
    UNIQUE(henkilo_id, sukulainen_id, suhdetyyppi)
);

-- Elämäntapahtumat
CREATE TABLE tapahtumat (
    id              SERIAL PRIMARY KEY,
    henkilo_id      INT REFERENCES henkilot(id),
    tyyppi          TEXT NOT NULL,        -- 'syntymä','kuolema','kaste',
                                          -- 'avioliitto','muutto','rippikoulu'
    paikka          TEXT,
    paiva           DATE,
    kuvaus          TEXT,
    lahde_id        INT REFERENCES lahteet(id)
);
```

### 3.2 DNA-data

```sql
-- DNA-testitulokset
CREATE TABLE dna_testit (
    id              SERIAL PRIMARY KEY,
    henkilo_id      INT REFERENCES henkilot(id),
    palvelu         TEXT,                 -- 'MyHeritage','23andMe','AncestryDNA'
    testi_tyyppi    TEXT,                 -- 'autosomal','Y-DNA','mtDNA'
    haplotyyppi_y   TEXT,                 -- esim. 'N-M231'
    haplotyyppi_mt  TEXT,                 -- esim. 'H1a'
    etnisyysarviot  JSONB,               -- {"Finnish": 85.2, "Swedish": 10.1}
    raakadata_tiedosto TEXT              -- polku raakadatatiedostoon
);

-- DNA-matchit (MyHeritage/FTDNA/GEDmatch export)
CREATE TABLE dna_matchit (
    id              SERIAL PRIMARY KEY,
    testaaja_id     INT REFERENCES dna_testit(id),
    match_nimi       TEXT NOT NULL,
    match_email      TEXT,
    shared_cm        REAL NOT NULL,       -- jaetut sentimorganit
    shared_segments  INT,                 -- jaettujen segmenttien lkm
    suurin_segmentti REAL,                -- suurin yksittäinen segmentti cM
    arvioitu_suhde   TEXT,                -- 'serkku','pikkuserkku' jne.
    yhteinen_esi_isä TEXT,                -- käyttäjän arvio/merkintä
    myheritage_id    TEXT,
    muistiinpanot    TEXT,
    tuotu            TIMESTAMPTZ DEFAULT now()
);

-- Kromosomaaliset segmentit (triangulation)
CREATE TABLE segmentit (
    id              SERIAL PRIMARY KEY,
    match_id        INT REFERENCES dna_matchit(id),
    kromosomi       INT NOT NULL,         -- 1-22, 23=X
    alku_pos        BIGINT NOT NULL,      -- aloituspositio (bp)
    loppu_pos       BIGINT NOT NULL,
    cm_pituus       REAL NOT NULL,
    snp_maara       INT
);

-- Tutkimuslähteet
CREATE TABLE lahteet (
    id              SERIAL PRIMARY KEY,
    tyyppi          TEXT,                 -- 'kirkonkirja','rippikirja',
                                          -- 'henkikirja','DNA','verkkolähde'
    kuvaus          TEXT,
    url             TEXT,
    arkisto         TEXT,                 -- 'Kansallisarkisto','SSHY'
    viite           TEXT,                 -- tarkka arkistoviite
    henkilo_id      INT REFERENCES henkilot(id)
);

-- DNA-ryhmät (klusterit)
CREATE TABLE dna_ryhmat (
    id              SERIAL PRIMARY KEY,
    nimi            TEXT NOT NULL,         -- 'Virtasen haara', 'Tuntematon klusteri A'
    kuvaus          TEXT,
    yhteinen_esi    TEXT                  -- hypoteesi yhteisestä esi-isästä
);

CREATE TABLE dna_ryhma_jasenet (
    ryhma_id        INT REFERENCES dna_ryhmat(id),
    match_id        INT REFERENCES dna_matchit(id),
    PRIMARY KEY (ryhma_id, match_id)
);
```

### 3.3 Indeksit

```sql
CREATE INDEX idx_henkilot_sukunimi ON henkilot(sukunimi);
CREATE INDEX idx_henkilot_syntymapaikka ON henkilot(syntymapaikka);
CREATE INDEX idx_matchit_cm ON dna_matchit(shared_cm DESC);
CREATE INDEX idx_segmentit_kromo ON segmentit(kromosomi, alku_pos, loppu_pos);
CREATE INDEX idx_tapahtumat_henkilo ON tapahtumat(henkilo_id);
```

---

## 4. Vektoridata (Qdrant / pgvector)

### 4.1 Kokoelmat ja niiden sisältö

| Kokoelma | Sisältö | Lähde |
|---|---|---|
| `tutkimusmuistiinpanot` | Omat muistiinpanot, hypoteesit, tutkimuspäiväkirja | Käyttäjä |
| `dna_opas` | DNA-sukututkimuksen perusteet: cM-tulkinta, triangulation, endogamia, haploryhmät | Julkiset oppaat |
| `paikkakuntahistoria` | Kylien, seurakuntien ja pitäjien historia, muuttoliikkeet | Kirjallisuus, Wikipedia |
| `kirkonkirjat_ocr` | OCR-luetut kirkonkirjamerkinnät (tekstinä) | Kansallisarkisto, SSHY |
| `sukunimitutkimus` | Sukunimien etymologia, levinneisyys, historia | Tutkimuskirjallisuus |
| `gedcom_narratiivit` | GEDCOM-datasta generoituja henkilökuvauksia (LLM-generoitu) | Oma GEDCOM |

### 4.2 Embedding-malli

```yaml
embedding:
  model: BAAI/bge-m3         # monikielinen, 1024 dim, toimii CPU:lla
  device: cpu
  chunk_size: 300            # tokenia
  chunk_overlap: 50
```

---

## 5. Backend-arkkitehtuuri (FastAPI)

### 5.1 Reitittimen logiikka (Query Router)

```python
# Pseudokoodi — reitittimen toimintaperiaate

async def handle_query(user_message: str, session: Session):
    """
    1. Analysoi käyttäjän kysymys
    2. Päätä mitä tietolähteitä tarvitaan
    3. Hae data
    4. Rakenna LLM-prompt
    5. Vastaa
    """

    # Vaihe 1: LLM päättää mitä dataa tarvitaan (function calling)
    plan = await llm.plan_query(user_message, tools=[
        "sql_query",           # tarkka data PostgreSQL:stä
        "vector_search",       # semanttinen haku
        "relationship_path",   # sukupuunavigaatio
        "cm_analyzer",         # cM-arvojen tulkinta
        "segment_overlap",     # segmenttien vertailu
    ])

    # Vaihe 2: Suorita työkalut
    context_parts = []
    for tool_call in plan.tool_calls:
        result = await execute_tool(tool_call)
        context_parts.append(result)

    # Vaihe 3: Kokoa vastaus
    response = await llm.generate(
        system_prompt=GENEALOGY_SYSTEM_PROMPT,
        context=context_parts,
        user_message=user_message,
        session_history=session.history
    )

    return response
```

### 5.2 Työkalut (Tools / Function Calling)

| Työkalu | Kuvaus | Tietolähde |
|---|---|---|
| `sql_query` | Suorita SQL-kysely henkilö/DNA-tauluihin | PostgreSQL |
| `vector_search` | Semanttinen haku tutkimustiedosta | Qdrant/pgvector |
| `relationship_path` | Etsi sukupuupolku henkilöstä toiseen (BFS/Dijkstra) | PostgreSQL (suhteet) |
| `cm_analyzer` | Tulkitse cM-arvo → mahdolliset suhderyhmät | Laskenta + taulukko |
| `segment_overlap` | Vertaa kahden matchin segmenttejä (triangulation) | PostgreSQL (segmentit) |
| `shared_matches` | Etsi matchit jotka jakavat DNA:ta molempien kanssa | PostgreSQL |
| `cluster_matches` | Ryhmittele matchit segmenttien perusteella | PostgreSQL + algoritmi |
| `timeline` | Rakenna henkilön/suvun aikajana | PostgreSQL (tapahtumat) |

### 5.3 Esimerkkiprompti

```
Olet sukututkimuksen AI-avustaja. Käyttäjällä on oma sukutietokanta
ja DNA-testituloksia.

Tehtäväsi:
- Vastaa sukututkimuskysymyksiin käyttäen annettua dataa
- Analysoi DNA-matcheja ja ehdota mahdollisia yhteyksiä
- Selitä DNA-käsitteet selkeästi (cM, segmentit, triangulation)
- Ehdota tutkimusstrategioita tuntemattomien sukulaisten paikantamiseen
- ÄLÄ keksi tietoa — kerro selkeästi mikä on datasta ja mikä on päättelyä

Käytettävissä olevat työkalut:
{tools}

Käyttäjän sukupuussa on {person_count} henkilöä ja {match_count} DNA-matchia.
```

---

## 6. Datan tuonti (Import Pipeline)

### 6.1 GEDCOM-importteri

```
MyHeritage → Export GEDCOM
                │
                ▼
    ┌───────────────────────┐
    │  gedcom_parser.py     │
    │  python-gedcom lib    │
    │                       │
    │  GEDCOM → SQL INSERT  │
    │  • henkilot           │
    │  • suhteet            │
    │  • tapahtumat         │
    └───────────────────────┘
```

### 6.2 DNA-datan tuonti

```
MyHeritage → DNA Matches CSV export
           → Chromosome Browser CSV export

    ┌───────────────────────┐
    │  dna_importer.py      │
    │                       │
    │  CSV → SQL INSERT     │
    │  • dna_matchit        │
    │  • segmentit          │
    └───────────────────────┘
```

### 6.3 Tutkimustiedon vektorointi

```
    Markdown/PDF/tekstit
           │
           ▼
    ┌───────────────────────┐
    │  embed_knowledge.py   │
    │                       │
    │  1. Chunkkaa teksti   │
    │  2. Laske embedding   │
    │  3. Tallenna Qdrant   │
    └───────────────────────┘
```

---

## 7. Infrastruktuuri (Docker Compose)

```yaml
# docker-compose.yaml
services:
  db:
    image: ankane/pgvector:latest
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: sukututkimus
      POSTGRES_USER: suku
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes:
      - /mnt/hdd/qdrant_data:/qdrant/storage   # HDD:lle, tilaa riittää

  api:
    build: .
    ports: ["8000:8000"]
    depends_on: [db, qdrant]
    environment:
      DATABASE_URL: postgresql://suku:${DB_PASSWORD}@db:5432/sukututkimus
      QDRANT_URL: http://qdrant:6333
      AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT}
      AZURE_OPENAI_API_KEY: ${AZURE_OPENAI_API_KEY}
      AZURE_OPENAI_DEPLOYMENT: ${AZURE_OPENAI_DEPLOYMENT}
    volumes:
      - ./static:/app/static
      - model_cache:/root/.cache

volumes:
  pgdata:
  model_cache:
```

**Resurssitarve (arvio):**

| Palvelu | RAM | Levy |
|---|---|---|
| PostgreSQL + pgvector | ~200 Mt | SSD |
| Qdrant | ~300 Mt | HDD (ok) |
| FastAPI + embedding-malli | ~1,5 Gt | SSD (malli cacheissa) |
| **Yhteensä** | **~2 Gt** | Mahtuu hyvin |

---

## 8. Toteutusjärjestys

### Vaihe 1 — Pohja (viikko 1–2)
- [ ] Uusi projekti: `~/dev/SukuAI/`
- [ ] Docker Compose: PostgreSQL + Qdrant
- [ ] Tietokantaskeema (migrate.sql)
- [ ] GEDCOM-parseri → henkilöt + suhteet PostgreSQL:iin
- [ ] Yksinkertainen testikysely: "montako henkilöä tietokannassa?"

### Vaihe 2 — DNA-data (viikko 3)
- [ ] MyHeritage DNA Match CSV importteri
- [ ] Segmenttidata-importteri (Chromosome Browser CSV)
- [ ] cM-analyysityökalu (cM → mahdolliset suhteet -taulukko)
- [ ] SQL-kyselyt: "näytä matchit yli 50 cM", "segmentit kromosomissa 7"

### Vaihe 3 — RAG + vektoridata (viikko 4)
- [ ] Embedding pipeline: tutkimusmuistiinpanot → Qdrant
- [ ] DNA-oppaan chunkkaus ja vektorointi
- [ ] Semanttinen haku: "miten tulkitsen endogamian vaikutuksen cM-arvoihin?"

### Vaihe 4 — AI-avustaja (viikko 5–6)
- [ ] FastAPI endpoint: chat
- [ ] Query Router: SQL vs. vektori vs. molemmat
- [ ] Function calling: LLM valitsee työkalut
- [ ] System prompt sukututkimuskontekstilla
- [ ] Web UI (chat + vastausten visualisointi)

### Vaihe 5 — Analytiikka (viikko 7–8)
- [ ] Sukupuupolun haku (relationship path)
- [ ] Triangulation-työkalu (segmenttien vertailu)
- [ ] Match-klusterointi (ryhmittele matchit haaroihin)
- [ ] Aikajananäkymä

### Vaihe 6 — Viimeistely (viikko 9–10)
- [ ] Tutkimuspäiväkirja (muistiinpanojen tallennus chatista)
- [ ] GEDCOM-päivitysten synkronointi
- [ ] DNA-visualisoinnit (kromosomikartta, verkkokaavio)
- [ ] Dokumentaatio

---

## 9. Teknologiapino

| Kerros | Teknologia | Peruste |
|---|---|---|
| LLM | Azure OpenAI (GPT-4o / GPT-35-turbo) | Jo käytössä, function calling -tuki |
| Embedding | BAAI/bge-m3 (lokaali) | Monikielinen, jo käytössä |
| Relaatiotietokanta | PostgreSQL + pgvector | Jo käytössä, luotettava |
| Vektoritietokanta | Qdrant TAI pgvector | Qdrant jos paljon kokoelmia |
| Backend | FastAPI (Python) | Jo käytössä, nopea kehittää |
| Frontend | HTML + vanilla JS | Yksinkertainen, ei buildausta |
| Kontit | Docker Compose | Jo käytössä |
| GEDCOM-parseri | python-gedcom2 | Vakiintunut Python-kirjasto |
| Graafialgoritmit | NetworkX | Sukupuupolkujen haku |

---

## 10. Esimerkkikäyttötapauksia

### "Kuka tämä DNA-match voisi olla?"
```
Käyttäjä: Minulla on match "Anna K.", shared 45 cM, 3 segmenttiä.
          Suurin segmentti 22 cM. Kuka hän voisi olla?

Avustaja:
  1. [cm_analyzer] → 45 cM = todennäköisesti 3.–4. serkun etäisyys
     (yhteinen esi-isä 4–6 sukupolvea taaksepäin, n. 1820–1880)
  2. [sql_query] → Haetaan muut matchit välillä 35–55 cM
  3. [segment_overlap] → Verrataan Anna K:n segmenttejä muihin matcheihin
     → Kromosomi 7:ssä päällekkäisyys "Matti V." kanssa!
  4. [vector_search] → "kromosomi 7 Kuopion suku 1850" → löytyy
     tutkimusmuistiinpano jossa maininta Kuopion suvusta
  5. Vastaus: "Anna K. jakaa 45 cM kanssasi, mikä viittaa 3.–4. serkkuun.
     Hänellä on yhteinen segmentti kromosomissa 7 myös Matti V:n kanssa,
     mikä viittaa samaan sukuhaaraan. Tutkimusmuistiinpanojesi perusteella
     tämä voisi liittyä Kuopion haaraan. Suosittelen..."
```

### "Näytä isänisän sukuhaara"
```
Käyttäjä: Näytä isänisäni sukuhaara niin pitkälle kuin tiedetään.

Avustaja:
  1. [sql_query] → Hae käyttäjä → isä → isänisä → ... (rekursiivinen)
  2. [timeline] → Rakenna aikajana tapahtumista
  3. Vastaus: taulukko + narratiivi sukuhaarasta
```

---

## 11. Tietoturva

- **Kaikki data paikallista** — ei pilvitallennusta (paitsi Azure OpenAI API-kutsut)
- LLM:lle lähetetään vain kontekstifragmentteja, ei koko tietokantaa
- Ei julkista verkkopääsyä — localhost only
- `.env`-tiedostossa API-avaimet (ei versionhallintaan)
- DNA-raakadata HDD:llä, ei Dockerin volumeissa
