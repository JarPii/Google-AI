# AI-suunnitteluavustaja – Toteutussuunnitelma
## Sähkökemiallinen pintakäsittely – laitossuunnittelu

---

## 1. Visio ja tavoite

Rakennetaan AI-pohjainen suunnitteluavustaja (agentti), joka palvelee
asiantuntijaorganisaatiota pintakäsittelylaitosten suunnittelussa,
perehdytyksessä ja käyttöönotossa.

**Käyttäjäroolit:**
- Prosessisuunnittelija
- Mekaniikkasuunnittelija
- Sähkösuunnittelija
- Automaatiosuunnittelija
- Käyttöönottaja

**Avustajan kyvyt (tavoitetila):**
- Vastaa kysymyksiin (chatbot)
- Hakee ja yhdistää tietoa useista lähteistä
- Laskee ja mitoittaa (altaat, lämmitys, virta, ilmastointi)
- Generoi dokumenttipohjia (IO-listat, tarkastuslistat, proseduurit)
- Tarkistaa suunnitelmia (EHS, standardit, parametrirajat)
- Etsii vikatilanteiden syitä ja korjausehdotuksia

---

## 2. Vaiheistettu eteneminen

### VAIHE 1 – Tietopohja (siemen) ✅ TEHTY
> Tavoite: Perus-RAG-haku avoimista lähteistä

**Toteutettu:**
- [x] Vertex AI (Gemini Flash) lähde-ehdotusten haku
- [x] Seed-lista 15 avointa lähdettä (Wikipedia, LibreTexts, OSHA, EPA)
- [x] Lataus → chunkkaus → embedding (bge-m3) → pgvector
- [x] 127 chunkkia, 11 lähdettä, ~36 000 tokenia
- [x] FastAPI (/search, /ask)
- [x] Chat-käyttöliittymä (web)
- [x] Docker Compose (Postgres+pgvector + API)
- [x] GitHub-repo

**Tekniset komponentit:**
- Postgres + pgvector (vektori-indeksi)
- bge-m3 (monikielinen embedding, paikallinen)
- FastAPI + staattinen HTML/JS UI
- Docker Compose

---

### VAIHE 2 – Avoimien lähteiden laajentaminen
> Tavoite: Kattava yleissivistystietokanta (~500–1000 chunkkia)

**Tehtävät:**
- [ ] Aktivoi Vertex AI -tunnukset → Gemini hakee automaattisesti uusia lähteitä
- [ ] Laajenna seed-lista kattamaan kaikki prosessit:
  - Galvanointi (Zn, Ni, Cu, Cr, Sn, Ag, Au)
  - Anodisointi (tyyppi I/II/III, värianodisointi)
  - Electropolishing
  - Passiviointi (Cr(III), kemiallinen, elektrokemiallinen)
  - Konversiopinnoitteet (fosfatointi, kromittomat)
  - Maalauksen esikäsittely
  - Jätevesien käsittely
- [ ] Laajenna suomenkielisiä lähteitä
- [ ] Lisää suunnittelun perustietoa:
  - Tasasuuntaajat, sähkön syöttö
  - Altaiden materiaalit (PP, PVC, RST, titaani)
  - Pumput, suodattimet, lämmönvaihtimet
  - Ilmanvaihto ja imukuvut
  - PLC/DCS-automaation perusteet pintakäsittelyssä
  - Nosturit ja kuljettimet
- [ ] ECHA/REACH-tiedon kierto (vaihtoehtoinen haku 403-sivuille)
- [ ] Aja pipeline uudelleen → tarkista laatu

**Aikataulu:** 1–2 viikkoa

---

### VAIHE 3 – Chatbot (LLM-generoitu vastaus)
> Tavoite: Vastaukset luonnollisella kielellä, ei pelkkä lainaus

**Tehtävät:**
- [ ] Valitse LLM:
  - Vaihtoehto A: Paikallinen (Ollama + Llama 3.2 8B) – ilmainen, hitaampi
  - Vaihtoehto B: Gemini Flash (pilvi) – nopea, senttejä/kysely
  - Vaihtoehto C: Molemmat (config-valinta)
- [ ] Toteuta RAG-generointi /ask-endpointiin:
  - Hae top-k chunkit pgvectorista
  - Kokoa system prompt + konteksti + kysymys
  - LLM generoi vastauksen viitteineen
- [ ] System prompt suunnitteluavustajalle:
  - "Vastaa vain kontekstin perusteella"
  - "Näytä lähteet"
  - "Korosta turvallisuushuomiot"
  - "Jos et tiedä, sano ettei löydy"
- [ ] Roolikohtaiset promptit (prosessi / mekaniikka / sähkö / automaatio)
- [ ] Keskusteluhistorian tuki (multi-turn)
- [ ] Päivitä chat-UI (markdown-renderöinti, parempi UX)

**Aikataulu:** 1–2 viikkoa

---

### VAIHE 4 – Organisaation oman datan tuonti
> Tavoite: Projekteista kertynyt tieto mukaan tietokantaan

**Datalähteet ja tuontiskriptit:**

| Lähde | Muoto | Skripti | Kohde |
|---|---|---|---|
| Kylpyreseptit | Excel/CSV | import_excel.py | recipes-taulu + vektori |
| Laitelistat | Excel | import_excel.py | equipment-taulu + vektori |
| IO-listat | Excel | import_excel.py | io_list-taulu + vektori |
| Prosessiselostukset | Word/PDF | import_documents.py | vektori + metadata |
| Ohjausfilosofiat | Word/PDF | import_documents.py | vektori + metadata |
| FAT/SAT-pohjat | Word/Excel | import_checklists.py | checklists-taulu + vektori |
| Vikakirjasto | Excel | import_excel.py | defects-taulu + vektori |
| Käyttöönottopöytäkirjat | PDF | import_documents.py | vektori + metadata |

**Tehtävät:**
- [ ] Tee import_excel.py (lukee .xlsx → Postgres-taulut + chunkkaa vektori-indeksiin)
- [ ] Tee import_documents.py (PDF/DOCX → teksti → chunk → vektori)
- [ ] Tee import_checklists.py (tarkastuslistojen jäsennys)
- [ ] Suunnittele tietokantaskeema strukturoidulle datalle:
  - recipes (kylpy, kemikaali, pitoisuus, yksikkö, T, pH, virrantiheys)
  - equipment (tagi, tyyppi, valmistaja, malli, parametrit)
  - io_list (tagi, tyyppi, alue, signaali, kuvaus)
  - defects (prosessi, vika, syy, korjaus, lähde)
  - checklists (vaihe, tarkistuspiste, hyväksymiskriteerit)
- [ ] Metadata jokaiselle: projekti, asiakas (anonymisoitu), vuosi, tekijä, versio
- [ ] Tietoturva: erota avoin ja luottamuksellinen data (tagging)

**Aikataulu:** 2–4 viikkoa (riippuu datan määrästä)

---

### VAIHE 5 – Datan laadunhallinta
> Tavoite: Varmista tietokannan luotettavuus

**Automaattinen validointi (skriptit):**
- [ ] Arvoaluetarkistus (pH 0–14, T, virrantiheys, pitoisuudet)
- [ ] Pakollisten kenttien tarkistus
- [ ] Duplikaattien tunnistus (cosine similarity > 0.95)
- [ ] Yksikkömuunnos ja normalisointi (kaikki SI-yksikköihin)
- [ ] Vanhentumisvaroitus (ikä, REACH/CLP-muutokset)
- [ ] CAS-numeroiden validointi

**LLM-avusteinen tarkistus:**
- [ ] Ristiriitojen haku samasta aiheesta eri lähteistä
- [ ] Puuttuvien parametrien tunnistus
- [ ] REACH/CLP-yhteensopivuuden tarkistus

**Tietomalli laadunhallinnalle:**
- [ ] Lisää kentät: quality_score, quality_flags, status, reviewed_by, reviewed_at
- [ ] Tila-kone: draft → validated → archived / rejected
- [ ] Tarkistusjono-UI asiantuntijalle

**Chatbotin luotettavuusnäkymä:**
- [ ] Näytä quality_score ja lähteen ikä vastauksissa
- [ ] Varoitus draft/vanha datasta
- [ ] Ristiriitatilanteissa näytä molemmat lähteet

**Aikataulu:** 2–3 viikkoa

---

### VAIHE 6 – Laskenta- ja mitoitustyökalut
> Tavoite: Agentti osaa laskea, ei pelkästään hakea tekstiä

**Python-funktiot (tools):**
- [ ] Altaan mitoitus (tilavuus, mitat kapasiteetin mukaan)
- [ ] Lämmitystehon laskenta (kylvyn lämmitys, ylläpito, häviöt)
- [ ] Tasasuuntaajan mitoitus (virta, jännite, teho, ylikapasiteetti)
- [ ] Imukuvun ilmamäärä (altaan pinta-ala, nopeus)
- [ ] Käsittelyajan laskenta (pinnoitepaksuus, virrantiheys, hyötysuhde)
- [ ] Huuhteluveden kulutus (kaskadihuuhtelu, laimentumiskerroin)
- [ ] Jäteveden neutraloinnin mitoitus
- [ ] Yksikkömuunnokset (A/dm² ↔ A/ft², mg/L ↔ oz/gal, jne.)

**Tehtävät:**
- [ ] Toteuta funktiot Python-moduulina (calc/surface_treatment.py)
- [ ] Tee yksikkötestit jokaiselle funktiolle
- [ ] Dokumentoi kaavat ja lähteet
- [ ] Rekisteröi funktiot LLM:n tool-use -käyttöön

**Aikataulu:** 2–4 viikkoa

---

### VAIHE 7 – Agentti (tool-use + päättely)
> Tavoite: Itsenäisesti toimiva suunnitteluavustaja

**Arkkitehtuuri:**
```
Käyttäjän tehtävä
       ↓
  Agentti (LLM + ReAct)
       ↓
  ┌─────────────────────────────────┐
  │ Työkalut:                       │
  │  🔍 search_knowledge    → pgvector-haku (avoin + org-data)
  │  📊 query_parameters    → SQL strukturoidusta datasta
  │  🧮 calculate           → Python-mitoitusfunktiot
  │  ⚠️  check_safety        → EHS/REACH-tarkistus
  │  📋 generate_checklist  → FAT/SAT/käyttöönotto-pohjat
  │  📝 generate_io_list    → IO-listan generointi
  │  🔧 diagnose_defect     → Vikakirjaston haku + syy-analyysi
  └─────────────────────────────────┘
       ↓
  Strukturoitu vastaus + perustelut + lähteet + varoitukset
```

**Tehtävät:**
- [ ] Valitse agenttirunko:
  - Vaihtoehto A: LangGraph (graafi-pohjainen, joustava)
  - Vaihtoehto B: Oma ReAct-looppi (kevyt, täysi hallinta)
- [ ] Rekisteröi kaikki työkalut (search, query, calculate, check, generate)
- [ ] Toteuta roolikohtaiset agenttiprofiilit:
  - Prosessi: painottaa kemiaa, reseptejä, prosessiparametreja
  - Mekaniikka: painottaa materiaaleja, altaita, putkistoja
  - Sähkö: painottaa tasasuuntaajia, kaapelointia, sähköturvallisuutta
  - Automaatio: painottaa IO:ta, logiikkaa, instrumentointia
  - Käyttöönotto: painottaa testejä, proseduureja, vianhakua
- [ ] Turvallisuuskerros: agentti ei saa ohittaa EHS-varoituksia
- [ ] Auditointi: jokainen agentin päätös ja työkalu-kutsu lokitetaan

**Aikataulu:** 3–5 viikkoa

---

### VAIHE 8 – Tuotantokelpoisuus
> Tavoite: Luotettava, turvallinen, ylläpidettävä järjestelmä

**Tehtävät:**
- [ ] Autentikointi ja roolipohjainen pääsy (OIDC)
- [ ] Luottamuksellisuustasot: avoin data vs. org-data vs. projektikohtainen
- [ ] Käyttöloki ja auditointikirjanpito
- [ ] Kustannusrajat (pilvi-LLM)
- [ ] Varmuuskopiointi (pgvector + Postgres)
- [ ] CI/CD-pipeline (testit, build, deploy)
- [ ] Monitorointi (API-vastausajat, virheet, käyttömäärät)
- [ ] Päivitysprosessi: uuden datan tuonti, mallin vaihto, promptien päivitys
- [ ] Käyttäjäpalaute-mekanismi (peukku ylös/alas → evaluointi)

**Aikataulu:** 2–4 viikkoa

---

## 3. Teknologiapino (yhteenveto)

| Komponentti | Teknologia | Sijainti |
|---|---|---|
| Tietokanta + vektori | Postgres + pgvector | Docker / on-prem |
| Embedding | bge-m3 (paikallinen) | Docker |
| Hakusihteeri (lähteet) | Vertex AI Gemini Flash | Pilvi (vain haku) |
| Chatbot/agentti LLM | Gemini Flash TAI paikallinen Llama/Mistral | Pilvi tai paikallinen |
| API | FastAPI | Docker |
| UI | Web (HTML/JS) tai Teams/Slack-integraatio | Docker |
| Laskenta | Python-moduulit | Docker |
| Agenttirunko | LangGraph tai oma ReAct | Docker |
| Kontit | Docker Compose | On-prem / GCP |

---

## 4. Tietoturva ja etiikka

- Organisaation data pysyy paikallisena (tai VPC + CMEK)
- Pilvi-LLM:lle EI lähetetä luottamuksellista dataa (ellei VPC + no-train)
- Anonymisointi: asiakkaat, henkilöt, sopimushinnat
- Varoitukset: LLM-vastaus EI korvaa asiantuntijan päätöstä
- EHS: turvallisuuskriittinen tieto aina verifioidaan
- Auditointi: kaikki kyselyt ja vastaukset lokitetaan

---

## 5. Aikataulu (karkea)

| Vaihe | Kuvaus | Kesto | Kumulatiivinen |
|---|---|---|---|
| 1 | Tietopohja (siemen) | ✅ Tehty | Viikko 0 |
| 2 | Avoimien lähteiden laajentaminen | 1–2 vk | Viikko 2 |
| 3 | Chatbot (LLM-generointi) | 1–2 vk | Viikko 4 |
| 4 | Organisaation oma data | 2–4 vk | Viikko 8 |
| 5 | Datan laadunhallinta | 2–3 vk | Viikko 11 |
| 6 | Laskenta- ja mitoitustyökalut | 2–4 vk | Viikko 15 |
| 7 | Agentti (tool-use) | 3–5 vk | Viikko 20 |
| 8 | Tuotantokelpoisuus | 2–4 vk | Viikko 24 |

**Kokonaisarvio: ~6 kuukautta** (yksi kehittäjä, osa-aikainen)

Jokainen vaihe tuottaa itsenäisesti käyttökelpoisen työkalun.
Ei tarvitse odottaa vaihetta 7 saadakseen hyötyä.

---

## 6. Riskit ja mitigaatiot

| Riski | Vaikutus | Mitigaatio |
|---|---|---|
| LLM hallusinoi | Väärä suunnittelutieto | RAG + lähdeviitteet + quality_score |
| Vanha data | Vanhentunut ohje käyttöön | Ikätarkistus + REACH-validointi |
| Pilvikulut karkaavat | Budjetti ylittyy | Flash-malli + cachetus + kustannusrajat |
| Org-data vuotaa | Luottamuksellisuusriski | Paikallinen LLM + tagging + auditointi |
| Käyttäjät luottavat sokeasti | Turvallisuusriski | Disclaimerit + EHS-varoitukset |
| Datan laatu heikko | Chatbot antaa huonoja vastauksia | 3-tasoinen validointi (auto+LLM+asiantuntija) |
