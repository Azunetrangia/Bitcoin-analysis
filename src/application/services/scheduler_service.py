"""
Scheduler Service - Automated data pipeline execution.

This service manages scheduled tasks for:
- Hourly data downloads from Binance
- Daily regime classification updates
- Weekly model retraining
- Monthly data migration (hot → warm storage)
"""

from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any, List
import logging
from dataclasses import dataclass, field

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job

from src.application.services.market_data_service import MarketDataService
from src.application.services.analysis_service import AnalysisService
from src.shared.exceptions.custom_exceptions import AppException

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    """Metadata for a scheduled job."""
    
    job_id: str
    name: str
    trigger: str  # 'cron' or 'interval'
    description: str
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SchedulerService:
    """
    Manages scheduled tasks for data pipeline automation.
    
    This service uses APScheduler to run tasks in the background:
    - Hourly: Download latest 1h candles from Binance
    - Daily: Update regime classification with latest data
    - Weekly: Retrain HMM models with rolling window
    - Monthly: Migrate old data from hot to warm storage
    
    Example:
        >>> scheduler = SchedulerService(market_service, analysis_service)
        >>> scheduler.start()
        >>> # Runs in background
        >>> scheduler.stop()
    """
    
    def __init__(
        self,
        market_data_service: MarketDataService,
        analysis_service: AnalysisService,
        timezone: str = "UTC"
    ):
        """
        Initialize scheduler with required services.
        
        Args:
            market_data_service: Service for market data operations
            analysis_service: Service for analysis operations
            timezone: Timezone for scheduling (default: UTC)
        """
        self.market_service = market_data_service
        self.analysis_service = analysis_service
        self.timezone = timezone
        
        # APScheduler instance
        self.scheduler = BackgroundScheduler(timezone=timezone)
        
        # Job tracking
        self.jobs: Dict[str, ScheduledJob] = {}
        
        logger.info(f"✅ Scheduler initialized (timezone={timezone})")
    
    def start(self) -> None:
        """
        Start the scheduler.
        
        This begins executing all configured jobs according to their schedules.
        
        Raises:
            AppException: If scheduler fails to start
        """
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("🚀 Scheduler started")
            else:
                logger.warning("⚠️  Scheduler already running")
                
        except Exception as e:
            raise AppException(
                f"Failed to start scheduler: {str(e)}",
                details={"jobs": len(self.jobs)}
            )
    
    def stop(self, wait: bool = True) -> None:
        """
        Stop the scheduler.
        
        Args:
            wait: If True, wait for running jobs to complete
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info(f"🛑 Scheduler stopped (wait={wait})")
        else:
            logger.warning("⚠️  Scheduler not running")
    
    def pause(self) -> None:
        """Pause all scheduled jobs."""
        self.scheduler.pause()
        logger.info("⏸️  Scheduler paused")
    
    def resume(self) -> None:
        """Resume all scheduled jobs."""
        self.scheduler.resume()
        logger.info("▶️  Scheduler resumed")
    
    # ==================== Job Configuration ====================
    
    def add_hourly_download_job(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1h",
        limit: int = 2
    ) -> str:
        """
        Schedule hourly data downloads.
        
        This runs every hour at minute 5 to download the latest 2 candles
        (current incomplete + previous complete).
        
        Args:
            symbol: Trading pair (default: BTCUSDT)
            interval: Timeframe (default: 1h)
            limit: Number of candles to fetch (default: 2)
            
        Returns:
            Job ID
        """
        job_id = f"hourly_download_{symbol}_{interval}"
        
        def job_func():
            return self._run_download_job(symbol, interval, limit)
        
        # Run at minute 5 of every hour (cron: 5 * * * *)
        trigger = CronTrigger(minute=5, timezone=self.timezone)
        
        job = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=f"Hourly Download: {symbol} {interval}",
            replace_existing=True
        )
        
        self.jobs[job_id] = ScheduledJob(
            job_id=job_id,
            name=f"Hourly Download: {symbol}",
            trigger="cron",
            description=f"Download latest {limit} {interval} candles for {symbol}",
            next_run=getattr(job, 'next_run_time', None),
            metadata={"symbol": symbol, "interval": interval, "limit": limit}
        )
        
        logger.info(f"✅ Added job: {job_id} (next run: {getattr(job, 'next_run_time', None)})")
        
        return job_id
    
    def add_daily_regime_update_job(
        self,
        symbol: str = "BTCUSDT",
        hour: int = 1,
        minute: int = 0
    ) -> str:
        """
        Schedule daily regime classification updates.
        
        This runs once per day to reclassify recent market regimes
        with the latest data.
        
        Args:
            symbol: Trading pair (default: BTCUSDT)
            hour: Hour to run (0-23, default: 1 AM)
            minute: Minute to run (0-59, default: 0)
            
        Returns:
            Job ID
        """
        job_id = f"daily_regime_{symbol}"
        
        def job_func():
            return self._run_regime_update_job(symbol)
        
        # Run daily at specified time (cron: minute hour * * *)
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone=self.timezone
        )
        
        job = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=f"Daily Regime Update: {symbol}",
            replace_existing=True
        )
        
        self.jobs[job_id] = ScheduledJob(
            job_id=job_id,
            name=f"Daily Regime Update: {symbol}",
            trigger="cron",
            description=f"Update regime classification for {symbol}",
            next_run=getattr(job, 'next_run_time', None),
            metadata={"symbol": symbol}
        )
        
        logger.info(f"✅ Added job: {job_id} (next run: {getattr(job, 'next_run_time', None)})")
        
        return job_id
    
    def add_weekly_retrain_job(
        self,
        symbol: str = "BTCUSDT",
        day_of_week: str = "sun",
        hour: int = 2,
        minute: int = 0
    ) -> str:
        """
        Schedule weekly model retraining.
        
        This retrains the HMM model with a rolling window of data
        to adapt to market evolution.
        
        Args:
            symbol: Trading pair (default: BTCUSDT)
            day_of_week: Day to run (mon-sun, default: sun)
            hour: Hour to run (0-23, default: 2 AM)
            minute: Minute to run (0-59, default: 0)
            
        Returns:
            Job ID
        """
        job_id = f"weekly_retrain_{symbol}"
        
        def job_func():
            return self._run_retrain_job(symbol)
        
        # Run weekly on specified day/time
        trigger = CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            timezone=self.timezone
        )
        
        job = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=f"Weekly Retrain: {symbol}",
            replace_existing=True
        )
        
        self.jobs[job_id] = ScheduledJob(
            job_id=job_id,
            name=f"Weekly Retrain: {symbol}",
            trigger="cron",
            description=f"Retrain HMM model for {symbol}",
            next_run=getattr(job, 'next_run_time', None),
            metadata={"symbol": symbol}
        )
        
        logger.info(f"✅ Added job: {job_id} (next run: {getattr(job, 'next_run_time', None)})")
        
        return job_id
    
    def add_monthly_migration_job(
        self,
        day: int = 1,
        hour: int = 3,
        minute: int = 0
    ) -> str:
        """
        Schedule monthly hot → warm storage migration.
        
        This moves data older than 3 months from hot (Parquet)
        to warm (Supabase) storage.
        
        Args:
            day: Day of month (1-31, default: 1st)
            hour: Hour to run (0-23, default: 3 AM)
            minute: Minute to run (0-59, default: 0)
            
        Returns:
            Job ID
        """
        job_id = "monthly_migration"
        
        def job_func():
            return self._run_migration_job()
        
        # Run monthly on specified day/time
        trigger = CronTrigger(
            day=day,
            hour=hour,
            minute=minute,
            timezone=self.timezone
        )
        
        job = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name="Monthly Storage Migration",
            replace_existing=True
        )
        
        self.jobs[job_id] = ScheduledJob(
            job_id=job_id,
            name="Monthly Migration",
            trigger="cron",
            description="Migrate old data from hot to warm storage",
            next_run=getattr(job, 'next_run_time', None),
            metadata={"retention_months": 3}
        )
        
        logger.info(f"✅ Added job: {job_id} (next run: {getattr(job, 'next_run_time', None)})")
        
        return job_id
    
    # ==================== Manual Triggers ====================
    
    def trigger_job(self, job_id: str) -> None:
        """
        Manually trigger a job to run immediately.
        
        Args:
            job_id: Job identifier
            
        Raises:
            AppException: If job not found
        """
        job = self.scheduler.get_job(job_id)
        
        if job is None:
            raise AppException(
                f"Job not found: {job_id}",
                details={"available_jobs": list(self.jobs.keys())}
            )
        
        logger.info(f"🔥 Manually triggering job: {job_id}")
        job.modify(next_run_time=datetime.now()) if hasattr(job, 'modify') else None
    
    def remove_job(self, job_id: str) -> None:
        """
        Remove a scheduled job.
        
        Args:
            job_id: Job identifier
        """
        self.scheduler.remove_job(job_id)
        self.jobs.pop(job_id, None)
        logger.info(f"🗑️  Removed job: {job_id}")
    
    # ==================== Status & Monitoring ====================
    
    def get_job_status(self, job_id: str) -> Optional[ScheduledJob]:
        """
        Get status of a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job metadata or None if not found
        """
        if job_id not in self.jobs:
            return None
        
        # Update next_run from scheduler
        job = self.scheduler.get_job(job_id)
        if job:
            self.jobs[job_id].next_run = getattr(job, 'next_run_time', None)
        
        return self.jobs[job_id]
    
    def list_jobs(self) -> List[ScheduledJob]:
        """
        List all scheduled jobs.
        
        Returns:
            List of job metadata
        """
        # Update next_run times from scheduler
        for job_id in self.jobs:
            job = self.scheduler.get_job(job_id)
            if job:
                self.jobs[job_id].next_run = getattr(job, 'next_run_time', None)
        
        return list(self.jobs.values())
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get overall scheduler status.
        
        Returns:
            Status dictionary with:
            - running: Is scheduler running
            - jobs_count: Number of scheduled jobs
            - timezone: Scheduler timezone
            - uptime: Time since start (if running)
        """
        return {
            "running": self.scheduler.running,
            "jobs_count": len(self.jobs),
            "timezone": self.timezone,
            "state": self.scheduler.state,
        }
    
    # ==================== Job Implementations ====================
    
    def _run_download_job(
        self,
        symbol: str,
        interval: str,
        limit: int
    ) -> Dict[str, Any]:
        """
        Execute data download job.
        
        Returns:
            Job result with status and metrics
        """
        job_id = f"hourly_download_{symbol}_{interval}"
        
        try:
            logger.info(f"▶️  Running: {job_id}")
            
            if job_id in self.jobs:
                self.jobs[job_id].status = "running"
                self.jobs[job_id].last_run = datetime.now()
            
            # Download latest data
            result = self.market_service.update_latest_data(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            if job_id in self.jobs:
                self.jobs[job_id].status = "completed"
                self.jobs[job_id].error_count = 0
            
            logger.info(f"✅ Completed: {job_id}, rows_added={result.get('rows_added', 0)}")
            
            return {
                "status": "success",
                "job_id": job_id,
                "rows_added": result.get("rows_added", 0),
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            if job_id in self.jobs:
                self.jobs[job_id].status = "failed"
                self.jobs[job_id].error_count += 1
            
            logger.error(f"❌ Failed: {job_id}, error={str(e)}")
            
            return {
                "status": "failed",
                "job_id": job_id,
                "error": str(e),
                "timestamp": datetime.now()
            }
    
    def _run_regime_update_job(self, symbol: str) -> Dict[str, Any]:
        """
        Execute regime classification update job.
        
        Returns:
            Job result with status and metrics
        """
        job_id = f"daily_regime_{symbol}"
        
        try:
            logger.info(f"▶️  Running: {job_id}")
            
            if job_id in self.jobs:
                self.jobs[job_id].status = "running"
                self.jobs[job_id].last_run = datetime.now()
            
            # Get last 30 days of data
            end = datetime.now()
            start = end - timedelta(days=30)
            
            # Classify regimes
            regimes = self.analysis_service.classify_market_regime(
                symbol=symbol,
                start=start,
                end=end,
                interval="1h"
            )
            
            if job_id in self.jobs:
                self.jobs[job_id].status = "completed"
                self.jobs[job_id].error_count = 0
            
            logger.info(f"✅ Completed: {job_id}, regimes_classified={len(regimes)}")
            
            return {
                "status": "success",
                "job_id": job_id,
                "regimes_classified": len(regimes),
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            self.jobs[job_id].status = "failed"
            self.jobs[job_id].error_count += 1
            
            logger.error(
                f"❌ Failed: {job_id}",
                error=str(e)
            )
            
            return {
                "status": "failed",
                "job_id": job_id,
                "error": str(e),
                "timestamp": datetime.now()
            }
    
    def _run_retrain_job(self, symbol: str) -> Dict[str, Any]:
        """
        Execute model retraining job.
        
        Returns:
            Job result with status and metrics
        """
        job_id = f"weekly_retrain_{symbol}"
        
        try:
            logger.info(f"▶️  Running: {job_id}")
            
            if job_id in self.jobs:
                self.jobs[job_id].status = "running"
                self.jobs[job_id].last_run = datetime.now()
            
            # Get 1 year of data for training
            end = datetime.now()
            start = end - timedelta(days=365)
            
            # Retrain model
            self.analysis_service.train_regime_classifier(
                symbol=symbol,
                start=start,
                end=end,
                interval="1h"
            )
            
            if job_id in self.jobs:
                self.jobs[job_id].status = "completed"
                self.jobs[job_id].error_count = 0
            
            logger.info(f"✅ Completed: {job_id}")
            
            return {
                "status": "success",
                "job_id": job_id,
                "training_days": 365,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            if job_id in self.jobs:
                self.jobs[job_id].status = "failed"
                self.jobs[job_id].error_count += 1
            
            logger.error(f"❌ Failed: {job_id}, error={str(e)}")
            
            return {
                "status": "failed",
                "job_id": job_id,
                "error": str(e),
                "timestamp": datetime.now()
            }
    
    def _run_migration_job(self) -> Dict[str, Any]:
        """
        Execute hot → warm storage migration job.
        
        Returns:
            Job result with status and metrics
        """
        job_id = "monthly_migration"
        
        try:
            logger.info(f"▶️  Running: {job_id}")
            
            if job_id in self.jobs:
                self.jobs[job_id].status = "running"
                self.jobs[job_id].last_run = datetime.now()
            
            # Calculate cutoff date (3 months ago)
            cutoff = datetime.now() - timedelta(days=90)
            
            # TODO: Implement migration logic
            # For now, just log the operation
            logger.info(f"Migration: Moving data before {cutoff}")
            
            if job_id in self.jobs:
                self.jobs[job_id].status = "completed"
                self.jobs[job_id].error_count = 0
            
            logger.info(f"✅ Completed: {job_id}")
            
            return {
                "status": "success",
                "job_id": job_id,
                "cutoff_date": cutoff,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            self.jobs[job_id].status = "failed"
            self.jobs[job_id].error_count += 1
            
            logger.error(
                f"❌ Failed: {job_id}",
                error=str(e)
            )
            
            return {
                "status": "failed",
                "job_id": job_id,
                "error": str(e),
                "timestamp": datetime.now()
            }
