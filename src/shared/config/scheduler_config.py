"""
Scheduler Configuration - Settings for automated data pipeline.

This defines the schedule and parameters for automated tasks.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class SchedulerConfig:
    """Configuration for scheduler service."""
    
    # Timezone for scheduling
    timezone: str = "UTC"
    
    # Data sources
    default_symbol: str = "BTCUSDT"
    default_interval: str = "1h"
    
    # Hourly download job
    hourly_download_enabled: bool = True
    hourly_download_minute: int = 5  # Run at minute 5 of each hour
    hourly_download_limit: int = 2  # Fetch last 2 candles
    
    # Daily regime update job
    daily_regime_enabled: bool = True
    daily_regime_hour: int = 1  # Run at 1 AM
    daily_regime_minute: int = 0
    
    # Weekly retraining job
    weekly_retrain_enabled: bool = True
    weekly_retrain_day: str = "sun"  # Run on Sunday
    weekly_retrain_hour: int = 2  # Run at 2 AM
    weekly_retrain_minute: int = 0
    weekly_retrain_days: int = 365  # Use 1 year of data
    
    # Monthly migration job
    monthly_migration_enabled: bool = True
    monthly_migration_day: int = 1  # Run on 1st of month
    monthly_migration_hour: int = 3  # Run at 3 AM
    monthly_migration_minute: int = 0
    monthly_migration_retention_months: int = 3  # Keep 3 months in hot storage
    
    # Error handling
    max_retries: int = 3
    retry_delay_seconds: int = 300  # 5 minutes
    
    # Performance
    max_concurrent_jobs: int = 2
    job_timeout_seconds: int = 3600  # 1 hour
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "timezone": self.timezone,
            "default_symbol": self.default_symbol,
            "default_interval": self.default_interval,
            "hourly_download": {
                "enabled": self.hourly_download_enabled,
                "minute": self.hourly_download_minute,
                "limit": self.hourly_download_limit,
            },
            "daily_regime": {
                "enabled": self.daily_regime_enabled,
                "hour": self.daily_regime_hour,
                "minute": self.daily_regime_minute,
            },
            "weekly_retrain": {
                "enabled": self.weekly_retrain_enabled,
                "day": self.weekly_retrain_day,
                "hour": self.weekly_retrain_hour,
                "minute": self.weekly_retrain_minute,
                "training_days": self.weekly_retrain_days,
            },
            "monthly_migration": {
                "enabled": self.monthly_migration_enabled,
                "day": self.monthly_migration_day,
                "hour": self.monthly_migration_hour,
                "minute": self.monthly_migration_minute,
                "retention_months": self.monthly_migration_retention_months,
            },
            "error_handling": {
                "max_retries": self.max_retries,
                "retry_delay_seconds": self.retry_delay_seconds,
            },
            "performance": {
                "max_concurrent_jobs": self.max_concurrent_jobs,
                "job_timeout_seconds": self.job_timeout_seconds,
            },
        }


# Default configuration
DEFAULT_SCHEDULER_CONFIG = SchedulerConfig()
