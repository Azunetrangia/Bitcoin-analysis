"""
Market Data Model
~~~~~~~~~~~~~~~~~

Domain model for OHLCV time-series data.

This is a rich domain model that encapsulates business logic
and validation rules for market data.
"""

from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from typing import List


@dataclass(frozen=True)
class MarketData:
    """
    Immutable domain model for OHLCV market data.
    
    Attributes:
        timestamp: UTC timestamp
        open: Opening price
        high: Highest price
        low: Lowest price
        close: Closing price
        volume: Trading volume
        symbol: Trading pair (e.g., 'BTCUSDT')
        interval: Time interval (e.g., '1h', '1d')
    """
    
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    
    def __post_init__(self) -> None:
        """Validate data integrity after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """
        Validate OHLCV data integrity.
        
        Raises:
            ValueError: If data is invalid
        """
        # Check for negative values
        if any(val < 0 for val in [self.open, self.high, self.low, self.close, self.volume]):
            raise ValueError("Price and volume must be non-negative")
        
        # Check OHLC relationships
        if self.high < self.low:
            raise ValueError(f"High ({self.high}) < Low ({self.low})")
        
        if self.high < self.open or self.high < self.close:
            raise ValueError("High must be >= Open and Close")
        
        if self.low > self.open or self.low > self.close:
            raise ValueError("Low must be <= Open and Close")
    
    def price_change(self) -> float:
        """
        Calculate price change (close - open).
        
        Returns:
            Price change in absolute terms
        """
        return self.close - self.open
    
    def price_change_pct(self) -> float:
        """
        Calculate percentage price change.
        
        Returns:
            Price change as percentage (0.05 = 5%)
        """
        if self.open == 0:
            return 0.0
        return (self.close - self.open) / self.open
    
    def typical_price(self) -> float:
        """
        Calculate typical price: (High + Low + Close) / 3
        
        Returns:
            Typical price
        """
        return (self.high + self.low + self.close) / 3
    
    def is_bullish(self) -> bool:
        """Check if this is a bullish candle (close > open)."""
        return self.close > self.open
    
    def is_bearish(self) -> bool:
        """Check if this is a bearish candle (close < open)."""
        return self.close < self.open
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "symbol": self.symbol,
            "interval": self.interval,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MarketData":
        """
        Create MarketData from dictionary.
        
        Args:
            data: Dictionary with OHLCV data
            
        Returns:
            MarketData instance
        """
        if isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        
        return cls(**data)


@dataclass
class MarketDataCollection:
    """
    Collection of MarketData objects with batch operations.
    
    This is a domain aggregate that manages a collection of MarketData entities.
    """
    
    data: List[MarketData]
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    
    def __len__(self) -> int:
        """Number of data points."""
        return len(self.data)
    
    def __getitem__(self, idx: int) -> MarketData:
        """Get data point by index."""
        return self.data[idx]
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert to pandas DataFrame.
        
        Returns:
            DataFrame with OHLCV columns
        """
        if not self.data:
            return pd.DataFrame()
        
        records = [item.to_dict() for item in self.data]
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")
        
        return df
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, symbol: str = "BTCUSDT", interval: str = "1h") -> "MarketDataCollection":
        """
        Create collection from DataFrame.
        
        Args:
            df: DataFrame with OHLCV columns and timestamp index
            symbol: Trading pair
            interval: Time interval
            
        Returns:
            MarketDataCollection instance
        """
        df = df.reset_index()
        
        data = [
            MarketData(
                timestamp=row["timestamp"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                symbol=symbol,
                interval=interval,
            )
            for _, row in df.iterrows()
        ]
        
        return cls(data=data, symbol=symbol, interval=interval)
    
    def get_latest(self, n: int = 1) -> List[MarketData]:
        """
        Get latest N data points.
        
        Args:
            n: Number of latest points to retrieve
            
        Returns:
            List of MarketData (most recent first)
        """
        return self.data[-n:][::-1]
    
    def filter_by_date_range(self, start: datetime, end: datetime) -> "MarketDataCollection":
        """
        Filter data by date range.
        
        Args:
            start: Start datetime (inclusive)
            end: End datetime (inclusive)
            
        Returns:
            New MarketDataCollection with filtered data
        """
        filtered = [
            item for item in self.data
            if start <= item.timestamp <= end
        ]
        
        return MarketDataCollection(data=filtered, symbol=self.symbol, interval=self.interval)
