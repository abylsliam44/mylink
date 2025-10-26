FROM python:3.11-slim

WORKDIR /app

# System deps (minimal for prod)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# App files
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start script with migrations
CMD ["bash", "-c", "alembic upgrade head || echo '⚠️ Migration failed, continuing...' && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

