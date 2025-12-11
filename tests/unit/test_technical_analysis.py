"""
Test: Technical Analysis Service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unit tests for technical indicator calculations.
"""

import pytest
import pandas as pd
import numpy as np
from src.domain.services.technical_analysis import TechnicalAnalysisService
from src.shared.exceptions.custom_exceptions import TechnicalIndicatorError


@pytest.fixture
def ta_service():
    """Technical Analysis service instance."""
    return TechnicalAnalysisService()


@pytest.fixture
def sample_prices():
    """Sample price data for testing."""
    np.random.seed(42)
    prices = pd.Series(
        45000 + np.cumsum(np.random.randn(100) * 100),
        name="close"
    )
    return prices


@pytest.fixture
def sample_ohlc():
    """Sample OHLC data for testing."""
    np.random.seed(42)
    close = 45000 + np.cumsum(np.random.randn(100) * 100)
    
    df = pd.DataFrame({
        "open": close - np.random.rand(100) * 50,
        "high": close + np.random.rand(100) * 100,
        "low": close - np.random.rand(100) * 100,
        "close": close,
        "volume": np.random.randint(1000, 2000, 100),
    })
    
    return df


class TestRSI:
    """Test cases for RSI calculation."""
    
    def test_rsi_calculation(self, ta_service, sample_prices):
        """Test basic RSI calculation."""
        rsi = ta_service.calculate_rsi(sample_prices, period=14)
        
        # RSI should be between 0 and 100
        assert (rsi.dropna() >= 0).all()
        assert (rsi.dropna() <= 100).all()
        
        # Should have NaN values at the start (due to rolling window + diff)
        # With period=14, we get 13 NaN values (first diff is NaN, then 12 more for rolling)
        assert rsi.isna().sum() >= 13
    
    def test_rsi_insufficient_data(self, ta_service):
        """Test RSI with insufficient data."""
        short_prices = pd.Series([45000, 45100, 45200])
        
        with pytest.raises(TechnicalIndicatorError):
            ta_service.calculate_rsi(short_prices, period=14)
    
    def test_rsi_custom_period(self, ta_service, sample_prices):
        """Test RSI with custom period."""
        rsi_7 = ta_service.calculate_rsi(sample_prices, period=7)
        rsi_21 = ta_service.calculate_rsi(sample_prices, period=21)
        
        # Different periods should give different results
        assert not rsi_7.equals(rsi_21)


class TestMACD:
    """Test cases for MACD calculation."""
    
    def test_macd_calculation(self, ta_service, sample_prices):
        """Test basic MACD calculation."""
        macd = ta_service.calculate_macd(sample_prices)
        
        assert "macd" in macd
        assert "signal" in macd
        assert "histogram" in macd
        
        # Histogram should equal MACD - Signal
        np.testing.assert_array_almost_equal(
            macd["histogram"].dropna(),
            (macd["macd"] - macd["signal"]).dropna()
        )
    
    def test_macd_custom_params(self, ta_service, sample_prices):
        """Test MACD with custom parameters."""
        macd_custom = ta_service.calculate_macd(
            sample_prices,
            fast_period=8,
            slow_period=17,
            signal_period=9
        )
        
        assert len(macd_custom) == 3


class TestBollingerBands:
    """Test cases for Bollinger Bands calculation."""
    
    def test_bollinger_bands_calculation(self, ta_service, sample_prices):
        """Test basic Bollinger Bands calculation."""
        bb = ta_service.calculate_bollinger_bands(sample_prices)
        
        assert "upper" in bb
        assert "middle" in bb
        assert "lower" in bb
        assert "bandwidth" in bb
        
        # Upper should be > Middle > Lower
        valid_data = ~bb["upper"].isna()
        assert (bb["upper"][valid_data] >= bb["middle"][valid_data]).all()
        assert (bb["middle"][valid_data] >= bb["lower"][valid_data]).all()
    
    def test_bollinger_bands_bandwidth(self, ta_service, sample_prices):
        """Test Bollinger Bands bandwidth calculation."""
        bb = ta_service.calculate_bollinger_bands(sample_prices, period=20)
        
        # Bandwidth should be positive
        assert (bb["bandwidth"].dropna() > 0).all()


class TestATR:
    """Test cases for ATR calculation."""
    
    def test_atr_calculation(self, ta_service, sample_ohlc):
        """Test basic ATR calculation."""
        atr = ta_service.calculate_atr(
            sample_ohlc["high"],
            sample_ohlc["low"],
            sample_ohlc["close"],
            period=14
        )
        
        # ATR should be positive
        assert (atr.dropna() > 0).all()
    
    def test_atr_reflects_volatility(self, ta_service):
        """Test that ATR increases with volatility."""
        # Low volatility
        df_low_vol = pd.DataFrame({
            "high": [100, 101, 100, 101, 100] * 10,
            "low": [99, 100, 99, 100, 99] * 10,
            "close": [100, 100, 100, 100, 100] * 10,
        })
        
        # High volatility
        df_high_vol = pd.DataFrame({
            "high": [100, 110, 90, 120, 80] * 10,
            "low": [90, 100, 80, 110, 70] * 10,
            "close": [95, 105, 85, 115, 75] * 10,
        })
        
        atr_low = ta_service.calculate_atr(
            df_low_vol["high"],
            df_low_vol["low"],
            df_low_vol["close"],
            period=5
        )
        
        atr_high = ta_service.calculate_atr(
            df_high_vol["high"],
            df_high_vol["low"],
            df_high_vol["close"],
            period=5
        )
        
        # High volatility ATR should be greater
        assert atr_high.mean() > atr_low.mean()


class TestBatchCalculations:
    """Test cases for batch indicator calculations."""
    
    def test_calculate_all_indicators(self, ta_service, sample_ohlc):
        """Test calculating all indicators at once."""
        result = ta_service.calculate_all_indicators(sample_ohlc)
        
        # Should have all indicator columns
        expected_cols = [
            "rsi", "macd", "macd_signal", "macd_histogram",
            "bb_upper", "bb_middle", "bb_lower", "bb_bandwidth",
            "atr", "sma_20", "sma_50", "ema_20"
        ]
        
        for col in expected_cols:
            assert col in result.columns
        
        # Original columns should be preserved
        assert "close" in result.columns
        assert "volume" in result.columns
    
    def test_extract_features_for_regime(self, ta_service, sample_ohlc):
        """Test feature extraction for regime classification."""
        features = ta_service.extract_features_for_regime_classification(sample_ohlc)
        
        # Should have specific feature columns
        expected_features = [
            "returns", "volatility", "rsi", 
            "macd_histogram", "atr_normalized", "volume_change"
        ]
        
        for feature in expected_features:
            assert feature in features.columns
        
        # Should have no NaN values (dropped)
        assert features.isna().sum().sum() == 0


class TestMovingAverages:
    """Test cases for moving averages."""
    
    def test_sma_calculation(self, ta_service, sample_prices):
        """Test Simple Moving Average."""
        sma = ta_service.calculate_sma(sample_prices, period=20)
        
        # SMA should smooth the data
        assert len(sma) == len(sample_prices)
        assert sma.isna().sum() == 19  # First 19 values are NaN
    
    def test_ema_calculation(self, ta_service, sample_prices):
        """Test Exponential Moving Average."""
        ema = ta_service.calculate_ema(sample_prices, period=20)
        
        # EMA reacts faster than SMA
        sma = ta_service.calculate_sma(sample_prices, period=20)
        
        # Both should exist
        assert len(ema) == len(sma)
        
        # EMA should have fewer NaN values (only the first one)
        assert ema.isna().sum() < sma.isna().sum()
