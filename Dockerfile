# syntax=docker/dockerfile:1.7
# Single image that serves both the website and its API.
# Works on any container host; the reference free deployment is Render Free.

# ---------------------------------------------------------------------------
# Stage 1 — build the React frontend into static files
# ---------------------------------------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 — Python runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/app \
    TIKTOKEN_CACHE_DIR=/home/app/.cache/tiktoken \
    CREWAI_DISABLE_TELEMETRY=true \
    CREWAI_TRACING_ENABLED=false \
    OTEL_SDK_DISABLED=true \
    FRONTEND_DIST=/app/frontend/dist \
    DATABASE_URL=sqlite:////app/data/research.db \
    HOST=0.0.0.0 \
    PORT=8000

RUN useradd --create-home --home-dir /home/app --uid 10001 app
WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY constraints ./constraints
COPY src ./src
# Security floors for transitive dependencies (see constraints/security.txt).
RUN pip install -c constraints/security.txt ".[web]"

# Pre-fetch tokenizer files LiteLLM uses for token counting, so the running
# container never needs to download them (and works behind strict egress rules).
USER app
RUN python -c "import tiktoken; [tiktoken.get_encoding(e) for e in ('cl100k_base', 'o200k_base')]"
USER root

COPY --from=frontend /build/frontend/dist ./frontend/dist
RUN mkdir -p /app/data && chown -R app:app /app/data

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT', '8000'), timeout=4)" || exit 1

CMD ["research-team-web"]
