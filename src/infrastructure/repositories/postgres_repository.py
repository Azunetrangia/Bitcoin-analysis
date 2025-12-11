"""
PostgreSQL/Supabase Market Data Repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implementation of IMarketDataRepository using Supabase/PostgreSQL.

This is the hot storage repository (last 30 days of data).
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional

from src.domain.interfaces.market_data_repository import IMarketDataRepository
from src.domain.models.market_data import MarketData
from src.infrastructure.database.supabase_client import SupabaseClient
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class PostgresMarketDataRepository(IMarketDataRepository):
    """
    Repository implementation using PostgreSQL/Supabase for hot storage.
    
    Storage Strategy:
    - Last 30 days in PostgreSQL
    - Fast writes and queries
    - Real-time updates
    
    Use Cases:
    - Recent data access (< 30 days)
    - Real-time monitoring
    - Quick lookups for current regime
    """
    
    def __init__(self, supabase_client: SupabaseClient):
        """
        Initialize repository.
        
        Args:
            supabase_client: Initialized Supabase client
        """
        self.client = supabase_client
        logger.info(f"✅ Postgres repository initialized")
    
    def get_by_date_range(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> List[MarketData]:
        """
        Get market data for date range.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            
        Returns:
            List of MarketData objects
        """
        # Query from Supabase
        df = self.client.get_market_data(symbol, interval, start, end)
        
        if df.empty:
            return []
        
        # Convert to domain objects
        market_data_list = []
        
        for _, row in df.iterrows():
            market_data = MarketData(
                symbol=symbol,
                interval=interval,
                timestamp=row["timestamp"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"])
            )
            market_data_list.append(market_data)
        
        logger.debug(
            f"📂 Retrieved from Postgres",
            symbol=symbol,
            interval=interval,
            rows=len(market_data_list)
        )
        
        return market_data_list
    
    def get_latest(
        self,
        symbol: str,
        interval: str,
        limit: int = 100
    ) -> List[MarketData]:
        """
        Get latest N records.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            limit: Number of records
            
        Returns:
            List of MarketData objects
        """
        # Query latest from Supabase
        df = self.client.get_latest_market_data(symbol, interval, limit)
        
        if df.empty:
            return []
        
        # Convert to domain objects
        market_data_list = []
        
        for _, row in df.iterrows():
            market_data = MarketData(
                symbol=symbol,
                interval=interval,
                timestamp=row["timestamp"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"])
            )
            market_data_list.append(market_data)
        
        return market_data_list
    
    def save(self, data: List[MarketData]) -> int:
        """
        Save market data.
        
        Args:
            data: List of MarketData objects
            
        Returns:
            Number of records saved
        """
        if not data:
            return 0
        
        # Convert to DataFrame
        records = []
        
        for md in data:
            records.append({
                "symbol": md.symbol,
                "interval": md.interval,
                "timestamp": md.timestamp,
                "open": md.open,
                "high": md.high,
                "low": md.low,
                "close": md.close,
                "volume": md.volume
            })
        
        df = pd.DataFrame(records)
        
        # Insert into Supabase
        count = self.client.insert_market_data(df)
        
        logger.info(
            f"💾 Saved to Postgres",
            symbol=data[0].symbol,
            interval=data[0].interval,
            rows=count
        )
        
        return count
    
    def exists(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> bool:
        """
        Check if data exists for date range.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            
        Returns:
            True if data exists
        """
        df = self.client.get_market_data(symbol, interval, start, end)
        return not df.empty
    
    def delete_by_date_range(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> int:
        """
        Delete data for date range.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            
        Returns:
            Number of records deleted
        """
        count = self.client.delete_market_data_by_date(
            symbol, interval, start, end
        )
        
        logger.info(
            f"🗑️ Deleted from Postgres",
            symbol=symbol,
            interval=interval,
            rows=count
        )
        
        return count
    
    def get_available_dates(
        self,
        symbol: str,
        interval: str
    ) -> List[datetime]:
        """
        Get list of available dates.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            
        Returns:
            List of datetime objects
        """
        # Get last 30 days
        end = datetime.now()
        start = end - timedelta(days=30)
        
        df = self.client.get_market_data(symbol, interval, start, end)
        
        if df.empty:
            return []
        
        # Return unique dates
        dates = df["timestamp"].dt.date.unique()
        
        return sorted([datetime.combine(d, datetime.min.time()) for d in dates])
