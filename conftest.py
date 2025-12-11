"""
Pytest Configuration & Fixtures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shared test fixtures for all tests.
"""

import pytest
import pandas as pd
from datetime import datetime, timezone
from src.domain.models.market_data import MarketData


@pytest.fixture
def sample_ohlcv_data():
    """
    Sample OHLCV data for testing.
    
    Returns:
        DataFrame with 10 rows of synthetic data
    """
    dates = pd.date_range(start="2024-01-01", periods=10, freq="1h", tz="UTC")
    
    df = pd.DataFrame({
        "timestamp": dates,
        "open": [45000, 45100, 45200, 45150, 45300, 45400, 45350, 45500, 45600, 45550],
        "high": [45150, 45250, 45300, 45250, 45450, 45500, 45450, 45650, 45700, 45650],
        "low": [44950, 45050, 45150, 45100, 45250, 45350, 45300, 45450, 45550, 45500],
        "close": [45100, 45200, 45150, 45300, 45400, 45350, 45500, 45600, 45550, 45650],
        "volume": [1000, 1100, 950, 1200, 1300, 1050, 1400, 1500, 1250, 1600],
    })
    
    return df


@pytest.fixture
def sample_market_data():
    """
    Sample MarketData domain object.
    
    Returns:
        MarketData instance
    """
    return MarketData(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=45000.0,
        high=45500.0,
        low=44800.0,
        close=45200.0,
        volume=1000.0,
        symbol="BTCUSDT",
        interval="1h",
    )


@pytest.fixture
def mock_settings(monkeypatch):
    """
    Mock settings for testing without .env file.
    
    Usage:
        def test_something(mock_settings):
            # Settings are mocked with test values
            pass
    """
    from src.shared.config.settings import Settings
    
    test_settings = Settings(
        ENVIRONMENT="development",
        DEBUG=True,
        R2_BUCKET_NAME="test-bucket",
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_KEY="test-key",
    )
    
    monkeypatch.setattr("src.shared.config.settings.settings", test_settings)
    
    return test_settings


@pytest.fixture
def temp_data_dir(tmp_path):
    """
    Temporary directory for test data files.
    
    Returns:
        Path to temporary directory (automatically cleaned up after test)
    """
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir
