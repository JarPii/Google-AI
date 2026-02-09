#!/usr/bin/env bash
set -euo pipefail

CONFIG=${1:-config.yaml}
TOPIC=${2:-"electrochemical surface treatment"}

python scripts/suggest_sources.py --config "$CONFIG" --topic "$TOPIC"
python scripts/fetch_and_chunk.py --config "$CONFIG" --sources data/sources.jsonl --out data/chunks.jsonl
python scripts/embed_and_index.py --config "$CONFIG" --chunks data/chunks.jsonl
