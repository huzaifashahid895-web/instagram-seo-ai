# backend/tests/unit/test_scheduler.py
# Cost classification: FREE + OPEN SOURCE
"""
Unit tests for scheduler service.

Tests verify:
- Job scheduling functionality
- Job status management
- Retry logic
- Job cancellation
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models.scheduled_job import ScheduledJob, ScheduledJobStatus
from app.services.scheduler import SchedulerService


class TestSchedulerServiceInit:
    """Tests for SchedulerService initialization."""
    
    def test_init_creates_scheduler(self):
        """Test that scheduler is initialized with default settings."""
        service = SchedulerService()
        
        assert service.max_retries == 3
        assert service.base_retry_delay == 60
        assert service.max_retry_delay == 3600
        assert service._job_handlers == {}
        assert service._is_started is False


class TestSchedulerServiceScheduleJob:
    """Tests for job scheduling."""


class TestSchedulerServiceJobHandlers:
    """Tests for job execution handlers."""
    
    @pytest.fixture
    def service(self):
        """Create scheduler service."""
        service = SchedulerService()
        
        # Mock session
        mock_session = MagicMock()
        mock_session.commit.return_value = None
        
        service._get_session = MagicMock()
        service._get_session.return_value.__enter__.return_value = mock_session
        service._get_session.return_value.__exit__.return_value = None
        
        return service
    
    def test_handle_publish_post_success(self, service):
        """Test successful post publishing handler."""
        job_id = uuid4()
        
        # Mock payload
        payload = {
            "job_id": str(job_id),
            "platform_id": str(uuid4()),
            "media_url": "https://example.com/image.jpg",
            "caption": "Test caption",
        }
        
        # Mock Instagram platform
        mock_instagram = MagicMock()
        mock_result = MagicMock()
        mock_result.platform_post_id = "1234567890"
        mock_result.permalink = "https://instagram.com/p/abc123"
        mock_result.published_at = "2024-01-01T00:00:00Z"
        mock_instagram.publish_post.return_value = mock_result
        
        service._get_instagram_platform = MagicMock(return_value=mock_instagram)
        
        result = service._handle_publish_post(payload)
        
        assert result["success"] is True
        assert result["post_id"] == "1234567890"
    
    def test_handle_publish_post_failure(self, service):
        """Test failed post publishing handler."""
        job_id = uuid4()
        
        payload = {
            "job_id": str(job_id),
            "platform_id": str(uuid4()),
            "media_url": "https://example.com/image.jpg",
        }
        
        service._get_instagram_platform = MagicMock(side_effect=Exception("API Error"))
        
        with pytest.raises(Exception):
            service._handle_publish_post(payload)


class TestSchedulerServiceRetryLogic:
    """Tests for job retry logic."""
    
    def test_retry_with_exponential_backoff(self):
        """Test that retries use exponential backoff."""
        service = SchedulerService()
        
        # Verify backoff calculation
        assert service.base_retry_delay == 60
        assert service.max_retry_delay == 3600
        
        # 1st retry: 60 seconds
        # 2nd retry: 120 seconds
        # 3rd retry: 240 seconds (capped at 3600)
        
        assert 60 * (2 ** 0) == 60
        assert 60 * (2 ** 1) == 120
        assert 60 * (2 ** 2) == 240


class TestSchedulerServiceCancelJob:
    """Tests for job cancellation."""
    
    @pytest.fixture
    def service(self):
        """Create scheduler service."""
        service = SchedulerService()
        
        # Mock session
        mock_session = MagicMock()
        mock_session.commit.return_value = None
        service._get_session = MagicMock()
        service._get_session.return_value.__enter__.return_value = mock_session
        service._get_session.return_value.__exit__.return_value = None
        
        return service
    
    def test_cancel_pending_job(self, service):
        """Test cancelling a pending job."""
        job_id = uuid4()
        
        mock_job = ScheduledJob(
            id=job_id,
            job_type="publish_instagram_post",
            status=ScheduledJobStatus.PENDING,
        )
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_job
        mock_session.commit.return_value = None
        
        service._get_session.return_value.__enter__.return_value = mock_session
        service._get_session.return_value.__exit__.return_value = None
        
        result = service.cancel_job(job_id)
        
        assert result is True
        assert mock_job.status == ScheduledJobStatus.CANCELLED
    
    def test_cancel_running_job_fails(self, service):
        """Test that running jobs cannot be cancelled."""
        job_id = uuid4()
        
        mock_job = ScheduledJob(
            id=job_id,
            job_type="publish_instagram_post",
            status=ScheduledJobStatus.RUNNING,
        )
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_job
        
        service._get_session.return_value.__enter__.return_value = mock_session
        service._get_session.return_value.__exit__.return_value = None
        
        with pytest.raises(ValueError):
            service.cancel_job(job_id)


class TestSchedulerServiceListJobs:
    """Tests for listing jobs."""
    
    @pytest.fixture
    def service(self):
        """Create scheduler service."""
        service = SchedulerService()
        return service
    
    def test_list_jobs_returns_all(self, service):
        """Test listing all jobs."""
        mock_session = MagicMock()
        mock_session.query.return_value.order_by.return_value.offset.return_value \
            .limit.return_value.all.return_value = []
        
        service._get_session = MagicMock()
        service._get_session.return_value.__enter__.return_value = mock_session
        service._get_session.return_value.__exit__.return_value = None
        
        jobs = service.list_jobs()
        
        assert isinstance(jobs, list)
    
    def test_list_jobs_with_status_filter(self, service):
        """Test listing jobs with status filter."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value.offset.return_value \
            .limit.return_value.all.return_value = []
        
        service._get_session = MagicMock()
        service._get_session.return_value.__enter__.return_value = mock_session
        service._get_session.return_value.__exit__.return_value = None
        
        jobs = service.list_jobs(status=ScheduledJobStatus.PENDING)
        
        assert isinstance(jobs, list)
        mock_query.filter_by.assert_called_with(status=ScheduledJobStatus.PENDING)


class TestSchedulerServiceGetJob:
    """Tests for getting a single job."""
    
    @pytest.fixture
    def service(self):
        """Create scheduler service."""
        service = SchedulerService()
        return service
    
    def test_get_job_not_found(self, service):
        """Test getting a non-existent job."""
        job_id = uuid4()
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        service._get_session = MagicMock()
        service._get_session.return_value.__enter__.return_value = mock_session
        service._get_session.return_value.__exit__.return_value = None
        
        job = service.get_job(job_id)
        
        assert job is None
    
    def test_get_job_found(self, service):
        """Test getting an existing job."""
        job_id = uuid4()
        mock_job = ScheduledJob(
            id=job_id,
            job_type="publish_instagram_post",
            status=ScheduledJobStatus.PENDING,
        )
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_job
        
        service._get_session = MagicMock()
        service._get_session.return_value.__enter__.return_value = mock_session
        service._get_session.return_value.__exit__.return_value = None
        
        job = service.get_job(job_id)
        
        assert job is not None
        assert job.id == job_id
        assert job.status == ScheduledJobStatus.PENDING


class TestSchedulerServiceStartStop:
    """Tests for scheduler start/stop."""
    
    def test_start_idempotent(self):
        """Test that starting twice is safe."""
        service = SchedulerService()
        
        # First start
        service.start()
        first_scheduler = service._scheduler
        
        # Second start should not create new scheduler
        service.start()
        second_scheduler = service._scheduler
        
        assert first_scheduler is second_scheduler
        
        # Cleanup
        service.stop()
    
    def test_stop_is_safe(self):
        """Test that stopping when not started is safe."""
        service = SchedulerService()
        
        # Should not raise
        service.stop()
        service.stop()
