"""
Pytest Fixtures
~~~~~~~~~~~~~~~

Shared fixtures for all tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone


@pytest.fixture
def sample_market_data():
    """Create valid sample MarketData."""
    from src.domain.models.market_data import MarketData
    
    return MarketData(
        symbol="BTCUSDT",
        interval="1h",
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=45000.0,
        high=45300.0,  # Must be >= open and close
        low=44900.0,
        close=45200.0,
        volume=1000.5
    )


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV DataFrame with valid data."""
    dates = pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC")
    
    # Create realistic OHLCV data where high >= max(open, close) and low <= min(open, close)
    closes = np.linspace(45000, 45650, 10)
    opens = closes + np.random.uniform(-50, 50, 10)
    
    # Ensure high is >= max(open, close) and low is <= min(open, close)
    highs = np.maximum(opens, closes) + np.random.uniform(10, 100, 10)
    lows = np.minimum(opens, closes) - np.random.uniform(10, 100, 10)
    
    return pd.DataFrame({
        "timestamp": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": np.random.uniform(900, 1100, 10)
    })
