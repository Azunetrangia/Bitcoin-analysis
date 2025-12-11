"""
Unit tests for AnalysisService.

Tests application layer analysis orchestration.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock
import pandas as pd
import numpy as np

from src.application.services.analysis_service import AnalysisService


@pytest.fixture
def mock_market_data_service():
    """Create mock market data service."""
    service = Mock()
    
    # Create realistic sample dataframe with volatility
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="1h", tz="UTC")
    
    # Create realistic price series with random walk
    returns = np.random.normal(0.0001, 0.01, 100)  # Mean slightly positive, with volatility
    prices = 45000 * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        "timestamp": dates,
        "open": prices * 0.999,
        "high": prices * 1.002,
        "low": prices * 0.998,
        "close": prices,
        "volume": np.random.uniform(100, 200, 100)
    })
    
    service.get_data_as_dataframe.return_value = df
    
    return service


@pytest.fixture
def service(mock_market_data_service):
    """Create AnalysisService with mocked market data service and mocked risk/regime services."""
    # Create a mock risk service that returns valid metrics
    from unittest.mock import Mock
    from src.domain.models.risk_metrics import RiskMetrics
    from datetime import datetime
    
    mock_risk_service = Mock()
    mock_risk_service.calculate_all_metrics.return_value = RiskMetrics(
        timestamp=datetime(2024, 1, 1),
        var_95=-0.03,  # Negative = loss
        var_99=-0.05,
        expected_shortfall_95=-0.04,
        expected_shortfall_99=-0.06,
        sharpe_ratio=1.5,
        sortino_ratio=2.0,
        max_drawdown=-0.15,  # Negative = 15% drawdown
        volatility=0.02,
        mean_return=0.001
    )
    
    # Mock regime service
    from src.domain.models.market_regime import MarketRegime, RegimeType
    
    mock_regime_service = Mock()
    mock_regime_service.is_fitted = True
    mock_regime_service.classify_latest.return_value = MarketRegime(
        timestamp=datetime(2024, 1, 1),
        regime=RegimeType.BULL,
        confidence=0.85,
        probabilities={RegimeType.BULL: 0.85, RegimeType.BEAR: 0.10, RegimeType.NEUTRAL: 0.05}
    )
    mock_regime_service.predict_proba.return_value = {RegimeType.BULL: 0.85, RegimeType.BEAR: 0.10, RegimeType.NEUTRAL: 0.05}
    mock_regime_service.classify.return_value = [0] * 100  # 0 = BULL
    mock_regime_service.detect_transitions.return_value = []
    
    return AnalysisService(
        market_data_service=mock_market_data_service,
        risk_service=mock_risk_service,
        regime_service=mock_regime_service
    )


class TestAnalysisService:
    """Test AnalysisService functionality."""
    
    def test_initialization(self, service):
        """Test service initializes correctly."""
        assert service is not None
        assert service.market_data_service is not None
        assert service.ta_service is not None
        assert service.risk_service is not None
        assert service.regime_service is not None
    
    def test_analyze_full_report(self, service, mock_market_data_service):
        """Test full analysis report generation."""
        end = datetime(2024, 1, 5)
        start = end - timedelta(days=7)
        
        report = service.analyze_full_report(
            symbol="btcusdt",
            interval="1h",
            start=start,
            end=end
        )
        
        # Check report structure
        assert isinstance(report, dict)
        assert report["symbol"] == "btcusdt"
        assert report["interval"] == "1h"
        assert "period" in report
        assert "latest_price" in report
        assert "technical_indicators" in report
        assert "risk_metrics" in report
        assert "regime" in report
        
        # Check market data service was called
        mock_market_data_service.get_data_as_dataframe.assert_called_once()
    
    def test_analyze_full_report_no_data(self, service, mock_market_data_service):
        """Test full analysis with no data."""
        mock_market_data_service.get_data_as_dataframe.return_value = pd.DataFrame()
        
        end = datetime(2024, 1, 5)
        start = end - timedelta(days=7)
        
        report = service.analyze_full_report(
            symbol="btcusdt",
            interval="1h",
            start=start,
            end=end
        )
        
        assert "error" in report
        assert report["error"] == "No data available"
    
    def test_analyze_technical(self, service, mock_market_data_service):
        """Test technical analysis returns DataFrame."""
        end = datetime(2024, 1, 5)
        start = end - timedelta(days=7)
        
        result = service.analyze_technical(
            symbol="btcusdt",
            interval="1h",
            start=start,
            end=end
        )
        
        # Check result is DataFrame with indicators
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 100
        assert "rsi" in result.columns
        
        # Check market data service was called
        mock_market_data_service.get_data_as_dataframe.assert_called_once()
    
    def test_analyze_technical_no_data(self, service, mock_market_data_service):
        """Test technical analysis with no data returns empty DataFrame."""
        mock_market_data_service.get_data_as_dataframe.return_value = pd.DataFrame()
        
        end = datetime(2024, 1, 5)
        start = end - timedelta(days=7)
        
        result = service.analyze_technical(
            symbol="btcusdt",
            interval="1h",
            start=start,
            end=end
        )
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    def test_analyze_risk(self, service, mock_market_data_service):
        """Test risk analysis returns RiskMetrics model."""
        from src.domain.models.risk_metrics import RiskMetrics
        
        end = datetime(2024, 1, 5)
        start = end - timedelta(days=7)
        
        result = service.analyze_risk(
            symbol="btcusdt",
            interval="1h",
            start=start,
            end=end
        )
        
        # Check result is RiskMetrics model
        assert isinstance(result, RiskMetrics)
        assert result.sharpe_ratio == 1.5
        assert result.max_drawdown == -0.15
        
        # Check market data service was called
        mock_market_data_service.get_data_as_dataframe.assert_called_once()
    
    def test_analyze_risk_no_data(self, service, mock_market_data_service):
        """Test risk analysis with no data returns empty dict."""
        mock_market_data_service.get_data_as_dataframe.return_value = pd.DataFrame()
        
        end = datetime(2024, 1, 5)
        start = end - timedelta(days=7)
        
        result = service.analyze_risk(
            symbol="btcusdt",
            interval="1h",
            start=start,
            end=end
        )
        
        assert isinstance(result, dict)
        assert result == {}

