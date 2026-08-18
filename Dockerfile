# Multi-stage Dockerfile for Sri Clips (FastAPI Backend + Next.js Frontend)

FROM python:3.11-slim as base

# Install system dependencies (FFmpeg, OpenMP libgomp1 for CTranslate2, libsndfile1, Node.js 20, Git, Curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgomp1 \
    libsndfile1 \
    curl \
    git \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements and install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy frontend package.json and install Node dependencies
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install

# Copy application source code
COPY . .

# Build Next.js production bundle
RUN cd frontend && npm run build

# Expose ports: 8000 (FastAPI API) and 3000 (Next.js UI)
EXPOSE 8000 3000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=3000

# Start script
CMD ["python", "run_production.py"]
