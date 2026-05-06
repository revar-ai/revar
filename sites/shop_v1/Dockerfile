# SPDX-License-Identifier: Apache-2.0
# Multi-stage build for shop_v1: build the Vite SPA, then copy into a slim Python image
# that runs the FastAPI backend serving both /api/* and the SPA static files.

# ---------------- Frontend build ----------------
FROM node:20-alpine AS frontend
WORKDIR /build
COPY sites/shop_v1/frontend/package.json sites/shop_v1/frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY sites/shop_v1/frontend ./
RUN npm run build

# ---------------- Backend runtime ----------------
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////data/shop_v1.sqlite \
    DEFAULT_SEED=42 \
    REVAR_TEST_MODE=1 \
    STATIC_DIR=/app/static \
    LOG_LEVEL=info

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /data /app

WORKDIR /app

# Install shared-models first (cache-friendly)
COPY packages/shared-models /tmp/shared-models
RUN pip install /tmp/shared-models && rm -rf /tmp/shared-models

# Install backend dependencies
COPY sites/shop_v1/backend/pyproject.toml /tmp/backend/pyproject.toml
RUN cd /tmp/backend && pip install \
      "fastapi>=0.110" \
      "uvicorn[standard]>=0.27" \
      "sqlmodel>=0.0.16" \
      "pydantic>=2.6" \
      "pydantic-settings>=2.2" \
      "python-multipart>=0.0.9" \
      "argon2-cffi>=23.1" \
      "itsdangerous>=2.1" \
      "email-validator>=2.1"

# Copy backend source
COPY sites/shop_v1/backend/app /app/app

# Copy built SPA from the frontend stage
COPY --from=frontend /build/dist /app/static

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -fsS http://localhost:8080/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
