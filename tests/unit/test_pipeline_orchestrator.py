"""
Tests for Pipeline Orchestrator.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.application.services.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineResult,
    PipelineStage
)


@pytest.fixture
def mock_market_service():
    """Create mock market data service."""
    service = Mock()
    service.update_latest_data.return_value = {"rows_added": 5}
    service.download_historical_data.return_value = {"rows_added": 100}
    return service


@pytest.fixture
def mock_analysis_service():
    """Create mock analysis service."""
    service = Mock()
    service.classify_market_regime.return_value = [Mock() for _ in range(10)]
    service.train_regime_classifier.return_value = None
    return service


@pytest.fixture
def orchestrator(mock_market_service, mock_analysis_service):
    """Create pipeline orchestrator instance."""
    return PipelineOrchestrator(
        mock_market_service,
        mock_analysis_service
    )


class TestPipelineOrchestrator:
    """Test pipeline orchestrator."""
    
    def test_initialization(self, orchestrator):
        """Test orchestrator initializes correctly."""
        assert len(orchestrator.active_pipelines) == 0
    
    def test_run_incremental_update_success(
        self, orchestrator, mock_market_service, mock_analysis_service
    ):
        """Test successful incremental update pipeline."""
        result = orchestrator.run_incremental_update(
            symbol="BTCUSDT",
            interval="1h",
            limit=2,
            run_analysis=True
        )
        
        assert result.status == "success"
        assert result.stage == PipelineStage.COMPLETE
        assert result.rows_downloaded == 5
        assert result.rows_stored == 5
        assert result.regimes_classified == 10
        assert result.duration_seconds is not None
        
        mock_market_service.update_latest_data.assert_called_once()
        mock_analysis_service.classify_market_regime.assert_called_once()
    
    def test_run_incremental_update_without_analysis(
        self, orchestrator, mock_market_service, mock_analysis_service
    ):
        """Test incremental update without analysis."""
        result = orchestrator.run_incremental_update(
            symbol="BTCUSDT",
            run_analysis=False
        )
        
        assert result.status == "success"
        assert result.regimes_classified == 0
        mock_analysis_service.classify_market_regime.assert_not_called()
    
    def test_run_incremental_update_failure(
        self, orchestrator, mock_market_service
    ):
        """Test failed incremental update pipeline."""
        mock_market_service.update_latest_data.side_effect = Exception("Download failed")
        
        result = orchestrator.run_incremental_update()
        
        assert result.status == "failed"
        assert result.stage == PipelineStage.FAILED
        assert len(result.errors) > 0
        assert "Download failed" in result.errors[0]
    
    def test_run_backfill_success(
        self, orchestrator, mock_market_service
    ):
        """Test successful backfill pipeline."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 2, 1)
        
        result = orchestrator.run_backfill(
            symbol="BTCUSDT",
            start=start,
            end=end,
            interval="1h",
            batch_days=30
        )
        
        assert result.status == "success"
        assert result.stage == PipelineStage.COMPLETE
        assert result.rows_downloaded > 0
        
        # Should call download for each batch
        assert mock_market_service.download_historical_data.call_count >= 1
    
    def test_run_backfill_multiple_batches(
        self, orchestrator, mock_market_service
    ):
        """Test backfill with multiple batches."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 3, 1)  # 2 months = 2 batches
        
        result = orchestrator.run_backfill(
            symbol="BTCUSDT",
            start=start,
            end=end,
            batch_days=30
        )
        
        assert result.status == "success"
        # Should make 2 calls (one per month)
        assert mock_market_service.download_historical_data.call_count == 2
    
    def test_run_retraining_pipeline_success(
        self, orchestrator, mock_analysis_service
    ):
        """Test successful retraining pipeline."""
        result = orchestrator.run_retraining_pipeline(
            symbol="BTCUSDT",
            training_days=365,
            interval="1h"
        )
        
        assert result.status == "success"
        assert result.stage == PipelineStage.COMPLETE
        assert result.regimes_classified == 10
        
        mock_analysis_service.train_regime_classifier.assert_called_once()
        mock_analysis_service.classify_market_regime.assert_called_once()
    
    def test_run_retraining_pipeline_failure(
        self, orchestrator, mock_analysis_service
    ):
        """Test failed retraining pipeline."""
        mock_analysis_service.train_regime_classifier.side_effect = Exception(
            "Training failed"
        )
        
        result = orchestrator.run_retraining_pipeline("BTCUSDT")
        
        assert result.status == "failed"
        assert result.stage == PipelineStage.FAILED
        assert "Training failed" in result.errors[0]
    
    def test_get_active_pipelines(self, orchestrator):
        """Test tracking active pipelines."""
        # Initially empty
        assert len(orchestrator.get_active_pipelines()) == 0
        
        # Active pipelines are tracked during execution
        # but cleared after completion in our implementation
        result = orchestrator.run_incremental_update()
        
        # After completion, should be cleared
        assert len(orchestrator.get_active_pipelines()) == 0
    
    def test_pipeline_result_duration(self):
        """Test pipeline result duration calculation."""
        result = PipelineResult(
            pipeline_id="test",
            start_time=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        # No end time yet
        assert result.duration_seconds is None
        
        # Set end time
        result.end_time = datetime(2024, 1, 1, 12, 0, 30)
        assert result.duration_seconds == 30.0


class TestPipelineResult:
    """Test PipelineResult dataclass."""
    
    def test_pipeline_result_creation(self):
        """Test creating a pipeline result."""
        result = PipelineResult(
            pipeline_id="test_pipeline",
            start_time=datetime.now()
        )
        
        assert result.pipeline_id == "test_pipeline"
        assert result.stage == PipelineStage.DOWNLOAD
        assert result.status == "running"
        assert result.rows_downloaded == 0
        assert isinstance(result.errors, list)
    
    def test_pipeline_result_with_metrics(self):
        """Test pipeline result with metrics."""
        result = PipelineResult(
            pipeline_id="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            rows_downloaded=100,
            rows_stored=100,
            regimes_classified=50
        )
        
        assert result.rows_downloaded == 100
        assert result.rows_stored == 100
        assert result.regimes_classified == 50
