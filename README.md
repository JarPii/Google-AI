# SearchAssistant (Vertex + Postgres/pgvector)

Paikallinen hakusiemen avoimista lähteistä: Gemini Flash ehdottaa lähteitä, data ingestoidaan, chunkataan, upsertataan pgvectoriin, ja FastAPI tarjoaa haun.

## Askelmerkit
1. Kopioi asetukset: `cp config.example.yaml config.yaml` ja täytä Vertex- ja Postgres-tiedot.
2. Käynnistä Postgres+pgvector Dockerilla: `cp .env.example .env && docker compose up -d`.
3. Asenna riippuvuudet: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
4. Aja koko putki yhdellä komennolla: `bash scripts/run_pipeline.sh config.yaml "electrochemical surface treatment"`.
	- Vaihtoehtoisesti manuaalisesti: `suggest_sources.py` → `fetch_and_chunk.py` → `embed_and_index.py`.
5. Käynnistä API: `DATABASE_URL=postgresql://user:pass@localhost:5432/search_assistant uvicorn api.rag_api:app --reload`.

## Tietokantarakenne
Taulu `public.documents` luodaan automaattisesti, sisältäen `vector(1024)` sarakkeen. Varmista, että `pgvector`-laajennus on asennettu.

## Vertex-kulut
Käytä Gemini Flashia ehdotuksiin; token-kulut pysyvät tyypillisesti senteissä per tuhansia kyselyjä. Promptit ovat lyhyitä (lista URL-ehdotuksista).

## Muistiinpanot
- Embedding tehdään paikallisesti `BAAI/bge-m3`:llä, joten embedding-API-kuluja ei tule.
- FastAPI:ssa on placeholder-embeddingkutsu; tuotantoon kannattaa nostaa embedding-malli palveluna ja lisätä BM25/tsvector-haku rinnalle.
- Lataa vain aidosti avoimet/lisenssoidut lähteet. Huomioi, että ISO/ASTM-standardien täysteksti ei ole avointa.
