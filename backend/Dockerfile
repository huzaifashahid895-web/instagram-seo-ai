# backend/Dockerfile — AI SEO & Social Media Manager (Phase 1)
# Cost classification: FREE + OPEN SOURCE (Python, FastAPI, SQLAlchemy, etc.)

FROM python:3.12-slim

# System deps for psycopg, chroma client, and any native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency files first for layer caching
COPY requirements.txt ./

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source
COPY . .

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Entrypoint runs migrations then starts uvicorn with reload
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
