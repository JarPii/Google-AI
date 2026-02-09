FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg binary, lxml, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ api/
COPY scripts/ scripts/
COPY static/ static/
COPY config.example.yaml .

# Pre-download the embedding model at build time so startup is fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"

EXPOSE 8000

CMD ["uvicorn", "api.rag_api:app", "--host", "0.0.0.0", "--port", "8000"]
