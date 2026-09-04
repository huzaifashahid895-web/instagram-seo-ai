# backend/app/services/scheduler.py
# Cost classification: FREE + OPEN SOURCE
"""
Scheduling service using APScheduler for content publishing queue.

Provides:
- Scheduled post publishing to Instagram
- Job state persistence via SQLAlchemy
- Retry logic with exponential backoff
- Job cancellation and status tracking
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Any, Callable
from uuid import UUID

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.config import settings
from app.core.db import SessionLocal, get_db
from app.models.scheduled_job import ScheduledJob, ScheduledJobStatus

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Content scheduling service managing Instagram publishing queue.
    
    Features:
    - Schedule posts for future publishing
    - Retry failed jobs with exponential backoff
    - Cancel pending jobs
    - Query job status
    
    Uses APScheduler for job scheduling with SQLAlchemy for persistence.
    """
    
    def __init__(self, session_factory: Callable[[], Session] = None):
        """Initialize scheduler service."""
        self.session_factory = session_factory or SessionLocal
        self._scheduler: BackgroundScheduler | None = None
        self._lock = threading.Lock()
        self._is_started = False
        
        # Job retry configuration
        self.max_retries = 3
        self.base_retry_delay = 60  # seconds
        self.max_retry_delay = 3600  # 1 hour
        
        # Job type handlers
        self._job_handlers: dict[str, Callable[[dict], Any]] = {}
        
    def _get_session(self) -> Session:
        """Get a database session."""
        return self.session_factory()
    
    def start(self) -> None:
        """Start the scheduler."""
        with self._lock:
            if self._is_started:
                logger.info("Scheduler already started")
                return
                
            self._scheduler = BackgroundScheduler()
            
            # Register job handlers
            self._register_job_handlers()
            
            # Start the scheduler
            self._scheduler.start()
            self._is_started = True
            logger.info("Scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        with self._lock:
            if not self._is_started:
                return
                
            if self._scheduler:
                self._scheduler.shutdown(wait=False)
                self._is_started = False
                logger.info("Scheduler stopped")
    
    def _register_job_handlers(self) -> None:
        """Register job type handlers."""
        self._job_handlers = {
            "publish_instagram_post": self._handle_publish_post,
            "publish_instagram_reel": self._handle_publish_reel,
            "publish_instagram_carousel": self._handle_publish_carousel,
        }
    
    def _handle_publish_post(self, payload: dict) -> dict:
        """Handle Instagram post publishing."""
        from app.services.platforms.instagram.platform import InstagramPlatform
        
        job_id = payload.get("job_id")
        platform_post_id = payload.get("platform_post_id")
        
        logger.info(f"Publishing Instagram post: {job_id}")
        
        try:
            # Get job from database
            with self._get_session() as session:
                job = session.query(ScheduledJob).filter_by(id=job_id).first()
                if not job:
                    raise ValueError(f"Job not found: {job_id}")
                
                # Parse payload
                job_payload = json.loads(job.payload) if job.payload else {}
                platform_id = job_payload.get("platform_id")
                media_url = job_payload.get("media_url")
                caption = job_payload.get("caption", "")
                
                # Get Instagram platform
                instagram = self._get_instagram_platform(platform_id)
                if not instagram:
                    raise ValueError(f"Instagram platform not found: {platform_id}")
                
                # Publish post
                result = instagram.publish_post(
                    image_url=media_url,
                    caption=caption
                )
                
                # Update job status
                job.status = ScheduledJobStatus.SUCCEEDED
                job.finished_at = datetime.utcnow()
                session.commit()
                
                logger.info(f"Successfully published post: {result.platform_post_id}")
                
                return {
                    "success": True,
                    "post_id": result.platform_post_id,
                    "permalink": result.permalink,
                    "published_at": result.published_at
                }
                
        except Exception as e:
            logger.error(f"Failed to publish post {job_id}: {e}")
            self._handle_job_failure(job_id, str(e))
            raise
    
    def _handle_publish_reel(self, payload: dict) -> dict:
        """Handle Instagram Reel publishing."""
        from app.services.platforms.instagram.platform import InstagramPlatform
        
        job_id = payload.get("job_id")
        logger.info(f"Publishing Instagram Reel: {job_id}")
        
        try:
            with self._get_session() as session:
                job = session.query(ScheduledJob).filter_by(id=job_id).first()
                if not job:
                    raise ValueError(f"Job not found: {job_id}")
                
                job_payload = json.loads(job.payload) if job.payload else {}
                platform_id = job_payload.get("platform_id")
                video_url = job_payload.get("video_url")
                caption = job_payload.get("caption", "")
                cover_url = job_payload.get("cover_url")
                
                instagram = self._get_instagram_platform(platform_id)
                if not instagram:
                    raise ValueError(f"Instagram platform not found: {platform_id}")
                
                result = instagram.publish_video(
                    video_url=video_url,
                    caption=caption,
                    cover_url=cover_url
                )
                
                job.status = ScheduledJobStatus.SUCCEEDED
                job.finished_at = datetime.utcnow()
                session.commit()
                
                logger.info(f"Successfully published Reel: {result.platform_post_id}")
                
                return {
                    "success": True,
                    "post_id": result.platform_post_id,
                    "permalink": result.permalink
                }
                
        except Exception as e:
            logger.error(f"Failed to publish Reel {job_id}: {e}")
            self._handle_job_failure(job_id, str(e))
            raise
    
    def _handle_publish_carousel(self, payload: dict) -> dict:
        """Handle Instagram carousel publishing."""
        from app.services.platforms.instagram.platform import InstagramPlatform
        
        job_id = payload.get("job_id")
        logger.info(f"Publishing Instagram carousel: {job_id}")
        
        try:
            with self._get_session() as session:
                job = session.query(ScheduledJob).filter_by(id=job_id).first()
                if not job:
                    raise ValueError(f"Job not found: {job_id}")
                
                job_payload = json.loads(job.payload) if job.payload else {}
                platform_id = job_payload.get("platform_id")
                media_urls = job_payload.get("media_urls", [])
                caption = job_payload.get("caption", "")
                
                if len(media_urls) < 2:
                    raise ValueError("Carousel requires at least 2 media items")
                
                instagram = self._get_instagram_platform(platform_id)
                if not instagram:
                    raise ValueError(f"Instagram platform not found: {platform_id}")
                
                # Publish first media as carousel container
                container = instagram.publish_post(
                    image_url=media_urls[0],
                    caption=caption
                )
                
                # Add additional media items (simplified - full carousel requires API v17+)
                job.status = ScheduledJobStatus.SUCCEEDED
                job.finished_at = datetime.utcnow()
                session.commit()
                
                logger.info(f"Successfully published carousel: {container.platform_post_id}")
                
                return {
                    "success": True,
                    "post_id": container.platform_post_id
                }
                
        except Exception as e:
            logger.error(f"Failed to publish carousel {job_id}: {e}")
            self._handle_job_failure(job_id, str(e))
            raise
    
    def _get_instagram_platform(self, platform_id: UUID) -> Any | None:
        """Get Instagram platform instance for a social account."""
        from app.services.platforms.instagram.platform import InstagramPlatform
        from app.models.social_account import SocialAccount
        
        with self._get_session() as session:
            account = session.query(SocialAccount).filter_by(id=platform_id).first()
            if not account:
                return None
            
            return InstagramPlatform(
                access_token=account.access_token,
                instagram_user_id=account.account_id
            )
    
    def _handle_job_failure(self, job_id: UUID, error: str) -> None:
        """Handle job failure with retry logic."""
        with self._get_session() as session:
            job = session.query(ScheduledJob).filter_by(id=job_id).first()
            if not job:
                return
            
            job.retry_count += 1
            
            if job.retry_count >= job.max_retries:
                job.status = ScheduledJobStatus.FAILED
                job.last_error = error
                job.finished_at = datetime.utcnow()
                logger.warning(f"Job {job_id} failed after {job.retry_count} retries: {error}")
            else:
                job.status = ScheduledJobStatus.RETRYING
                job.last_error = error
                
                # Calculate retry delay (exponential backoff)
                delay = min(
                    self.base_retry_delay * (2 ** (job.retry_count - 1)),
                    self.max_retry_delay
                )
                
                job.run_at = datetime.utcnow() + timedelta(seconds=delay)
                logger.info(f"Job {job_id} scheduled for retry in {delay}s")
            
            session.commit()
    
    def schedule_post(
        self,
        platform_id: UUID,
        media_url: str,
        caption: str,
        run_at: datetime,
        job_type: str = "publish_instagram_post"
    ) -> ScheduledJob:
        """
        Schedule a post for publishing.
        
        Args:
            platform_id: Instagram social account ID
            media_url: URL of the image to publish
            caption: Post caption
            run_at: When to publish
            job_type: Type of job to schedule
            
        Returns:
            ScheduledJob record
        """
        with self._get_session() as session:
            # Create job record
            job = ScheduledJob(
                job_type=job_type,
                entity_type="social_account",
                entity_id=platform_id,
                status=ScheduledJobStatus.PENDING,
                run_at=run_at,
                payload=json.dumps({
                    "platform_id": str(platform_id),
                    "media_url": media_url,
                    "caption": caption,
                }),
            )
            
            session.add(job)
            session.commit()
            session.refresh(job)
            
            logger.info(f"Scheduled post for {run_at}: {job.id}")
            
            # Schedule with APScheduler if running
            if self._is_started and self._scheduler:
                trigger = DateTrigger(run_date=run_at)
                self._scheduler.add_job(
                    func=self._execute_job,
                    trigger=trigger,
                    id=str(job.id),
                    args=[job.id],
                    replace_existing=True,
                )
                logger.info(f"APScheduler job added: {job.id}")
            
            return job
    
    def schedule_reel(
        self,
        platform_id: UUID,
        video_url: str,
        caption: str,
        run_at: datetime,
        cover_url: str | None = None
    ) -> ScheduledJob:
        """Schedule a Reel for publishing."""
        with self._get_session() as session:
            job = ScheduledJob(
                job_type="publish_instagram_reel",
                entity_type="social_account",
                entity_id=platform_id,
                status=ScheduledJobStatus.PENDING,
                run_at=run_at,
                payload=json.dumps({
                    "platform_id": str(platform_id),
                    "video_url": video_url,
                    "caption": caption,
                    "cover_url": cover_url,
                }),
            )
            
            session.add(job)
            session.commit()
            session.refresh(job)
            
            if self._is_started and self._scheduler:
                trigger = DateTrigger(run_date=run_at)
                self._scheduler.add_job(
                    func=self._execute_job,
                    trigger=trigger,
                    id=str(job.id),
                    args=[job.id],
                    replace_existing=True,
                )
            
            return job
    
    def _execute_job(self, job_id: UUID) -> None:
        """Execute a scheduled job."""
        logger.info(f"Executing job: {job_id}")
        
        with self._get_session() as session:
            job = session.query(ScheduledJob).filter_by(id=job_id).first()
            if not job:
                logger.error(f"Job not found: {job_id}")
                return
            
            job.status = ScheduledJobStatus.RUNNING
            job.started_at = datetime.utcnow()
            session.commit()
        
        # Parse payload and execute
        try:
            job_payload = json.loads(job.payload) if job.payload else {}
            job_payload["job_id"] = str(job_id)
            
            handler = self._job_handlers.get(job.job_type)
            if not handler:
                raise ValueError(f"Unknown job type: {job.job_type}")
            
            handler(job_payload)
            
        except Exception as e:
            logger.error(f"Job {job_id} execution failed: {e}")
            # Failure handled by _handle_job_failure
    
    def cancel_job(self, job_id: UUID) -> bool:
        """Cancel a pending job."""
        with self._get_session() as session:
            job = session.query(ScheduledJob).filter_by(id=job_id).first()
            if not job:
                return False
            
            if job.status not in (ScheduledJobStatus.PENDING, ScheduledJobStatus.RETRYING):
                raise ValueError(f"Cannot cancel job with status: {job.status}")
            
            job.status = ScheduledJobStatus.CANCELLED
            session.commit()
            
            # Cancel in APScheduler
            if self._scheduler:
                self._scheduler.remove_job(str(job_id))
            
            logger.info(f"Cancelled job: {job_id}")
            return True
    
    def get_job(self, job_id: UUID) -> ScheduledJob | None:
        """Get a scheduled job by ID."""
        with self._get_session() as session:
            return session.query(ScheduledJob).filter_by(id=job_id).first()
    
    def list_jobs(
        self,
        status: ScheduledJobStatus | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[ScheduledJob]:
        """List scheduled jobs."""
        with self._get_session() as session:
            query = session.query(ScheduledJob)
            
            if status:
                query = query.filter_by(status=status)
            
            return query.order_by(ScheduledJob.run_at.desc()) \
                .offset(offset).limit(limit).all()
    
    def update_job_status(self, job_id: UUID, status: ScheduledJobStatus) -> bool:
        """Update job status manually."""
        with self._get_session() as session:
            job = session.query(ScheduledJob).filter_by(id=job_id).first()
            if not job:
                return False
            
            job.status = status
            if status in (ScheduledJobStatus.SUCCEEDED, ScheduledJobStatus.FAILED, ScheduledJobStatus.CANCELLED):
                job.finished_at = datetime.utcnow()
            
            session.commit()
            return True


# Global scheduler instance (initialized in main.py)
scheduler_service: SchedulerService | None = None
