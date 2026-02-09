import os
from functools import lru_cache
from pathlib import Path

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pgvector.psycopg import register_vector
from pydantic import BaseModel

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="SearchAssistant")


# ── Models ───────────────────────────────────────────────────────────
class SearchResult(BaseModel):
    id: str
    score: float
    content: str
    source_url: str | None
    title: str | None
    license: str | None
    language: str | None


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchResult]


# ── DB helpers ───────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_conn():
    conn = psycopg.connect(os.getenv("DATABASE_URL"))
    register_vector(conn)
    return conn


def fetch_matches(query_vector, limit: int = 5):
    sql = """
    SELECT id, source_url, title, license, language, content,
           1 - (embedding <=> %(qv)s::vector) AS score
    FROM public.documents
    ORDER BY embedding <=> %(qv)s::vector
    LIMIT %(limit)s
    """
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, {"qv": query_vector, "limit": limit})
        rows = cur.fetchall()
    return rows


# ── Embedding helper ─────────────────────────────────────────────────
def _get_model():
    from sentence_transformers import SentenceTransformer
    if not hasattr(_get_model, "_inst"):
        model_name = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
        _get_model._inst = SentenceTransformer(model_name)  # type: ignore[attr-defined]
    return _get_model._inst  # type: ignore[attr-defined]


def embed_query(text: str) -> list[float]:
    model = _get_model()
    return model.encode([text], normalize_embeddings=True)[0].tolist()


# ── Routes ───────────────────────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/search", response_model=list[SearchResult])
def search(q: str = Query(..., description="Natural language query"), k: int = 5):
    vec = embed_query(q)
    rows = fetch_matches(vec, limit=k)
    if not rows:
        raise HTTPException(status_code=404, detail="No results")
    return [
        SearchResult(id=r[0], source_url=r[1], title=r[2], license=r[3],
                     language=r[4], content=r[5], score=float(r[6]))
        for r in rows
    ]


@app.get("/ask", response_model=AskResponse)
def ask(q: str = Query(..., description="Kysymys suomeksi tai englanniksi"), k: int = 5):
    """
    Hae konteksti pgvectorista ja kokoa vastaus lähteistä.
    Tämä on yksinkertainen extractive-RAG: palauttaa osuvimman
    kappaleen vastauksena ja loput lähteiksi.
    Myöhemmin tähän voi liittää LLM-generoinnin.
    """
    vec = embed_query(q)
    rows = fetch_matches(vec, limit=k)
    if not rows:
        return AskResponse(
            answer="Valitettavasti en löytänyt tietoa tästä aiheesta tietokannasta.",
            sources=[],
        )

    results = [
        SearchResult(id=r[0], source_url=r[1], title=r[2], license=r[3],
                     language=r[4], content=r[5], score=float(r[6]))
        for r in rows
    ]

    # Build a simple extractive answer from the top result
    best = results[0]
    answer_parts = []
    answer_parts.append(f"Tässä tietoa aiheesta (lähde: {best.title}):\n")
    answer_parts.append(best.content[:1500])
    if len(results) > 1:
        answer_parts.append(f"\n\nLisätietoa löytyy {len(results) - 1} muusta lähteestä (ks. alla).")

    return AskResponse(answer="".join(answer_parts), sources=results)


# Serve static files (CSS, JS, images, etc.)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
