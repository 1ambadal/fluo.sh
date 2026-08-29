# Multi-stage Dockerfile for AI Language Learner

# --- Stage 1: Build Frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --prefer-offline

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Runtime ---
FROM python:3.11-slim-bookworm

# Only runtime system libs — no curl, no build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps — wheels only, no cache left behind
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt \
 || pip install --no-cache-dir -r requirements.txt

# Application code
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# HuggingFace cache lives in a mounted volume, not the image
ENV HF_HOME=/app/.cache/huggingface
ENV PYTHONUNBUFFERED=1

# Entrypoint handles first-run model download into the volume
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
