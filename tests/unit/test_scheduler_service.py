"""
Tests for Scheduler Service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.application.services.scheduler_service import (
    SchedulerService,
    ScheduledJob
)
from src.shared.exceptions.custom_exceptions import AppException


@pytest.fixture
def mock_market_service():
    """Create mock market data service."""
    service = Mock()
    service.update_latest_data.return_value = {"rows_added": 2}
    return service


@pytest.fixture
def mock_analysis_service():
    """Create mock analysis service."""
    service = Mock()
    service.classify_market_regime.return_value = [Mock(), Mock()]
    service.train_regime_classifier.return_value = None
    return service


@pytest.fixture
def scheduler_service(mock_market_service, mock_analysis_service):
    """Create scheduler service instance."""
    return SchedulerService(
        mock_market_service,
        mock_analysis_service,
        timezone="UTC"
    )


class TestSchedulerService:
    """Test scheduler service."""
    
    def test_initialization(self, scheduler_service):
        """Test scheduler initializes correctly."""
        assert scheduler_service.timezone == "UTC"
        assert not scheduler_service.scheduler.running
        assert len(scheduler_service.jobs) == 0
    
    def test_start_stop(self, scheduler_service):
        """Test starting and stopping scheduler."""
        # Start
        scheduler_service.start()
        assert scheduler_service.scheduler.running
        
        # Stop
        scheduler_service.stop(wait=False)
        assert not scheduler_service.scheduler.running
    
    def test_add_hourly_download_job(self, scheduler_service):
        """Test adding hourly download job."""
        job_id = scheduler_service.add_hourly_download_job(
            symbol="BTCUSDT",
            interval="1h",
            limit=2
        )
        
        assert job_id == "hourly_download_BTCUSDT_1h"
        assert job_id in scheduler_service.jobs
        
        job = scheduler_service.get_job_status(job_id)
        assert job.name == "Hourly Download: BTCUSDT"
        assert job.trigger == "cron"
        assert job.metadata["symbol"] == "BTCUSDT"
    
    def test_add_daily_regime_update_job(self, scheduler_service):
        """Test adding daily regime update job."""
        job_id = scheduler_service.add_daily_regime_update_job(
            symbol="BTCUSDT",
            hour=1,
            minute=0
        )
        
        assert job_id == "daily_regime_BTCUSDT"
        assert job_id in scheduler_service.jobs
        
        job = scheduler_service.get_job_status(job_id)
        assert job.name == "Daily Regime Update: BTCUSDT"
        assert job.trigger == "cron"
    
    def test_add_weekly_retrain_job(self, scheduler_service):
        """Test adding weekly retrain job."""
        job_id = scheduler_service.add_weekly_retrain_job(
            symbol="BTCUSDT",
            day_of_week="sun",
            hour=2,
            minute=0
        )
        
        assert job_id == "weekly_retrain_BTCUSDT"
        assert job_id in scheduler_service.jobs
        
        job = scheduler_service.get_job_status(job_id)
        assert job.name == "Weekly Retrain: BTCUSDT"
        assert job.trigger == "cron"
    
    def test_add_monthly_migration_job(self, scheduler_service):
        """Test adding monthly migration job."""
        job_id = scheduler_service.add_monthly_migration_job(
            day=1,
            hour=3,
            minute=0
        )
        
        assert job_id == "monthly_migration"
        assert job_id in scheduler_service.jobs
        
        job = scheduler_service.get_job_status(job_id)
        assert job.name == "Monthly Migration"
        assert job.trigger == "cron"
    
    def test_list_jobs(self, scheduler_service):
        """Test listing all jobs."""
        # Add multiple jobs
        scheduler_service.add_hourly_download_job()
        scheduler_service.add_daily_regime_update_job()
        
        jobs = scheduler_service.list_jobs()
        assert len(jobs) == 2
        assert all(isinstance(job, ScheduledJob) for job in jobs)
    
    def test_remove_job(self, scheduler_service):
        """Test removing a job."""
        job_id = scheduler_service.add_hourly_download_job()
        assert job_id in scheduler_service.jobs
        
        scheduler_service.remove_job(job_id)
        assert job_id not in scheduler_service.jobs
    
    def test_get_scheduler_status(self, scheduler_service):
        """Test getting scheduler status."""
        status = scheduler_service.get_scheduler_status()
        
        assert "running" in status
        assert "jobs_count" in status
        assert "timezone" in status
        assert status["timezone"] == "UTC"
    
    def test_run_download_job_success(
        self, scheduler_service, mock_market_service
    ):
        """Test successful download job execution."""
        result = scheduler_service._run_download_job(
            symbol="BTCUSDT",
            interval="1h",
            limit=2
        )
        
        assert result["status"] == "success"
        assert result["rows_added"] == 2
        mock_market_service.update_latest_data.assert_called_once()
    
    def test_run_download_job_failure(
        self, scheduler_service, mock_market_service
    ):
        """Test failed download job execution."""
        mock_market_service.update_latest_data.side_effect = Exception("API error")
        
        result = scheduler_service._run_download_job(
            symbol="BTCUSDT",
            interval="1h",
            limit=2
        )
        
        assert result["status"] == "failed"
        assert "API error" in result["error"]
    
    def test_run_regime_update_job_success(
        self, scheduler_service, mock_analysis_service
    ):
        """Test successful regime update job."""
        result = scheduler_service._run_regime_update_job("BTCUSDT")
        
        assert result["status"] == "success"
        assert result["regimes_classified"] == 2
        mock_analysis_service.classify_market_regime.assert_called_once()
    
    def test_trigger_job_not_found(self, scheduler_service):
        """Test triggering non-existent job raises error."""
        with pytest.raises(AppException, match="Job not found"):
            scheduler_service.trigger_job("non_existent_job")


class TestScheduledJob:
    """Test ScheduledJob dataclass."""
    
    def test_scheduled_job_creation(self):
        """Test creating a scheduled job."""
        job = ScheduledJob(
            job_id="test_job",
            name="Test Job",
            trigger="cron",
            description="Test description"
        )
        
        assert job.job_id == "test_job"
        assert job.name == "Test Job"
        assert job.status == "pending"
        assert job.error_count == 0
        assert isinstance(job.metadata, dict)
