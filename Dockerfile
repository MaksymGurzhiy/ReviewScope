# =====================================================
# ReviewScope - Backend (FastAPI + ML pipeline)
# =====================================================
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/cache/hf \
    TRANSFORMERS_CACHE=/cache/hf

WORKDIR /app

# System deps for some Python wheels (psycopg2, lxml, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY src ./src
COPY data/test ./data/test
COPY .env.example ./.env.example

# Pre-create data directories
RUN mkdir -p /cache/hf /app/data/raw

EXPOSE 8000

# Railway / Render inject PORT; fallback 8000 for local docker-compose.
HEALTHCHECK --interval=30s --timeout=15s --start-period=180s --retries=5 \
    CMD /bin/sh -c "curl -sf http://127.0.0.1:${PORT:-8000}/api/health" || exit 1

CMD ["/bin/sh", "-c", "exec uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
