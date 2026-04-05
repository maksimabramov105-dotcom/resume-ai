# ── Stage 1: build React app ──────────────────────────────────────────────────
FROM node:20-slim AS frontend
WORKDIR /app/webapp
COPY webapp/package.json webapp/package-lock.json* ./
RUN npm ci --quiet
COPY webapp/ ./
RUN npm run build          # outputs to /app/webapp/dist

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.11-slim AS backend
WORKDIR /app

# System deps (Cyrillic PDF fonts need libfreetype)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY bot/   bot/
COPY api/   api/
COPY run.py .

# Copy built React app from stage 1
COPY --from=frontend /app/webapp/dist webapp/dist

EXPOSE 8000
CMD ["python", "run.py"]
