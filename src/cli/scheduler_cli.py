"""
CLI Management Tool for Data Pipeline Scheduler.

Usage:
    python -m src.cli.scheduler_cli start           # Start scheduler
    python -m src.cli.scheduler_cli stop            # Stop scheduler
    python -m src.cli.scheduler_cli status          # Show status
    python -m src.cli.scheduler_cli trigger <job>   # Trigger job manually
    python -m src.cli.scheduler_cli backfill        # Run backfill
"""

import argparse
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.application.services.scheduler_service import SchedulerService
from src.application.services.pipeline_orchestrator import PipelineOrchestrator
from src.application.services.market_data_service import MarketDataService
from src.application.services.analysis_service import AnalysisService
from src.infrastructure.data.binance_client import BinanceClient
from src.infrastructure.repositories.parquet_repository import ParquetRepository
from src.infrastructure.storage.parquet_manager import ParquetManager
from src.infrastructure.storage.duckdb_query_engine import DuckDBQueryEngine
from src.domain.services.technical_analysis import TechnicalAnalysisService
from src.domain.services.regime_classifier import RegimeClassifierService
from src.domain.services.risk_calculator import RiskCalculatorService
from src.shared.config.scheduler_config import DEFAULT_SCHEDULER_CONFIG
from src.shared.config.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SchedulerCLI:
    """CLI interface for scheduler management."""
    
    def __init__(self):
        """Initialize CLI with service dependencies."""
        self.settings = Settings()
        self.config = DEFAULT_SCHEDULER_CONFIG
        
        # Initialize infrastructure
        self.binance = BinanceClient()
        self.parquet_manager = ParquetManager(self.settings.STORAGE_PATH)
        self.query_engine = DuckDBQueryEngine()
        self.repository = ParquetRepository(
            self.parquet_manager,
            self.query_engine
        )
        
        # Initialize domain services
        self.ta_service = TechnicalAnalysisService()
        self.regime_classifier = RegimeClassifierService(self.ta_service)
        self.risk_calculator = RiskCalculatorService()
        
        # Initialize application services
        self.market_service = MarketDataService(
            self.binance,
            self.repository
        )
        self.analysis_service = AnalysisService(
            self.repository,
            self.ta_service,
            self.regime_classifier,
            self.risk_calculator
        )
        
        # Initialize scheduler and orchestrator
        self.scheduler = SchedulerService(
            self.market_service,
            self.analysis_service,
            timezone=self.config.timezone
        )
        self.orchestrator = PipelineOrchestrator(
            self.market_service,
            self.analysis_service
        )
    
    def start(self, args: argparse.Namespace) -> None:
        """Start the scheduler with configured jobs."""
        print("🚀 Starting scheduler...")
        
        # Add jobs based on configuration
        jobs_added = []
        
        if self.config.hourly_download_enabled:
            job_id = self.scheduler.add_hourly_download_job(
                symbol=self.config.default_symbol,
                interval=self.config.default_interval,
                limit=self.config.hourly_download_limit
            )
            jobs_added.append(job_id)
        
        if self.config.daily_regime_enabled:
            job_id = self.scheduler.add_daily_regime_update_job(
                symbol=self.config.default_symbol,
                hour=self.config.daily_regime_hour,
                minute=self.config.daily_regime_minute
            )
            jobs_added.append(job_id)
        
        if self.config.weekly_retrain_enabled:
            job_id = self.scheduler.add_weekly_retrain_job(
                symbol=self.config.default_symbol,
                day_of_week=self.config.weekly_retrain_day,
                hour=self.config.weekly_retrain_hour,
                minute=self.config.weekly_retrain_minute
            )
            jobs_added.append(job_id)
        
        if self.config.monthly_migration_enabled:
            job_id = self.scheduler.add_monthly_migration_job(
                day=self.config.monthly_migration_day,
                hour=self.config.monthly_migration_hour,
                minute=self.config.monthly_migration_minute
            )
            jobs_added.append(job_id)
        
        # Start scheduler
        self.scheduler.start()
        
        print(f"✅ Scheduler started with {len(jobs_added)} jobs:")
        for job_id in jobs_added:
            job = self.scheduler.get_job_status(job_id)
            if job:
                print(f"   • {job.name}")
                print(f"     Next run: {job.next_run}")
        
        print("\n⏸️  Press Ctrl+C to stop")
        
        # Keep running
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping scheduler...")
            self.scheduler.stop()
            print("✅ Scheduler stopped")
    
    def stop(self, args: argparse.Namespace) -> None:
        """Stop the scheduler."""
        print("🛑 Stopping scheduler...")
        self.scheduler.stop()
        print("✅ Scheduler stopped")
    
    def status(self, args: argparse.Namespace) -> None:
        """Show scheduler status."""
        status = self.scheduler.get_scheduler_status()
        jobs = self.scheduler.list_jobs()
        
        print("\n📊 Scheduler Status")
        print("=" * 60)
        print(f"Running: {status['running']}")
        print(f"Jobs: {status['jobs_count']}")
        print(f"Timezone: {status['timezone']}")
        
        if jobs:
            print("\n📅 Scheduled Jobs:")
            print("-" * 60)
            for job in jobs:
                print(f"\n{job.name} ({job.job_id})")
                print(f"  Status: {job.status}")
                print(f"  Trigger: {job.trigger}")
                if job.next_run:
                    print(f"  Next run: {job.next_run}")
                if job.last_run:
                    print(f"  Last run: {job.last_run}")
                if job.error_count > 0:
                    print(f"  Errors: {job.error_count}")
        else:
            print("\nNo scheduled jobs")
    
    def trigger(self, args: argparse.Namespace) -> None:
        """Manually trigger a job."""
        job_id = args.job_id
        
        print(f"🔥 Triggering job: {job_id}")
        
        try:
            self.scheduler.trigger_job(job_id)
            print(f"✅ Job triggered: {job_id}")
        except Exception as e:
            print(f"❌ Failed to trigger job: {e}")
            sys.exit(1)
    
    def backfill(self, args: argparse.Namespace) -> None:
        """Run historical data backfill."""
        symbol = args.symbol or self.config.default_symbol
        days = args.days or 365
        interval = args.interval or self.config.default_interval
        
        end = datetime.now()
        start = end - timedelta(days=days)
        
        print(f"📥 Starting backfill:")
        print(f"   Symbol: {symbol}")
        print(f"   Period: {start} to {end}")
        print(f"   Interval: {interval}")
        print(f"   Days: {days}")
        
        result = self.orchestrator.run_backfill(
            symbol=symbol,
            start=start,
            end=end,
            interval=interval
        )
        
        if result.status == "success":
            print(f"\n✅ Backfill complete:")
            print(f"   Rows downloaded: {result.rows_downloaded}")
            print(f"   Duration: {result.duration_seconds:.2f}s")
        else:
            print(f"\n❌ Backfill failed:")
            for error in result.errors:
                print(f"   {error}")
            sys.exit(1)
    
    def update(self, args: argparse.Namespace) -> None:
        """Run incremental update manually."""
        symbol = args.symbol or self.config.default_symbol
        interval = args.interval or self.config.default_interval
        
        print(f"🔄 Running incremental update:")
        print(f"   Symbol: {symbol}")
        print(f"   Interval: {interval}")
        
        result = self.orchestrator.run_incremental_update(
            symbol=symbol,
            interval=interval
        )
        
        if result.status == "success":
            print(f"\n✅ Update complete:")
            print(f"   Rows downloaded: {result.rows_downloaded}")
            print(f"   Regimes classified: {result.regimes_classified}")
            print(f"   Duration: {result.duration_seconds:.2f}s")
        else:
            print(f"\n❌ Update failed:")
            for error in result.errors:
                print(f"   {error}")
            sys.exit(1)
    
    def retrain(self, args: argparse.Namespace) -> None:
        """Run model retraining."""
        symbol = args.symbol or self.config.default_symbol
        days = args.days or self.config.weekly_retrain_days
        interval = args.interval or self.config.default_interval
        
        print(f"🔧 Running model retraining:")
        print(f"   Symbol: {symbol}")
        print(f"   Training days: {days}")
        print(f"   Interval: {interval}")
        
        result = self.orchestrator.run_retraining_pipeline(
            symbol=symbol,
            training_days=days,
            interval=interval
        )
        
        if result.status == "success":
            print(f"\n✅ Retraining complete:")
            print(f"   Regimes classified: {result.regimes_classified}")
            print(f"   Duration: {result.duration_seconds:.2f}s")
        else:
            print(f"\n❌ Retraining failed:")
            for error in result.errors:
                print(f"   {error}")
            sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Bitcoin Market Intelligence - Scheduler Management"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Start command
    parser_start = subparsers.add_parser("start", help="Start scheduler")
    
    # Stop command
    parser_stop = subparsers.add_parser("stop", help="Stop scheduler")
    
    # Status command
    parser_status = subparsers.add_parser("status", help="Show scheduler status")
    
    # Trigger command
    parser_trigger = subparsers.add_parser("trigger", help="Trigger job manually")
    parser_trigger.add_argument("job_id", help="Job ID to trigger")
    
    # Backfill command
    parser_backfill = subparsers.add_parser("backfill", help="Run historical backfill")
    parser_backfill.add_argument("--symbol", help="Trading pair (default: BTCUSDT)")
    parser_backfill.add_argument("--days", type=int, help="Days to backfill (default: 365)")
    parser_backfill.add_argument("--interval", help="Timeframe (default: 1h)")
    
    # Update command
    parser_update = subparsers.add_parser("update", help="Run incremental update")
    parser_update.add_argument("--symbol", help="Trading pair (default: BTCUSDT)")
    parser_update.add_argument("--interval", help="Timeframe (default: 1h)")
    
    # Retrain command
    parser_retrain = subparsers.add_parser("retrain", help="Run model retraining")
    parser_retrain.add_argument("--symbol", help="Trading pair (default: BTCUSDT)")
    parser_retrain.add_argument("--days", type=int, help="Training days (default: 365)")
    parser_retrain.add_argument("--interval", help="Timeframe (default: 1h)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize CLI
    cli = SchedulerCLI()
    
    # Execute command
    command_map = {
        "start": cli.start,
        "stop": cli.stop,
        "status": cli.status,
        "trigger": cli.trigger,
        "backfill": cli.backfill,
        "update": cli.update,
        "retrain": cli.retrain,
    }
    
    command_func = command_map.get(args.command)
    if command_func:
        command_func(args)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
