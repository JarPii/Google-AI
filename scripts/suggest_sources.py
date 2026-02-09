"""
suggest_sources.py – Ask Vertex AI (Gemini) for open-source URLs about
electrochemical surface treatment.  Falls back to a built-in seed list
when no Vertex credentials are available.
"""

import argparse
import json
import re
from pathlib import Path

import yaml
from pydantic import BaseModel


class SourceCandidate(BaseModel):
    url: str
    title: str | None = None
    license: str | None = None
    language: str | None = None
    year: int | None = None
    notes: str | None = None


# ── Prompt for Gemini ────────────────────────────────────────────────
PROMPT_TEMPLATE = """\
You are a research assistant specialising in electrochemical surface treatment
(electroplating, anodizing, electropolishing, passivation, conversion coatings)
and the engineering of surface-treatment plants (process, mechanical, electrical,
automation, commissioning).

List up to {max_per_topic} openly licensed web resources (articles, guides,
government publications, university course materials, open textbooks).
Include ONLY public-domain, government, CC-BY, or CC-BY-SA materials.
Exclude paywalled standards (ISO/ASTM full text) and proprietary vendor manuals.

Return **only** a JSON array (no markdown fences). Each object must have:
  url, title, license, language (ISO 639-1), year (int or null), notes.

Prefer Finnish and English sources.

Topic: {topic}
"""

# ── Built-in seed list (no Vertex needed) ────────────────────────────
SEED_SOURCES: list[dict] = [
    {
        "url": "https://chem.libretexts.org/Bookshelves/Analytical_Chemistry/Supplemental_Modules_(Analytical_Chemistry)/Electrochemistry/Electrolytic_Cells",
        "title": "LibreTexts – Electrolytic Cells",
        "license": "CC-BY",
        "language": "en",
        "year": 2023,
        "notes": "Open textbook chapter: electrolysis fundamentals.",
    },
    {
        "url": "https://chem.libretexts.org/Courses/University_of_Kentucky/UK%3A_General_Chemistry/18%3A_Electrochemistry",
        "title": "LibreTexts – Electrochemistry (University of Kentucky)",
        "license": "CC-BY-SA",
        "language": "en",
        "year": 2023,
        "notes": "Full university course module on electrochemistry.",
    },
    {
        "url": "https://ocw.mit.edu/courses/3-11-mechanics-of-materials-fall-1999/",
        "title": "MIT OCW – Mechanics of Materials",
        "license": "CC-BY-SA",
        "language": "en",
        "year": 1999,
        "notes": "Material science fundamentals applicable to coatings.",
    },
    {
        "url": "https://echa.europa.eu/understanding-clp",
        "title": "ECHA – Understanding CLP (GHS in EU)",
        "license": "government",
        "language": "en",
        "year": 2024,
        "notes": "EU chemicals classification and labelling guidance.",
    },
    {
        "url": "https://echa.europa.eu/regulations/reach/understanding-reach",
        "title": "ECHA – Understanding REACH",
        "license": "government",
        "language": "en",
        "year": 2024,
        "notes": "REACH regulation overview for chemicals used in plating.",
    },
    {
        "url": "https://www.osha.gov/metal-fumes",
        "title": "OSHA – Metal Fumes Safety",
        "license": "government",
        "language": "en",
        "year": 2023,
        "notes": "Occupational safety guidance for metal fume exposure.",
    },
    {
        "url": "https://www.osha.gov/chromium",
        "title": "OSHA – Hexavalent Chromium",
        "license": "government",
        "language": "en",
        "year": 2023,
        "notes": "Chromium(VI) exposure limits and controls in plating.",
    },
    {
        "url": "https://en.wikipedia.org/wiki/Electroplating",
        "title": "Wikipedia – Electroplating",
        "license": "CC-BY-SA",
        "language": "en",
        "year": 2024,
        "notes": "Overview article covering processes, baths, defects.",
    },
    {
        "url": "https://en.wikipedia.org/wiki/Anodizing",
        "title": "Wikipedia – Anodizing",
        "license": "CC-BY-SA",
        "language": "en",
        "year": 2024,
        "notes": "Anodizing process, types (I/II/III), electrolytes.",
    },
    {
        "url": "https://en.wikipedia.org/wiki/Electropolishing",
        "title": "Wikipedia – Electropolishing",
        "license": "CC-BY-SA",
        "language": "en",
        "year": 2024,
        "notes": "Electropolishing theory and industrial applications.",
    },
    {
        "url": "https://en.wikipedia.org/wiki/Passivation_(chemistry)",
        "title": "Wikipedia – Passivation",
        "license": "CC-BY-SA",
        "language": "en",
        "year": 2024,
        "notes": "Chemical and electrochemical passivation methods.",
    },
    {
        "url": "https://en.wikipedia.org/wiki/Conversion_coating",
        "title": "Wikipedia – Conversion coating",
        "license": "CC-BY-SA",
        "language": "en",
        "year": 2024,
        "notes": "Chromate, phosphate, and other conversion coatings.",
    },
    {
        "url": "https://www.epa.gov/eg/metal-finishing-effluent-guidelines",
        "title": "EPA – Metal Finishing Effluent Guidelines",
        "license": "government",
        "language": "en",
        "year": 2023,
        "notes": "US EPA wastewater/effluent rules for metal finishing.",
    },
    {
        "url": "https://fi.wikipedia.org/wiki/Galvanointi",
        "title": "Wikipedia (FI) – Galvanointi",
        "license": "CC-BY-SA",
        "language": "fi",
        "year": 2024,
        "notes": "Suomenkielinen yleiskatsaus galvanointiin.",
    },
    {
        "url": "https://fi.wikipedia.org/wiki/Anodisointi",
        "title": "Wikipedia (FI) – Anodisointi",
        "license": "CC-BY-SA",
        "language": "fi",
        "year": 2024,
        "notes": "Suomenkielinen yleiskatsaus anodisointiin.",
    },
]


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _extract_json_array(text: str) -> list[dict]:
    """Try to pull a JSON array out of model output (may have markdown fences)."""
    text = text.strip()
    # Strip possible ```json ... ``` wrapping
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        return json.loads(m.group())
    return json.loads(text)


def suggest_via_vertex(cfg: dict, topic: str) -> list[SourceCandidate]:
    """Call Gemini via Vertex AI and return parsed candidates."""
    from vertexai.generative_models import GenerativeModel
    import vertexai

    v = cfg["vertex"]
    vertexai.init(project=v["project_id"], location=v["location"])
    model = GenerativeModel(v["model"])

    prompt = PROMPT_TEMPLATE.format(
        max_per_topic=cfg["sources"]["max_per_topic"],
        topic=topic,
    )
    response = model.generate_content(prompt)
    parsed = _extract_json_array(response.text)
    return [SourceCandidate(**item) for item in parsed]


def suggest_sources(cfg: dict, topic: str) -> list[SourceCandidate]:
    """Try Vertex first; fall back to built-in seed list."""
    try:
        candidates = suggest_via_vertex(cfg, topic)
        if candidates:
            print(f"Vertex AI returned {len(candidates)} candidates")
            return candidates
    except Exception as exc:
        print(f"Vertex AI unavailable ({exc}), using built-in seed list")

    # Fallback: return seed list
    return [SourceCandidate(**s) for s in SEED_SOURCES]


def main():
    parser = argparse.ArgumentParser(description="Suggest open resources via Vertex AI")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    parser.add_argument("--topic", default="electrochemical surface treatment", help="Topic to search")
    parser.add_argument("--out", default="data/sources.jsonl", help="Output JSONL path")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    candidates = suggest_sources(cfg, args.topic)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for c in candidates:
            f.write(c.model_dump_json() + "\n")
    print(f"Wrote {len(candidates)} candidates to {out_path}")


if __name__ == "__main__":
    main()
