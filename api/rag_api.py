import os
import uuid
import json
import logging
from functools import lru_cache
from pathlib import Path
from datetime import datetime

from openai import AzureOpenAI
import calc.surface_treatment as st

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pgvector.psycopg import register_vector
from pydantic import BaseModel, Field

log = logging.getLogger("searchassistant")

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


class AskRequest(BaseModel):
    question: str
    session_id: str | None = None
    k: int = 5


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchResult]
    session_id: str


class SessionInfo(BaseModel):
    id: str
    title: str | None
    summary: str | None
    created_at: str
    updated_at: str


class SessionDetail(BaseModel):
    session: SessionInfo
    messages: list[dict]


# ── DB helpers ───────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_conn():
    conn = psycopg.connect(os.getenv("DATABASE_URL"))
    register_vector(conn)
    return conn


def ensure_session_tables():
    """Create sessions and messages tables if they don't exist."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at    TIMESTAMPTZ DEFAULT NOW(),
            updated_at    TIMESTAMPTZ DEFAULT NOW(),
            title         TEXT,
            summary       TEXT,
            summary_embedding VECTOR(1024)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id            SERIAL PRIMARY KEY,
            session_id    UUID REFERENCES sessions(id) ON DELETE CASCADE,
            role          TEXT CHECK (role IN ('user','assistant')),
            content       TEXT,
            created_at    TIMESTAMPTZ DEFAULT NOW()
        );
        """)
    conn.commit()


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



# ── Tools definition (shared) ────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "faraday_mass_calculation",
            "description": "Laskee saostuneen aineen massan Faradayn elektrolyysilain avulla.",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_a": {"type": "number", "description": "Sähkövirta ampeereina (A)"},
                    "time_s": {"type": "number", "description": "Aika sekunteina (s)"},
                    "molar_mass": {"type": "number", "description": "Aineen moolimassa (g/mol), esim. Cu=63.546"},
                    "electrons": {"type": "integer", "description": "Siirtyvien elektronien hapetusluku (z), esim. Cu=2"}
                },
                "required": ["current_a", "time_s", "molar_mass", "electrons"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "faraday_thickness_calculation",
            "description": "Laskee pinnoitteen paksuuden massan, tiheyden ja pinta-alan perusteella.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mass_g": {"type": "number", "description": "Saostunut massa grammoina (g)"},
                    "density_g_cm3": {"type": "number", "description": "Pinnoitteen tiheys (g/cm³), esim Cu=8.96"},
                    "area_dm2": {"type": "number", "description": "Pinta-ala neliödesimetreinä (dm²)"}
                },
                "required": ["mass_g", "density_g_cm3", "area_dm2"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "current_density_calculation",
            "description": "Laskee virtatiheyden.",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_a": {"type": "number", "description": "Virta (A)"},
                    "area_dm2": {"type": "number", "description": "Pinta-ala (dm²)"}
                },
                "required": ["current_a", "area_dm2"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "unit_conversion",
            "description": (
                "Muuntaa arvon SI-etuliitteiden välillä. "
                "Tuetut etuliitteet: piko, nano, mikro, milli, sentti, desi, perus (ei etuliitettä), "
                "deka, hehto, kilo, mega, giga. Tukee myös englanninkielisiä nimiä (pico, micro, centi jne.). "
                "Esim: 1500 milli-metriä = 1.5 metriä, 2.5 kilogrammaa = 2500 grammaa."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "Muunnettava lukuarvo"},
                    "from_prefix": {
                        "type": "string",
                        "description": "Lähtöetuliite, esim. 'milli', 'kilo', 'mikro', 'sentti', 'perus' (=ei etuliitettä)",
                        "enum": ["piko", "nano", "mikro", "milli", "sentti", "desi", "perus", "deka", "hehto", "kilo", "mega", "giga"]
                    },
                    "to_prefix": {
                        "type": "string",
                        "description": "Kohdeetuliite, esim. 'perus', 'milli', 'kilo'",
                        "enum": ["piko", "nano", "mikro", "milli", "sentti", "desi", "perus", "deka", "hehto", "kilo", "mega", "giga"]
                    },
                    "unit_symbol": {
                        "type": "string",
                        "description": "Perusyksikön symboli, esim. 'm' (metri), 'g' (gramma), 'A' (ampeeri), 'l' (litra)"
                    }
                },
                "required": ["value", "from_prefix", "to_prefix", "unit_symbol"]
            }
        }
    }
]

TOOL_DISPATCH = {
    "faraday_mass_calculation": st.faraday_mass_calculation,
    "faraday_thickness_calculation": st.faraday_thickness_calculation,
    "current_density_calculation": st.current_density_calculation,
    "unit_conversion": st.unit_conversion,
}


# ── Session helpers ──────────────────────────────────────────────────
def get_or_create_session(session_id: str | None, first_question: str) -> str:
    """Return existing session_id or create a new one."""
    conn = get_conn()
    if session_id:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM sessions WHERE id = %s", (session_id,))
            if cur.fetchone():
                return session_id
    # Create new session
    new_id = str(uuid.uuid4())
    title = first_question[:80]
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO sessions (id, title) VALUES (%s, %s)",
            (new_id, title)
        )
    conn.commit()
    return new_id


def get_session_summary(session_id: str) -> str | None:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT summary FROM sessions WHERE id = %s", (session_id,))
        row = cur.fetchone()
    return row[0] if row else None


def save_message(session_id: str, role: str, content: str):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content)
        )
    conn.commit()


def update_session_summary(session_id: str, summary: str):
    conn = get_conn()
    try:
        summary_vec = embed_query(summary)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET summary = %s, summary_embedding = %s::vector, "
                "updated_at = NOW() WHERE id = %s",
                (summary, summary_vec, session_id)
            )
        conn.commit()
    except Exception as e:
        log.warning("Failed to update session summary: %s", e)
        conn.rollback()


def generate_summary(client, deployment_name: str, old_summary: str | None,
                     question: str, answer: str) -> str | None:
    """Ask LLM to create a progressive summary of the session."""
    if not client:
        return None
    context = ""
    if old_summary:
        context = f"Aiempi tiivistelmä:\n{old_summary}\n\n"
    context += f"Viimeisin Q&A:\nKäyttäjä: {question}\nAssistentti: {answer[:500]}"

    try:
        resp = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": (
                    "Tehtäväsi on tiivistää käyty keskustelu 2–4 lauseella. "
                    "Säilytä: aiheet, laskelmat (parametrit + tulokset), "
                    "johtopäätökset ja avoimet kysymykset. Ole tiivis."
                )},
                {"role": "user", "content": context}
            ],
            max_tokens=300
        )
        return resp.choices[0].message.content
    except Exception as e:
        log.warning("Summary generation failed: %s", e)
        return None


# ── Startup ──────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    ensure_session_tables()


# ── POST /ask ────────────────────────────────────────────────────────
@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    q = req.question
    vec = embed_query(q)
    rows = fetch_matches(vec, limit=req.k)

    results = [
        SearchResult(id=r[0], source_url=r[1], title=r[2], license=r[3],
                     language=r[4], content=r[5], score=float(r[6]))
        for r in rows
    ]

    client = None
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-35-turbo")

    if api_key and endpoint:
        client = AzureOpenAI(
            api_key=api_key,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=endpoint
        )

    # Session management
    session_id = get_or_create_session(req.session_id, q)
    old_summary = get_session_summary(session_id)

    if not client:
        # Fallback: no LLM
        if not results:
            return AskResponse(
                answer="Valitettavasti en löytänyt tietoa tästä aiheesta tietokannasta.",
                sources=[], session_id=session_id
            )
        best = results[0]
        answer_parts = [f"Tässä tietoa aiheesta (lähde: {best.title}):\n", best.content[:1500]]
        if len(results) > 1:
            answer_parts.append(f"\n\nLisätietoa löytyy {len(results) - 1} muusta lähteestä.")
        fallback_answer = "".join(answer_parts)
        save_message(session_id, "user", q)
        save_message(session_id, "assistant", fallback_answer)
        return AskResponse(answer=fallback_answer, sources=results, session_id=session_id)

    # Context building
    context_texts = [f"Lähde: {r.title}\n{r.content}" for r in results]
    context_str = "\n\n---\n\n".join(context_texts)

    summary_block = ""
    if old_summary:
        summary_block = (
            f"\n\nAIEMPI KESKUSTELU (tiivistelmä):\n{old_summary}\n\n"
            "Ota aiempi keskustelu huomioon vastauksessasi. "
            "Käyttäjä saattaa viitata aiempiin kysymyksiin.\n"
        )

    system_prompt = (
        "Olet teollisen pintakäsittelyn ja sähkökemian asiantuntija. "
        "Käytä vastauksissasi vain viereistä lähdekontekstia TAI käytössäsi olevia laskentatyökaluja. "
        "Jos sinun pitää laskea sähkökemiallisia arvoja (Faradayn massat, paksuudet, virtatiheydet), "
        "KÄYTÄ AINA TYÖKALUJA (tools), äläkä yritä laskea itse päässäsi. Palauta tuloksena saamasi "
        "laskentavaiheet (calculation_steps, jotka ovat valmista LaTeXia) sellaisenaan suoraan vastauksessasi!"
        f"{summary_block}\n"
        f"LÄHTEET:\n{context_str}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": q}
    ]

    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )
        msg = response.choices[0].message

        # Tool execution loop
        if msg.tool_calls:
            messages.append(msg)
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                handler = TOOL_DISPATCH.get(func_name)
                tool_result = handler(**args) if handler else {"error": f"Unknown tool: {func_name}"}
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result)
                })

            second_response = client.chat.completions.create(
                model=deployment_name,
                messages=messages
            )
            final_answer = second_response.choices[0].message.content
        else:
            final_answer = msg.content

        # Persist Q+A and update summary
        save_message(session_id, "user", q)
        save_message(session_id, "assistant", final_answer)

        new_summary = generate_summary(client, deployment_name, old_summary, q, final_answer)
        if new_summary:
            update_session_summary(session_id, new_summary)

        return AskResponse(answer=final_answer, sources=results, session_id=session_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        save_message(session_id, "user", q)
        err_answer = f"Virhe kielimallin käytössä: {str(e)}"
        save_message(session_id, "assistant", err_answer)
        return AskResponse(answer=err_answer, sources=results, session_id=session_id)


# ── Session CRUD endpoints ───────────────────────────────────────────
@app.get("/sessions", response_model=list[SessionInfo])
def list_sessions():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, title, summary, created_at, updated_at
            FROM sessions ORDER BY updated_at DESC LIMIT 50
        """)
        rows = cur.fetchall()
    return [
        SessionInfo(
            id=str(r[0]), title=r[1], summary=r[2],
            created_at=r[3].isoformat(), updated_at=r[4].isoformat()
        )
        for r in rows
    ]


@app.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: str):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, summary, created_at, updated_at FROM sessions WHERE id = %s",
            (session_id,)
        )
        s = cur.fetchone()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE session_id = %s ORDER BY created_at",
            (session_id,)
        )
        msgs = cur.fetchall()

    return SessionDetail(
        session=SessionInfo(
            id=str(s[0]), title=s[1], summary=s[2],
            created_at=s[3].isoformat(), updated_at=s[4].isoformat()
        ),
        messages=[{"role": m[0], "content": m[1], "created_at": m[2].isoformat()} for m in msgs]
    )


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE id = %s RETURNING id", (session_id,))
        deleted = cur.fetchone()
    conn.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "id": session_id}


# Serve static files (CSS, JS, images, etc.)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# TESTAUSTA VARTEN - Reitti, joka palauttaa matematiikkaa
class AskResponseTest(BaseModel):
    answer: str
    sources: list = []

@app.get("/test-ask", response_model=AskResponseTest)
def test_ask():
    # Tämä palauttaa demovastauksen, jossa on KaTeX/LaTeX -kaavoja
    return AskResponseTest(
        answer="Tässä on esimerkki laskentakaavojeni näyttämisestä:\n\nLämmitystarpeen kaava on $P = \\frac{m \\cdot c \\cdot \\Delta T}{t}$, missä $m$ on massa ja $\\Delta T$ on lämpötilaero.\n\nEsimerkkilaskun tulos on:\n$$ E = \\int_{0}^{t} P(t) dt \\approx 45.2 \\text{ kW} $$"
    )
