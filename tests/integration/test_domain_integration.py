"""
Integration Test: Domain Layer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

End-to-end tests for domain services working together.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

from src.domain.models import MarketData, MarketDataCollection
from src.domain.services import (
    TechnicalAnalysisService,
    RiskCalculatorService,
    RegimeClassifierService,
)


@pytest.fixture
def large_ohlcv_dataset():
    """
    Generate large synthetic OHLCV dataset for testing.
    
    Simulates 1 year of hourly data (~8,760 rows).
    """
    np.random.seed(42)
    
    # Generate 1 year of hourly timestamps
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    dates = pd.date_range(start=start_date, periods=8760, freq="1h")
    
    # Simulate price with trend and volatility
    returns = np.random.randn(8760) * 0.02  # 2% hourly volatility
    returns += 0.0001  # Slight upward drift
    
    close_prices = 45000 * np.exp(np.cumsum(returns))
    
    # Generate OHLCV
    df = pd.DataFrame({
        "timestamp": dates,
        "open": close_prices * (1 + np.random.randn(8760) * 0.002),
        "high": close_prices * (1 + np.abs(np.random.randn(8760)) * 0.005),
        "low": close_prices * (1 - np.abs(np.random.randn(8760)) * 0.005),
        "close": close_prices,
        "volume": np.random.randint(1000, 5000, 8760),
    })
    
    # Ensure OHLC validity
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)
    
    return df


class TestDomainIntegration:
    """Integration tests for domain layer."""
    
    def test_full_workflow(self, large_ohlcv_dataset):
        """
        Test complete workflow: Technical Analysis → Risk Calculation → Regime Classification.
        
        This simulates a real use case.
        """
        df = large_ohlcv_dataset
        
        # Step 1: Technical Analysis
        ta_service = TechnicalAnalysisService()
        df_with_indicators = ta_service.calculate_all_indicators(df)
        
        # Verify indicators were calculated
        assert "rsi" in df_with_indicators.columns
        assert "macd" in df_with_indicators.columns
        assert "bb_upper" in df_with_indicators.columns
        assert "atr" in df_with_indicators.columns
        
        # Step 2: Risk Calculation
        risk_calc = RiskCalculatorService(risk_free_rate=0.02)
        risk_metrics = risk_calc.calculate_all_metrics(
            df["close"],
            periods_per_year=8760  # Hourly data
        )
        
        # Verify risk metrics
        assert risk_metrics.var_95 < 0
        assert risk_metrics.sharpe_ratio is not None
        assert risk_metrics.max_drawdown <= 0
        
        # Step 3: Regime Classification
        regime_classifier = RegimeClassifierService(n_regimes=4)
        regime_classifier.fit(df)
        
        # Classify regimes
        regimes = regime_classifier.classify(df.tail(100))  # Last 100 hours
        
        assert len(regimes) > 0
        assert all(r.confidence >= 0 and r.confidence <= 1 for r in regimes)
        
        # Step 4: Detect transitions
        transitions = regime_classifier.detect_transitions(regimes)
        
        # Should have some transitions (not all same regime)
        assert isinstance(transitions, list)
    
    def test_technical_analysis_features_for_regime(self, large_ohlcv_dataset):
        """Test that TA features work correctly with regime classification."""
        df = large_ohlcv_dataset
        
        ta_service = TechnicalAnalysisService()
        features = ta_service.extract_features_for_regime_classification(df)
        
        # Features should be valid
        assert len(features) > 0
        assert not features.isna().all().any()  # No completely NaN columns
        
        # Required features
        required = ["returns", "volatility", "rsi", "macd_histogram", "atr_normalized"]
        for col in required:
            assert col in features.columns
        
        # Use features for regime classification
        regime_classifier = RegimeClassifierService(n_regimes=4)
        regime_classifier.fit(df)
        
        # Should succeed
        latest_regime = regime_classifier.classify_latest(df)
        assert latest_regime.regime is not None
    
    def test_risk_metrics_with_regime_changes(self, large_ohlcv_dataset):
        """Test risk metrics during different market regimes."""
        df = large_ohlcv_dataset
        
        # Classify regimes
        regime_classifier = RegimeClassifierService(n_regimes=4)
        regime_classifier.fit(df)
        regimes = regime_classifier.classify(df)
        
        # Calculate risk for each regime type
        risk_calc = RiskCalculatorService()
        
        from src.domain.models import RegimeType
        
        for regime_type in [RegimeType.BULL, RegimeType.BEAR, RegimeType.NEUTRAL]:
            # Find periods with this regime
            regime_periods = [r for r in regimes if r.regime == regime_type]
            
            if len(regime_periods) > 50:  # Need sufficient data
                # Get timestamps
                regime_timestamps = [r.timestamp for r in regime_periods[:50]]
                
                # Filter data
                regime_data = df[df["timestamp"].isin(regime_timestamps)]
                
                if len(regime_data) > 30:
                    # Calculate risk metrics for this regime
                    metrics = risk_calc.calculate_all_metrics(
                        regime_data["close"],
                        periods_per_year=8760
                    )
                    
                    # Risk metrics should vary by regime
                    assert metrics.volatility >= 0
                    assert metrics.var_95 < 0
    
    def test_market_data_domain_model_integration(self, large_ohlcv_dataset):
        """Test MarketData domain model with real services."""
        df = large_ohlcv_dataset.head(100)
        
        # Convert to domain model
        collection = MarketDataCollection.from_dataframe(
            df.set_index("timestamp"),
            symbol="BTCUSDT",
            interval="1h"
        )
        
        # Verify collection
        assert len(collection) == 100
        assert collection.symbol == "BTCUSDT"
        
        # Get latest data points
        latest = collection.get_latest(n=10)
        assert len(latest) == 10
        
        # Convert back to DataFrame
        df_reconverted = collection.to_dataframe()
        
        # Run technical analysis on reconverted data
        ta_service = TechnicalAnalysisService()
        
        # Reset index to have timestamp column
        df_with_timestamp = df_reconverted.reset_index()
        
        indicators = ta_service.calculate_all_indicators(df_with_timestamp)
        
        assert "rsi" in indicators.columns
    
    def test_regime_classifier_persistence(self, large_ohlcv_dataset):
        """Test that regime classifier can be fitted once and reused."""
        df = large_ohlcv_dataset
        
        # Fit classifier
        classifier = RegimeClassifierService(n_regimes=4)
        classifier.fit(df[:7000])  # Train on first 7000 hours
        
        # Classify on different data (last 1000 hours)
        test_data = df[7000:]
        regimes = classifier.classify(test_data)
        
        assert len(regimes) > 0
        
        # Verify all regimes are classified
        for regime in regimes:
            assert regime.regime is not None
            assert 0 <= regime.confidence <= 1
            assert len(regime.probabilities) == 4  # 4 regimes


class TestPerformance:
    """Performance tests for domain layer."""
    
    def test_technical_analysis_performance(self, large_ohlcv_dataset):
        """Test TA performance on large dataset."""
        import time
        
        df = large_ohlcv_dataset
        
        ta_service = TechnicalAnalysisService()
        
        start = time.time()
        df_with_indicators = ta_service.calculate_all_indicators(df)
        elapsed = time.time() - start
        
        # Should complete in reasonable time (<5 seconds for 8760 rows)
        assert elapsed < 5.0
        assert len(df_with_indicators) == len(df)
    
    def test_regime_classification_performance(self, large_ohlcv_dataset):
        """Test regime classification performance."""
        import time
        
        df = large_ohlcv_dataset
        
        classifier = RegimeClassifierService(n_regimes=4)
        
        # Fit time
        start = time.time()
        classifier.fit(df)
        fit_time = time.time() - start
        
        # Should fit in reasonable time (<30 seconds)
        assert fit_time < 30.0
        
        # Classify time
        start = time.time()
        regimes = classifier.classify(df.tail(100))
        classify_time = time.time() - start
        
        # Should classify quickly (<2 seconds for 100 points)
        assert classify_time < 2.0
        # Note: Due to rolling window calculations (20-period volatility),
        # we lose ~20 rows at the start, so expect ~80 regimes from 100 input rows
        assert len(regimes) >= 80
