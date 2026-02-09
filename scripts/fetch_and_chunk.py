import argparse
import json
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

import httpx
import tiktoken
import trafilatura
import yaml
from pydantic import BaseModel


HEADERS = {
    "User-Agent": "SearchAssistant/1.0 (educational research bot; contact: admin@example.com)"
}


class DocumentChunk(BaseModel):
    id: str
    source_url: str
    title: str | None
    license: str | None
    language: str | None
    text: str
    tokens: int


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_sources(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def _is_wikipedia(url: str) -> bool:
    return "wikipedia.org/wiki/" in url


def _wiki_article_name(url: str) -> tuple[str, str]:
    """Return (lang, article_name) from a Wikipedia URL."""
    m = re.match(r"https?://(\w+)\.wikipedia\.org/wiki/(.+)", url)
    if not m:
        raise ValueError(f"Not a Wikipedia URL: {url}")
    return m.group(1), unquote(m.group(2))


def fetch_wikipedia(url: str) -> tuple[str, str]:
    """Fetch article plain text via Wikipedia REST API."""
    lang, title = _wiki_article_name(url)
    api_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/html/{title}"
    with httpx.Client(timeout=30.0, follow_redirects=True, headers=HEADERS) as client:
        resp = client.get(api_url)
        resp.raise_for_status()
    extracted = trafilatura.extract(resp.text, url=url) or ""
    return url, extracted


def fetch_text(url: str) -> tuple[str, str]:
    """Fetch and extract main text from a URL."""
    if _is_wikipedia(url):
        return fetch_wikipedia(url)
    with httpx.Client(timeout=30.0, follow_redirects=True, headers=HEADERS) as client:
        resp = client.get(url)
        resp.raise_for_status()
    extracted = trafilatura.extract(resp.text, url=url) or ""
    return str(resp.url), extracted


def chunk_text(text: str, target_tokens: int, overlap: int) -> Iterable[str]:
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    step = max(target_tokens - overlap, 1)
    for start in range(0, len(tokens), step):
        end = start + target_tokens
        chunk_tokens = tokens[start:end]
        yield enc.decode(chunk_tokens)


def main():
    parser = argparse.ArgumentParser(description="Fetch URLs and chunk into JSONL")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--sources", default="data/sources.jsonl")
    parser.add_argument("--out", default="data/chunks.jsonl")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    sources = load_sources(Path(args.sources))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    target_tokens = cfg["chunking"]["target_tokens"]
    overlap = cfg["chunking"]["overlap_tokens"]

    enc = tiktoken.get_encoding("cl100k_base")

    with out_path.open("w", encoding="utf-8") as f:
        for src in sources:
            try:
                final_url, text = fetch_text(src["url"])
            except Exception as exc:  # rare network errors; log and continue
                print(f"Failed to fetch {src['url']}: {exc}")
                continue
            if not text:
                print(f"Empty extract for {src['url']}")
                continue
            for idx, chunk in enumerate(chunk_text(text, target_tokens, overlap)):
                tokens = len(enc.encode(chunk))
                doc = DocumentChunk(
                    id=f"{src['url']}#c{idx}",
                    source_url=str(final_url),
                    title=src.get("title"),
                    license=src.get("license"),
                    language=src.get("language"),
                    text=chunk,
                    tokens=tokens,
                )
                f.write(doc.model_dump_json() + "\n")
    print(f"Wrote chunks to {out_path}")


if __name__ == "__main__":
    main()
