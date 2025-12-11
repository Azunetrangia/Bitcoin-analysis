"""
Pipeline Orchestrator - Coordinate end-to-end data pipeline workflows.

This service orchestrates complex workflows involving multiple steps:
1. Download data from Binance
2. Validate and clean data
3. Store in appropriate tier (hot/warm)
4. Run analysis and classification
5. Generate insights and alerts
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
from dataclasses import dataclass
from enum import Enum

from src.application.services.market_data_service import MarketDataService
from src.application.services.analysis_service import AnalysisService
from src.shared.exceptions.custom_exceptions import AppException

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline execution stages."""
    DOWNLOAD = "download"
    VALIDATION = "validation"
    STORAGE = "storage"
    ANALYSIS = "analysis"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    
    pipeline_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    stage: PipelineStage = PipelineStage.DOWNLOAD
    status: str = "running"
    
    # Metrics
    rows_downloaded: int = 0
    rows_stored: int = 0
    regimes_classified: int = 0
    alerts_generated: int = 0
    
    # Errors
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate execution duration."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class PipelineOrchestrator:
    """
    Orchestrates end-to-end data pipeline workflows.
    
    This service coordinates multiple services to execute complex
    data processing workflows:
    
    1. **Incremental Update Pipeline**:
       - Download latest data from Binance
       - Validate OHLCV data
       - Store in hot storage (Parquet)
       - Update regime classification
       
    2. **Backfill Pipeline**:
       - Download historical data in batches
       - Store directly to warm storage (Supabase)
       - Skip analysis for historical data
       
    3. **Retraining Pipeline**:
       - Query data from storage
       - Retrain HMM models
       - Update regime classifications
       - Generate insights report
    
    Example:
        >>> orchestrator = PipelineOrchestrator(market_service, analysis_service)
        >>> result = orchestrator.run_incremental_update("BTCUSDT")
        >>> print(f"Downloaded {result.rows_downloaded} candles")
    """
    
    def __init__(
        self,
        market_data_service: MarketDataService,
        analysis_service: AnalysisService
    ):
        """
        Initialize orchestrator with required services.
        
        Args:
            market_data_service: Service for market data operations
            analysis_service: Service for analysis operations
        """
        self.market_service = market_data_service
        self.analysis_service = analysis_service
        
        # Track running pipelines
        self.active_pipelines: Dict[str, PipelineResult] = {}
        
        logger.info("✅ Pipeline orchestrator initialized")
    
    # ==================== Main Pipelines ====================
    
    def run_incremental_update(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1h",
        limit: int = 2,
        run_analysis: bool = True
    ) -> PipelineResult:
        """
        Execute incremental update pipeline.
        
        This is the main pipeline for real-time data updates:
        1. Download latest N candles
        2. Store in hot storage (Parquet)
        3. Update regime classification (if enabled)
        
        Args:
            symbol: Trading pair (default: BTCUSDT)
            interval: Timeframe (default: 1h)
            limit: Number of candles to fetch (default: 2)
            run_analysis: Run regime classification (default: True)
            
        Returns:
            PipelineResult with execution metrics
        """
        pipeline_id = f"incremental_{symbol}_{datetime.now().timestamp()}"
        result = PipelineResult(
            pipeline_id=pipeline_id,
            start_time=datetime.now()
        )
        self.active_pipelines[pipeline_id] = result
        
        try:
            logger.info(f"🚀 Starting incremental update pipeline: {pipeline_id}, symbol={symbol}")
            
            # Stage 1: Download
            result.stage = PipelineStage.DOWNLOAD
            download_result = self.market_service.update_latest_data(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            result.rows_downloaded = download_result.get("rows_added", 0) if isinstance(download_result, dict) else download_result
            
            logger.info(f"✅ Download complete: {result.rows_downloaded} rows")
            
            # Stage 2: Storage (handled by market_service)
            result.stage = PipelineStage.STORAGE
            result.rows_stored = result.rows_downloaded
            
            # Stage 3: Analysis
            if run_analysis and result.rows_downloaded > 0:
                result.stage = PipelineStage.ANALYSIS
                
                # Get recent data for classification (last 30 days)
                end = datetime.now()
                start = end - timedelta(days=30)
                
                regimes = self.analysis_service.classify_market_regime(
                    symbol=symbol,
                    start=start,
                    end=end,
                    interval=interval
                )
                
                result.regimes_classified = len(regimes)
                
                logger.info(f"✅ Analysis complete: {result.regimes_classified} regimes")
            
            # Complete
            result.stage = PipelineStage.COMPLETE
            result.status = "success"
            result.end_time = datetime.now()
            
            logger.info(f"✅ Pipeline complete: {pipeline_id}, duration={result.duration_seconds}s")
            
            return result
            
        except Exception as e:
            result.stage = PipelineStage.FAILED
            result.status = "failed"
            result.end_time = datetime.now()
            result.errors.append(str(e))
            
            logger.error(f"❌ Pipeline failed: {pipeline_id}, stage={result.stage.value}, error={str(e)}")
            
            return result
        
        finally:
            # Remove from active pipelines
            self.active_pipelines.pop(pipeline_id, None)
    
    def run_backfill(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1h",
        batch_days: int = 30
    ) -> PipelineResult:
        """
        Execute historical data backfill pipeline.
        
        This downloads historical data in batches and stores
        directly to warm storage (Supabase):
        1. Split date range into batches
        2. Download each batch from Binance
        3. Store in warm storage
        4. Skip analysis (for performance)
        
        Args:
            symbol: Trading pair
            start: Start date for backfill
            end: End date for backfill
            interval: Timeframe (default: 1h)
            batch_days: Days per batch (default: 30)
            
        Returns:
            PipelineResult with execution metrics
        """
        pipeline_id = f"backfill_{symbol}_{datetime.now().timestamp()}"
        result = PipelineResult(
            pipeline_id=pipeline_id,
            start_time=datetime.now()
        )
        self.active_pipelines[pipeline_id] = result
        
        try:
            logger.info(f"🚀 Starting backfill pipeline: {pipeline_id}, symbol={symbol}, start={start}, end={end}")
            
            # Stage 1: Download in batches
            result.stage = PipelineStage.DOWNLOAD
            
            current_start = start
            total_rows = 0
            
            while current_start < end:
                current_end = min(
                    current_start + timedelta(days=batch_days),
                    end
                )
                
                logger.info(f"Downloading batch: {current_start} to {current_end}")
                
                # Download batch
                batch_result = self.market_service.download_historical_data(
                    symbol=symbol,
                    start=current_start,
                    end=current_end,
                    interval=interval
                )
                
                batch_rows = batch_result.get("rows_added", 0)
                total_rows += batch_rows
                
                logger.info(f"Batch complete: {batch_rows} rows")
                
                current_start = current_end
            
            result.rows_downloaded = total_rows
            result.rows_stored = total_rows
            
            # Complete (skip analysis for backfill)
            result.stage = PipelineStage.COMPLETE
            result.status = "success"
            result.end_time = datetime.now()
            
            logger.info(f"✅ Backfill complete: {pipeline_id}, total_rows={total_rows}, duration={result.duration_seconds}s")
            
            return result
            
        except Exception as e:
            result.stage = PipelineStage.FAILED
            result.status = "failed"
            result.end_time = datetime.now()
            result.errors.append(str(e))
            
            logger.error(f"❌ Backfill failed: {pipeline_id}, error={str(e)}")
            
            return result
        
        finally:
            self.active_pipelines.pop(pipeline_id, None)
    
    def run_retraining_pipeline(
        self,
        symbol: str,
        training_days: int = 365,
        interval: str = "1h"
    ) -> PipelineResult:
        """
        Execute model retraining pipeline.
        
        This retrains the HMM model with recent data:
        1. Query training data from storage
        2. Train HMM model
        3. Reclassify recent regimes
        4. Generate insights
        
        Args:
            symbol: Trading pair
            training_days: Days of data for training (default: 365)
            interval: Timeframe (default: 1h)
            
        Returns:
            PipelineResult with execution metrics
        """
        pipeline_id = f"retrain_{symbol}_{datetime.now().timestamp()}"
        result = PipelineResult(
            pipeline_id=pipeline_id,
            start_time=datetime.now()
        )
        self.active_pipelines[pipeline_id] = result
        
        try:
            logger.info(f"🚀 Starting retraining pipeline: {pipeline_id}, symbol={symbol}, training_days={training_days}")
            
            # Stage 1: Query training data
            result.stage = PipelineStage.DOWNLOAD
            
            end = datetime.now()
            start = end - timedelta(days=training_days)
            
            # Stage 2: Train model
            result.stage = PipelineStage.ANALYSIS
            
            self.analysis_service.train_regime_classifier(
                symbol=symbol,
                start=start,
                end=end,
                interval=interval
            )
            
            logger.info("✅ Model training complete")
            
            # Stage 3: Reclassify recent regimes (last 30 days)
            recent_start = datetime.now() - timedelta(days=30)
            
            regimes = self.analysis_service.classify_market_regime(
                symbol=symbol,
                start=recent_start,
                end=end,
                interval=interval
            )
            
            result.regimes_classified = len(regimes)
            
            # Complete
            result.stage = PipelineStage.COMPLETE
            result.status = "success"
            result.end_time = datetime.now()
            
            logger.info(f"✅ Retraining pipeline complete: {pipeline_id}, regimes={result.regimes_classified}, duration={result.duration_seconds}s")
            
            return result
            
        except Exception as e:
            result.stage = PipelineStage.FAILED
            result.status = "failed"
            result.end_time = datetime.now()
            result.errors.append(str(e))
            
            logger.error(f"❌ Retraining failed: {pipeline_id}, error={str(e)}")
            
            return result
        
        finally:
            self.active_pipelines.pop(pipeline_id, None)
    
    # ==================== Monitoring ====================
    
    def get_active_pipelines(self) -> List[PipelineResult]:
        """
        Get list of currently running pipelines.
        
        Returns:
            List of active pipeline results
        """
        return list(self.active_pipelines.values())
    
    def get_pipeline_status(self, pipeline_id: str) -> Optional[PipelineResult]:
        """
        Get status of a specific pipeline.
        
        Args:
            pipeline_id: Pipeline identifier
            
        Returns:
            Pipeline result or None if not found
        """
        return self.active_pipelines.get(pipeline_id)
