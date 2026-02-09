import argparse
import json
from pathlib import Path

import numpy as np
import psycopg
import yaml
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer


CREATE_EXTENSION = "CREATE EXTENSION IF NOT EXISTS vector"
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS {schema}.{table} (
    id TEXT PRIMARY KEY,
    source_url TEXT,
    title TEXT,
    license TEXT,
    language TEXT,
    content TEXT,
    tokens INT,
    embedding vector(1024)
)
"""
UPSERT = """
INSERT INTO {schema}.{table} (id, source_url, title, license, language, content, tokens, embedding)
VALUES (%(id)s, %(source_url)s, %(title)s, %(license)s, %(language)s, %(content)s, %(tokens)s, %(embedding)s)
ON CONFLICT (id) DO UPDATE SET
    source_url = EXCLUDED.source_url,
    title = EXCLUDED.title,
    license = EXCLUDED.license,
    language = EXCLUDED.language,
    content = EXCLUDED.content,
    tokens = EXCLUDED.tokens,
    embedding = EXCLUDED.embedding
"""


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_chunks(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def main():
    parser = argparse.ArgumentParser(description="Embed chunks and upsert into Postgres/pgvector")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--chunks", default="data/chunks.jsonl")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    db_cfg = cfg["postgres"]
    emb_cfg = cfg["embedding"]

    model = SentenceTransformer(emb_cfg["model_name"], device=emb_cfg.get("device", "cpu"))

    conn_str = (
        f"host={db_cfg['host']} port={db_cfg['port']} dbname={db_cfg['database']} "
        f"user={db_cfg['user']} password={db_cfg['password']}"
    )
    with psycopg.connect(conn_str) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(CREATE_EXTENSION)
            cur.execute(CREATE_TABLE.format(schema=db_cfg["schema"], table=db_cfg["table"]))
            conn.commit()

        batch_ids = []
        batch_texts = []
        batch_rows = []
        for row in load_chunks(Path(args.chunks)):
            batch_ids.append(row["id"])
            batch_texts.append(row["text"])
            batch_rows.append(row)
            if len(batch_texts) >= emb_cfg.get("batch_size", 16):
                embeddings = model.encode(batch_texts, normalize_embeddings=True)
                _upsert_batch(conn, db_cfg, batch_rows, embeddings)
                batch_ids.clear(); batch_texts.clear(); batch_rows.clear()
        if batch_texts:
            embeddings = model.encode(batch_texts, normalize_embeddings=True)
            _upsert_batch(conn, db_cfg, batch_rows, embeddings)
        conn.commit()
    print("Embedding and upsert complete")


def _upsert_batch(conn, db_cfg, rows, embeddings: np.ndarray):
    with conn.cursor() as cur:
        for row, emb in zip(rows, embeddings):
            cur.execute(
                UPSERT.format(schema=db_cfg["schema"], table=db_cfg["table"]),
                {
                    "id": row["id"],
                    "source_url": row["source_url"],
                    "title": row.get("title"),
                    "license": row.get("license"),
                    "language": row.get("language"),
                    "content": row["text"],
                    "tokens": row.get("tokens", 0),
                    "embedding": emb.tolist(),
                },
            )
    conn.commit()


if __name__ == "__main__":
    main()
