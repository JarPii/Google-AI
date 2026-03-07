import os
from functools import lru_cache
from pathlib import Path


import json
from openai import AzureOpenAI
import calc.surface_treatment as st

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
    vec = embed_query(q)
    rows = fetch_matches(vec, limit=k)
    
    results = [
        SearchResult(id=r[0], source_url=r[1], title=r[2], license=r[3],
                     language=r[4], content=r[5], score=float(r[6]))
        for r in rows
    ]

    client = None
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    
    if api_key and endpoint:
        client = AzureOpenAI(
            api_key=api_key,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=endpoint
        )
        
    if not client:
        # Fallback to old basic behavior if Azure is missing
        if not results:
            return AskResponse(answer="Valitettavasti en löytänyt tietoa tästä aiheesta tietokannasta.", sources=[])
        best = results[0]
        answer_parts = [f"Tässä tietoa aiheesta (lähde: {best.title}):\n", best.content[:1500]]
        if len(results) > 1:
            answer_parts.append(f"\n\nLisätietoa löytyy {len(results) - 1} muusta lähteestä.")
        return AskResponse(answer="".join(answer_parts), sources=results)

    # Context building
    context_texts = [f"Lähde: {r.title}\n{r.content}" for r in results]
    context_str = "\n\n---\n\n".join(context_texts)

    system_prompt = (
        "Olet teollisen pintakäsittelyn ja sähkökemian asiantuntija. "
        "Käytä vastauksissasi vain viereistä lähdekontekstia TAI käytössäsi olevia laskentatyökaluja. "
        "Jos sinun pitää laskea sähkökemiallisia arvoja (Faradayn massat, paksuudet, virtatiheydet), "
        "KÄYTÄ AINA TYÖKALUJA (tools), äläkä yritä laskea itse päässäsi. Palauta tuloksena saamasi "
        "laskentavaiheet (calculation_steps, jotka ovat valmista LaTeXia) sellaisenaan suoraan vastauksessasi!\n\n"
        f"LÄHTEET:\n{context_str}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": q}
    ]

    tools = [
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
        }
    ]

    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-35-turbo")
    
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        msg = response.choices[0].message
        
        # Tool execution loop
        if msg.tool_calls:
            messages.append(msg) # append assistant tool call
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                tool_result = {"error": "Tool not found"}
                if func_name == "faraday_mass_calculation":
                    tool_result = st.faraday_mass_calculation(**args)
                elif func_name == "faraday_thickness_calculation":
                    tool_result = st.faraday_thickness_calculation(**args)
                elif func_name == "current_density_calculation":
                    tool_result = st.current_density_calculation(**args)
                    
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result)
                })
                
            # Get final answer after tool results
            second_response = client.chat.completions.create(
                model=deployment_name,
                messages=messages
            )
            final_answer = second_response.choices[0].message.content
        else:
            final_answer = msg.content

        return AskResponse(answer=final_answer, sources=results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return AskResponse(answer=f"Virhe kielimallin käytössä: {str(e)}", sources=results)

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
