"""
Test: MarketData Domain Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unit tests for MarketData entity and validation logic.
"""

import pytest
from datetime import datetime, timezone
from src.domain.models.market_data import MarketData, MarketDataCollection


class TestMarketData:
    """Test cases for MarketData entity."""
    
    def test_valid_market_data(self, sample_market_data):
        """Test creation of valid MarketData."""
        assert sample_market_data.symbol == "BTCUSDT"
        assert sample_market_data.open == 45000.0
        assert sample_market_data.close == 45200.0
    
    def test_price_change(self, sample_market_data):
        """Test price change calculation."""
        assert sample_market_data.price_change() == 200.0  # 45200 - 45000
    
    def test_price_change_pct(self, sample_market_data):
        """Test percentage price change."""
        expected = (45200 - 45000) / 45000
        assert abs(sample_market_data.price_change_pct() - expected) < 1e-6
    
    def test_is_bullish(self, sample_market_data):
        """Test bullish candle detection."""
        assert sample_market_data.is_bullish() is True
        assert sample_market_data.is_bearish() is False
    
    def test_invalid_high_low(self):
        """Test validation: high < low should raise ValueError."""
        with pytest.raises(ValueError, match="High.*< Low"):
            MarketData(
                timestamp=datetime.now(timezone.utc),
                open=45000,
                high=44000,  # Invalid: high < low
                low=45000,
                close=45000,
                volume=1000,
            )
    
    def test_negative_price(self):
        """Test validation: negative prices should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            MarketData(
                timestamp=datetime.now(timezone.utc),
                open=-100,  # Invalid
                high=45000,
                low=44000,
                close=45000,
                volume=1000,
            )
    
    def test_to_dict_and_from_dict(self, sample_market_data):
        """Test serialization and deserialization."""
        data_dict = sample_market_data.to_dict()
        
        assert isinstance(data_dict, dict)
        assert "timestamp" in data_dict
        assert data_dict["open"] == 45000.0
        
        # Round-trip
        reconstructed = MarketData.from_dict(data_dict)
        assert reconstructed.open == sample_market_data.open
        assert reconstructed.close == sample_market_data.close


class TestMarketDataCollection:
    """Test cases for MarketDataCollection aggregate."""
    
    def test_from_dataframe(self, sample_ohlcv_data):
        """Test creation from DataFrame."""
        collection = MarketDataCollection.from_dataframe(
            sample_ohlcv_data.set_index("timestamp"),
            symbol="BTCUSDT",
            interval="1h"
        )
        
        assert len(collection) == 10
        assert collection.symbol == "BTCUSDT"
    
    def test_to_dataframe(self, sample_ohlcv_data):
        """Test conversion to DataFrame."""
        collection = MarketDataCollection.from_dataframe(
            sample_ohlcv_data.set_index("timestamp")
        )
        
        df = collection.to_dataframe()
        
        assert len(df) == 10
        assert "open" in df.columns
        assert "close" in df.columns
    
    def test_get_latest(self, sample_ohlcv_data):
        """Test getting latest N data points."""
        collection = MarketDataCollection.from_dataframe(
            sample_ohlcv_data.set_index("timestamp")
        )
        
        latest_3 = collection.get_latest(n=3)
        
        assert len(latest_3) == 3
        # Latest should come first
        assert latest_3[0].close == 45650  # Last row
