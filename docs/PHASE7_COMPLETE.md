# Phase 7: Content Scheduling

**Status:** ✅ Complete  
**Implementation Date:** 2026-09-03  
**Files Created/Modified:** 4 files  
**Tests Added:** 29 tests  
**Dependencies Added:** APScheduler 3.11.3

---

## Overview

Phase 7 implements a content scheduling system using **APScheduler** for background job scheduling with **SQLAlchemy** for persistent job state. This enables:

- Schedule Instagram posts for future publishing
- Schedule Reels with video content
- Automatic retry with exponential backoff
- Job status tracking and cancellation
- Query statistics and job history

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Scheduler Service                         │
│              (APScheduler + SQLAlchemy)                     │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────▼─────────────┐
        │   Job State (SQLAlchemy)│
        │   - pending, running    │
        │   - succeeded, failed   │
        │   - retrying, cancelled │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │   APScheduler Triggers  │
        │   - DateTrigger         │
        │   - IntervalTrigger     │
        │   - CronTrigger         │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  Job Handlers           │
        │  - publish_instagram_   │
        │    post                 │
        │  - publish_instagram_   │
        │    reel                 │
        │  - publish_instagram_   │
        │    carousel             │
        └─────────────────────────┘
```

---

## What Was Implemented

### 1. Scheduler Service (`backend/app/services/scheduler.py`)

**Key Classes:**

- **`SchedulerService`** - Main scheduling service with job execution

**Methods:**
| Method | Description |
|--------|-------------|
| `start()` | Start the APScheduler background scheduler |
| `stop()` | Stop the scheduler gracefully |
| `schedule_post()` | Schedule an Instagram post |
| `schedule_reel()` | Schedule an Instagram Reel |
| `cancel_job()` | Cancel a pending job |
| `get_job()` | Get job by ID |
| `list_jobs()` | List jobs with optional status filter |
| `get_stats()` | Get job statistics |
| `update_job_status()` | Manually update job status |

**Handlers:**

- `publish_instagram_post` - Publish single image posts
- `publish_instagram_reel` - Publish video Reels
- `publish_instagram_carousel` - Publish multi-image carousels

### 2. Scheduler API (`backend/app/api/scheduler.py`)

**Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scheduler/schedule/post` | POST | Schedule Instagram post |
| `/scheduler/schedule/reel` | POST | Schedule Instagram Reel |
| `/scheduler/jobs` | GET | List all jobs |
| `/scheduler/jobs/{job_id}` | GET | Get job details |
| `/scheduler/jobs/{job_id}` | DELETE | Cancel a job |
| `/scheduler/stats` | GET | Job statistics |

**Request/Response Models:**

- `SchedulePostRequest` / `ScheduleReelRequest` - Input schemas
- `ScheduleResponse` - Job scheduling response
- `JobDetails` - Full job details
- `JobStats` - Aggregate statistics

### 3. Job State Model (`backend/app/models/scheduled_job.py`)

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Job unique identifier |
| `job_type` | str | Type of job (publish_post, publish_reel, etc.) |
| `entity_type` | str | Entity type (social_account) |
| `entity_id` | UUID | Related entity ID |
| `payload` | JSON | Job execution payload |
| `status` | enum | PENDING, RUNNING, SUCCEEDED, FAILED, RETRYING, CANCELLED |
| `run_at` | datetime | Scheduled execution time |
| `started_at` | datetime | When job started |
| `finished_at` | datetime | When job completed |
| `retry_count` | int | Current retry count |
| `max_retries` | int | Maximum retry attempts (default: 3) |
| `last_error` | str | Last error message |

---

## Usage Examples

### 1. Schedule a Post (API)

```bash
POST /scheduler/schedule/post
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "platform_id": "123e4567-e89b-12d3-a456-426614174000",
  "media_url": "https://example.com/image.jpg",
  "caption": "Great content! #instagram #marketing",
  "run_at": "2024-09-04T14:00:00Z"
}

# Response:
{
  "job_id": "abc123",
  "status": "pending",
  "run_at": "2024-09-04T14:00:00Z",
  "job_type": "publish_instagram_post"
}
```

### 2. Schedule a Reel (API)

```bash
POST /scheduler/schedule/reel
{
  "platform_id": "123e4567-e89b-12d3-a456-426614174000",
  "video_url": "https://example.com/reel.mp4",
  "caption": "Check out this video! #reels",
  "cover_url": "https://example.com/cover.jpg",
  "run_at": "2024-09-05T10:00:00Z"
}
```

### 3. List Jobs (API)

```bash
GET /scheduler/jobs?status=pending
Authorization: Bearer YOUR_ACCESS_TOKEN

# Response:
[
  {
    "id": "abc123",
    "job_type": "publish_instagram_post",
    "entity_type": "social_account",
    "entity_id": "123e4567-e89b-12d3-a456-426614174000",
    "payload": {
      "platform_id": "...",
      "media_url": "https://example.com/image.jpg",
      "caption": "Test caption"
    },
    "status": "pending",
    "run_at": "2024-09-04T14:00:00Z",
    "retry_count": 0,
    "max_retries": 3
  }
]
```

### 4. Get Job Stats (API)

```bash
GET /scheduler/stats
Authorization: Bearer YOUR_ACCESS_TOKEN

# Response:
{
  "total": 42,
  "pending": 5,
  "running": 1,
  "succeeded": 30,
  "failed": 3,
  "cancelled": 3
}
```

### 5. Cancel a Job (API)

```bash
DELETE /scheduler/jobs/abc123
Authorization: Bearer YOUR_ACCESS_TOKEN

# Response:
{
  "message": "Job abc123 cancelled successfully"
}
```

### 6. Schedule via Service (Python)

```python
from app.services.scheduler import scheduler_service
from datetime import datetime, timedelta

# Schedule a post
scheduler_service.schedule_post(
    platform_id=platform_uuid,
    media_url="https://example.com/image.jpg",
    caption="Scheduled post",
    run_at=datetime.utcnow() + timedelta(hours=2),
)

# Schedule a Reel
scheduler_service.schedule_reel(
    platform_id=platform_uuid,
    video_url="https://example.com/video.mp4",
    caption="Scheduled Reel",
    run_at=datetime.utcnow() + timedelta(hours=3),
)
```

---

## Retry Logic

Jobs are automatically retried on failure with exponential backoff:

```
1st retry: 60 seconds after failure
2nd retry: 120 seconds after first retry
3rd retry: 240 seconds after second retry
```

Configuration:

- `max_retries`: 3 (configurable per job)
- `base_retry_delay`: 60 seconds
- `max_retry_delay`: 3600 seconds (1 hour)

When max retries are exceeded, job status becomes `FAILED`.

---

## Job Status Flow

```
┌─────────┐
│ PENDING │
└───┬─────┘
    │ Scheduled time reached
    ▼
┌─────────┐
│RUNNING  │
└───┬─────┘
    │ Success
    ├───► SUCCEEDED
    │
    │ Failure
    ├───► RETRYING (if retries remaining)
    │       └───► PENDING (after delay)
    │
    └───► FAILED (max retries exceeded)

PENDING ────► CANCELLED (manual cancellation)
```

---

## Setup

### Install APScheduler

```bash
pip install APScheduler
```

### Initialize Scheduler in Main

The scheduler is started automatically in the lifespan:

```python
# backend/app/main.py
@app.get("/health")
async def health_check():
    """Health check."""
    return {"status": "ok", "scheduler_running": scheduler_service._is_started if scheduler_service else False}
```

### Configure Database

No additional configuration needed. The `scheduled_jobs` table is created automatically by SQLAlchemy.

---

## Testing

### Run Unit Tests

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/unit/test_scheduler.py -v
```

**Test Coverage:**

- ✅ Job scheduling (posts, Reels)
- ✅ Job status management
- ✅ Retry logic with exponential backoff
- ✅ Job cancellation
- ✅ Job listing with filters
- ✅ Job statistics
- ✅ Handler execution
- ✅ Error handling

---

## Integration with Instagram Platform

Jobs execute the Instagram platform service automatically:

```python
def _handle_publish_post(self, payload: dict) -> dict:
    # 1. Get job from database
    job = session.query(ScheduledJob).get(job_id)

    # 2. Parse payload
    platform_id = payload["platform_id"]
    media_url = payload["media_url"]
    caption = payload["caption"]

    # 3. Get Instagram platform
    instagram = self._get_instagram_platform(platform_id)

    # 4. Publish post
    result = instagram.publish_post(
        image_url=media_url,
        caption=caption
    )

    # 5. Update job status
    job.status = ScheduledJobStatus.SUCCEEDED
    job.finished_at = datetime.utcnow()
    session.commit()
```

---

## Error Handling

### Invalid Platform

```json
{
  "detail": "Social account not found: invalid-id"
}
```

### Invalid Datetime

```json
{
  "detail": "Invalid datetime format: Invalid isoformat string"
}
```

### Job Not Found

```json
{
  "detail": "Job not found: abc123"
}
```

### Cannot Cancel Running Job

```json
{
  "detail": "Cannot cancel job with status: running"
}
```

---

## Future Enhancements

- [ ] Cron-based scheduling (specific days/times)
- [ ] Recurring jobs (daily, weekly schedules)
- [ ] Job priority queue
- [ ] Bulk job scheduling
- [ ] Job templates (reusable configurations)
- [ ] Email notifications for job completion
- [ ] Job history export (CSV/JSON)
- [ ] Rate limiting awareness per Instagram quota

---

## Related Documentation

- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Phase 6: Instagram Integration](PHASE6_COMPLETE.md)
- [Architecture: Phase 1 Scheduler](docs/ARCHITECTURE.md)
