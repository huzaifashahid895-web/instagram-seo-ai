# backend/app/api/scheduler.py
# Cost classification: FREE + OPEN SOURCE
"""
Scheduler API endpoints for managing scheduled content publishing jobs.

Endpoints:
- POST /scheduler/schedule/post - Schedule a post
- POST /scheduler/schedule/reel - Schedule a Reel
- GET /scheduler/jobs - List scheduled jobs
- GET /scheduler/jobs/{job_id} - Get job details
- DELETE /scheduler/jobs/{job_id} - Cancel a job
- GET /scheduler/stats - Job statistics
"""

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import UUID

from app.config import settings
from app.core.db import get_db
from app.models.scheduled_job import ScheduledJob, ScheduledJobStatus
from app.services.scheduler import SchedulerService, scheduler_service

router = APIRouter()


# Pydantic schemas
class SchedulePostRequest(BaseModel):
    """Request to schedule a post."""
    platform_id: str  # Social account ID as string
    media_url: str
    caption: str = ""
    run_at: str  # ISO format datetime string


class ScheduleReelRequest(BaseModel):
    """Request to schedule a Reel."""
    platform_id: str
    video_url: str
    caption: str = ""
    cover_url: str | None = None
    run_at: str


class ScheduleResponse(BaseModel):
    """Response for scheduled job."""
    job_id: str
    status: str
    run_at: str
    job_type: str


class JobDetails(BaseModel):
    """Full job details."""
    id: str
    job_type: str
    entity_type: str | None
    entity_id: str | None
    payload: dict
    status: str
    run_at: str
    started_at: str | None
    finished_at: str | None
    retry_count: int
    max_retries: int
    last_error: str | None
    created_at: str
    updated_at: str


class JobStats(BaseModel):
    """Job statistics."""
    total: int
    pending: int
    running: int
    succeeded: int
    failed: int
    cancelled: int


def get_scheduler_service() -> SchedulerService:
    """Get scheduler service, ensuring it's started."""
    if not scheduler_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler service not initialized"
        )
    return scheduler_service


@router.post("/schedule/post", response_model=ScheduleResponse)
async def schedule_post(
    request: SchedulePostRequest,
    scheduler: SchedulerService = Depends(get_scheduler_service),
    db: Session = Depends(get_db),
):
    """Schedule an Instagram post for publishing."""
    from app.models.social_account import SocialAccount
    
    # Validate platform exists
    platform_id = UUID(request.platform_id)
    account = db.query(SocialAccount).filter_by(id=platform_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Social account not found: {request.platform_id}"
        )
    
    # Parse run_at datetime
    try:
        run_at = request.run_at if isinstance(request.run_at, str) else str(request.run_at)
        from datetime import datetime
        run_datetime = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {e}"
        )
    
    # Schedule the job
    job = scheduler.schedule_post(
        platform_id=platform_id,
        media_url=request.media_url,
        caption=request.caption,
        run_at=run_datetime,
    )
    
    return ScheduleResponse(
        job_id=str(job.id),
        status=job.status.value,
        run_at=job.run_at.isoformat(),
        job_type=job.job_type,
    )


@router.post("/schedule/reel", response_model=ScheduleResponse)
async def schedule_reel(
    request: ScheduleReelRequest,
    scheduler: SchedulerService = Depends(get_scheduler_service),
    db: Session = Depends(get_db),
):
    """Schedule an Instagram Reel for publishing."""
    from app.models.social_account import SocialAccount
    
    # Validate platform exists
    platform_id = UUID(request.platform_id)
    account = db.query(SocialAccount).filter_by(id=platform_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Social account not found: {request.platform_id}"
        )
    
    # Parse run_at datetime
    try:
        run_at = request.run_at if isinstance(request.run_at, str) else str(request.run_at)
        from datetime import datetime
        run_datetime = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {e}"
        )
    
    # Schedule the job
    job = scheduler.schedule_reel(
        platform_id=platform_id,
        video_url=request.video_url,
        caption=request.caption,
        run_at=run_datetime,
        cover_url=request.cover_url,
    )
    
    return ScheduleResponse(
        job_id=str(job.id),
        status=job.status.value,
        run_at=job.run_at.isoformat(),
        job_type=job.job_type,
    )


@router.get("/jobs", response_model=List[JobDetails])
async def list_jobs(
    status_filter: str | None = None,
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    """List scheduled jobs with optional status filter."""
    status_enum = None
    if status_filter:
        try:
            status_enum = ScheduledJobStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    jobs = scheduler.list_jobs(status=status_enum)
    
    return [
        JobDetails(
            id=str(job.id),
            job_type=job.job_type,
            entity_type=job.entity_type,
            entity_id=str(job.entity_id) if job.entity_id else None,
            payload=json.loads(job.payload) if job.payload else {},
            status=job.status.value,
            run_at=job.run_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            finished_at=job.finished_at.isoformat() if job.finished_at else None,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            last_error=job.last_error,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
        )
        for job in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobDetails)
async def get_job(
    job_id: str,
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    """Get details of a scheduled job."""
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    job = scheduler.get_job(job_uuid)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )
    
    return JobDetails(
        id=str(job.id),
        job_type=job.job_type,
        entity_type=job.entity_type,
        entity_id=str(job.entity_id) if job.entity_id else None,
        payload=json.loads(job.payload) if job.payload else {},
        status=job.status.value,
        run_at=job.run_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
        last_error=job.last_error,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    """Cancel a pending scheduled job."""
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    success = scheduler.cancel_job(job_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )
    
    return {"message": f"Job {job_id} cancelled successfully"}


@router.get("/stats", response_model=JobStats)
async def get_stats(
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    """Get job statistics."""
    jobs = scheduler.list_jobs()
    
    stats = {
        "total": len(jobs),
        "pending": sum(1 for j in jobs if j.status == ScheduledJobStatus.PENDING),
        "running": sum(1 for j in jobs if j.status == ScheduledJobStatus.RUNNING),
        "succeeded": sum(1 for j in jobs if j.status == ScheduledJobStatus.SUCCEEDED),
        "failed": sum(1 for j in jobs if j.status == ScheduledJobStatus.FAILED),
        "cancelled": sum(1 for j in jobs if j.status == ScheduledJobStatus.CANCELLED),
    }
    
    return JobStats(**stats)
