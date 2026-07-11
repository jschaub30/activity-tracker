# Multi-stage: React build + FastAPI runtime (single Fly process)
# syntax=docker/dockerfile:1

# ----- Frontend -----
FROM node:24-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Same-origin API on Fly — leave VITE_API_URL unset (production uses relative /api)
RUN npm run build

# ----- Backend -----
FROM python:3.12-slim-bookworm AS backend

# System deps for curl-cffi / garminconnect
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

WORKDIR /app

# Install Python deps first (better layer cache)
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
COPY backend/src ./src
RUN uv sync --frozen --no-dev

COPY --from=frontend /frontend/dist /app/frontend/dist

# Runtime data lives on Fly volume at /data (often root-owned — run as root for writes)
RUN mkdir -p /data

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/frontend/dist \
    DATABASE_URL=sqlite:////data/garmin_tracker.db \
    DEBUG=false \
    DEFAULT_TIMEZONE=America/Denver \
    CORS_ORIGINS=* \
    PORT=8000

EXPOSE 8000

# Single worker: Garmin MFA state is in-process memory
CMD ["sh", "-c", "mkdir -p /data && uvicorn garmin_tracker.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
