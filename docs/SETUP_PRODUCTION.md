# Production Deployment Guide

This guide covers migrating from SQLite to PostgreSQL, adding MinIO for object storage, and configuring Celery for background tasks.

## Overview

**Current Setup (Development):**

- SQLite database
- Local file storage
- APScheduler for jobs
- Single-process uvicorn

**Production Setup:**

- PostgreSQL database
- MinIO S3-compatible storage
- Celery + Redis for distributed tasks
- Multi-worker deployment

---

## Part 1: PostgreSQL Setup

### Option A: Docker Compose (Recommended)

Already configured in `docker-compose.yml`. Just start it:

```cmd
cd "D:\Instagram SEO"
docker-compose up postgres -d
```

The configuration:

```yaml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_DB: aism
    POSTGRES_USER: aism
    POSTGRES_PASSWORD: aism_dev_pw
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

### Option B: Install PostgreSQL Locally

1. Download: https://www.postgresql.org/download/windows/
2. Install PostgreSQL 16
3. During installation:

   - Port: 5432
   - Password: Choose a strong password
   - Locale: Default

4. Create database:

```sql
-- Open psql or pgAdmin
CREATE DATABASE aism;
CREATE USER aism WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE aism TO aism;
```

### Step 2: Install PostgreSQL Driver

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
pip install psycopg[binary]==3.1.18
```

### Step 3: Update Database URL

Edit `D:\Instagram SEO\.env`:

```env
# Old (SQLite):
# DATABASE_URL=sqlite:///./aism.db

# New (PostgreSQL):
DATABASE_URL=postgresql+psycopg://aism:aism_dev_pw@localhost:5432/aism
```

### Step 4: Run Migrations

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
alembic upgrade head
```

### Step 5: Verify Migration

```cmd
python -c "from app.core.db import init_db; init_db(); print('✅ PostgreSQL connected')"
```

---

## Part 2: MinIO Setup (S3-Compatible Storage)

### Step 1: Start MinIO with Docker

```cmd
cd "D:\Instagram SEO"
docker-compose up minio -d
```

The configuration in `docker-compose.yml`:

```yaml
minio:
  image: minio/minio:latest
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  ports:
    - "9000:9000" # API
    - "9001:9001" # Console
  volumes:
    - minio_data:/data
```

### Step 2: Access MinIO Console

1. Open: http://localhost:9001
2. Login:
   - Username: `minioadmin`
   - Password: `minioadmin`

### Step 3: Create Buckets

In MinIO console:

1. Click "Buckets" > "Create Bucket"
2. Create these buckets:

   - `aism-raw` (uploaded content)
   - `aism-processed` (analyzed media)
   - `aism-generated` (AI-generated content)
   - `aism-published` (published to Instagram)
   - `aism-thumbnails` (preview images)
   - `aism-audio` (audio files)

3. Set access policy to "Public" for thumbnails bucket

### Step 4: Install MinIO Client (boto3)

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
pip install boto3==1.34.51
```

### Step 5: Update Storage Configuration

Edit `D:\Instagram SEO\.env`:

```env
# Storage backend
STORAGE_BACKEND=s3  # Options: local, s3
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_PREFIX=aism-
S3_REGION=us-east-1
```

### Step 6: Update Storage Service

The app already has S3 storage abstraction. Just restart:

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
uvicorn app.main:app --reload
```

---

## Part 3: Celery + Redis Setup

### Step 1: Start Redis with Docker

```cmd
cd "D:\Instagram SEO"
docker-compose up redis -d
```

Configuration:

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
```

### Step 2: Install Celery

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
pip install celery[redis]==5.3.6 redis==5.0.1
```

### Step 3: Create Celery Application

Create `D:\Instagram SEO\backend\app\celery_app.py`:

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "aism",
    broker=f"redis://localhost:6379/0",
    backend=f"redis://localhost:6379/1",
    include=[
        "app.tasks.content",
        "app.tasks.analytics",
        "app.tasks.comments",
        "app.tasks.publishing",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 min warning
)
```

### Step 4: Create Task Modules

Create `D:\Instagram SEO\backend\app\tasks\__init__.py`:

```python
from app.celery_app import celery_app

__all__ = ["celery_app"]
```

Create `D:\Instagram SEO\backend\app\tasks\content.py`:

```python
from app.celery_app import celery_app
from app.core.db import get_db
from app.services.media_analysis import analyze_video, analyze_image
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.analyze_content")
def analyze_content_task(asset_id: int):
    """Analyze uploaded content in background."""
    logger.info(f"Analyzing content asset {asset_id}")

    db = next(get_db())
    try:
        # Fetch asset, analyze, update DB
        # Implementation depends on your models
        pass
    finally:
        db.close()

    return {"asset_id": asset_id, "status": "analyzed"}

@celery_app.task(name="tasks.generate_caption")
def generate_caption_task(content_id: int):
    """Generate AI caption in background."""
    logger.info(f"Generating caption for content {content_id}")
    # LLM call here
    return {"content_id": content_id, "status": "generated"}
```

### Step 5: Start Celery Worker

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
celery -A app.celery_app worker --loglevel=info --pool=solo
```

_Note: Use `--pool=solo` on Windows. For Linux/Mac, use `--pool=prefork`_

### Step 6: Start Celery Beat (Scheduler)

In a new terminal:

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
celery -A app.celery_app beat --loglevel=info
```

### Step 7: Configure Scheduled Tasks

Update `app/celery_app.py` with periodic tasks:

```python
celery_app.conf.beat_schedule = {
    "sync-instagram-comments": {
        "task": "tasks.sync_comments",
        "schedule": 300.0,  # Every 5 minutes
    },
    "fetch-analytics": {
        "task": "tasks.fetch_analytics",
        "schedule": 3600.0,  # Every hour
    },
    "publish-scheduled-posts": {
        "task": "tasks.publish_scheduled",
        "schedule": 60.0,  # Every minute
    },
}
```

---

## Part 4: Full Production Stack

### Option A: Docker Compose (All Services)

Start everything:

```cmd
cd "D:\Instagram SEO"
docker-compose up -d
```

This starts:

- PostgreSQL
- Redis
- MinIO
- Chroma (vector DB)
- Backend API
- Frontend
- Celery Worker
- Celery Beat

### Option B: Manual Start (Development)

Terminal 1 - Backend API:

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Terminal 2 - Celery Worker:

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
celery -A app.celery_app worker --loglevel=info --pool=solo
```

Terminal 3 - Celery Beat:

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
celery -A app.celery_app beat --loglevel=info
```

Terminal 4 - Frontend:

```cmd
cd "D:\Instagram SEO\frontend"
npm run build
npm run preview
```

---

## Part 5: Production Configuration

### Step 1: Update Environment Variables

Create `D:\Instagram SEO\.env.production`:

```env
# Database
DATABASE_URL=postgresql+psycopg://aism:STRONG_PASSWORD@postgres:5432/aism

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO / S3
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=CHANGE_THIS_IN_PRODUCTION
S3_BUCKET_PREFIX=aism-
S3_REGION=us-east-1

# Chroma
CHROMA_HOST=chroma
CHROMA_PORT=8000

# Security
JWT_SECRET=GENERATE_NEW_RANDOM_SECRET_HERE
ENCRYPTION_KEY=GENERATE_NEW_RANDOM_KEY_HERE

# Instagram
INSTAGRAM_APP_ID=your_app_id
INSTAGRAM_APP_SECRET=your_app_secret
INSTAGRAM_REDIRECT_URI=https://yourdomain.com/social-accounts/callback
INSTAGRAM_WEBHOOK_VERIFY_TOKEN=RANDOM_WEBHOOK_TOKEN

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

### Step 2: Generate Secrets

```python
# Generate secure secrets:
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('WEBHOOK_TOKEN=' + secrets.token_hex(32))"
```

### Step 3: Update Docker Compose

Production `docker-compose.yml` additions:

```yaml
services:
  backend:
    build: ./backend
    env_file: .env.production
    depends_on:
      - postgres
      - redis
      - minio
      - chroma
    ports:
      - "8000:8000"
    restart: unless-stopped

  celery_worker:
    build: ./backend
    command: celery -A app.celery_app worker --loglevel=info
    env_file: .env.production
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  celery_beat:
    build: ./backend
    command: celery -A app.celery_app beat --loglevel=info
    env_file: .env.production
    depends_on:
      - redis
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - frontend
```

---

## Part 6: Monitoring & Logging

### Step 1: Add Flower (Celery Monitoring)

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
pip install flower==2.0.1
```

Start Flower:

```cmd
celery -A app.celery_app flower --port=5555
```

Access: http://localhost:5555

### Step 2: Setup Logging

All logs go to stdout/stderr, captured by Docker:

```cmd
# View logs:
docker-compose logs -f backend
docker-compose logs -f celery_worker
```

### Step 3: Database Backups

```bash
# Automated backup script:
#!/bin/bash
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL backup
docker exec postgres pg_dump -U aism aism > "$BACKUP_DIR/db_$DATE.sql"

# MinIO backup (using mc client)
mc mirror minio/aism-raw "$BACKUP_DIR/minio-raw-$DATE"
```

---

## Part 7: Performance Tuning

### PostgreSQL Tuning

Edit `docker-compose.yml`:

```yaml
postgres:
  command:
    - "postgres"
    - "-c"
    - "shared_buffers=256MB"
    - "-c"
    - "max_connections=100"
    - "-c"
    - "work_mem=16MB"
```

### Celery Workers

Scale workers:

```cmd
celery -A app.celery_app worker --concurrency=4 --loglevel=info
```

### Redis Configuration

For persistence:

```yaml
redis:
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
```

---

## Part 8: Health Checks

Add to `docker-compose.yml`:

```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3

postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U aism"]
    interval: 10s
    timeout: 5s
    retries: 5

redis:
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 3s
    retries: 3
```

---

## Troubleshooting

### PostgreSQL Connection Issues

```cmd
# Test connection:
python -c "import psycopg; conn = psycopg.connect('postgresql://aism:password@localhost:5432/aism'); print('✅ Connected')"
```

### MinIO Access Issues

```cmd
# Install mc client:
docker run --rm -it --entrypoint=/bin/sh minio/mc
mc alias set local http://localhost:9000 minioadmin minioadmin
mc ls local
```

### Celery Tasks Not Running

```cmd
# Check Redis:
redis-cli ping

# Check Celery status:
celery -A app.celery_app inspect active
celery -A app.celery_app inspect stats
```

### High Memory Usage

- Reduce Celery worker concurrency
- Use PostgreSQL connection pooling
- Limit Ollama context window
- Enable Redis maxmemory policy

---

## Migration Checklist

- [ ] Backup SQLite database
- [ ] Start PostgreSQL
- [ ] Run migrations
- [ ] Verify data integrity
- [ ] Start MinIO
- [ ] Create buckets
- [ ] Migrate uploaded files to MinIO
- [ ] Start Redis
- [ ] Install Celery
- [ ] Create task modules
- [ ] Start Celery worker + beat
- [ ] Update environment variables
- [ ] Test all endpoints
- [ ] Monitor logs for errors
- [ ] Setup automated backups

---

## Production Deployment Checklist

- [ ] Use `.env.production` with strong secrets
- [ ] Enable HTTPS with SSL certificates
- [ ] Configure firewall rules
- [ ] Setup monitoring (Flower, logs)
- [ ] Configure automated backups
- [ ] Test disaster recovery
- [ ] Document runbook procedures
- [ ] Setup alerting
- [ ] Load test the application
- [ ] Create deployment automation

---

Your production infrastructure is now ready!
