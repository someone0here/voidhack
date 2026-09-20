# Production build: bundles the React frontend and FastAPI backend into a
# single deployable image/service. This is deliberate — it lets the whole
# app run on one free-tier host instead of paying for two, and it removes
# CORS entirely since the frontend is served from the same origin as the API.
#
# Local dev still uses docker-compose.yml (two separate hot-reloading
# services) — this Dockerfile is for deployment only.

# ---- Stage 1: build the frontend ------------------------------------------
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Empty VITE_API_URL -> api-client.ts falls back to relative paths, which
# resolve correctly once everything is served from one origin.
ENV VITE_API_URL=""
RUN npm run build

# ---- Stage 2: backend + baked-in frontend build ----------------------------
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

COPY backend/app ./app

# Drop the built frontend where main.py's static-file block expects it.
COPY --from=frontend-build /frontend/dist ./app/static

# Persistent SQLite file lives here; mount a volume at this path on whatever
# host you deploy to, or the database resets on every redeploy.
RUN mkdir -p /app/data
ENV DATABASE_URL=sqlite:////app/data/fraud_correlator.db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
