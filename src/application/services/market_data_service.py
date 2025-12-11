"""
Market Data Service
~~~~~~~~~~~~~~~~~~~

Application service for managing market data operations.

Responsibilities:
- Download historical data from Binance
- Store data in appropriate storage (hot/warm)
- Provide data access interface
- Handle incremental updates

This is the bridge between domain logic and infrastructure.
"""

from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd

from src.domain.models.market_data import MarketData
from src.domain.interfaces.market_data_repository import IMarketDataRepository
from src.infrastructure.data.binance_client import BinanceDataClient
from src.shared.exceptions.custom_exceptions import (
    DataDownloadError,
    StorageError
)
from src.shared.utils.logging_utils import get_logger
from src.shared.utils.datetime_utils import to_utc

logger = get_logger(__name__)


class MarketDataService:
    """
    Service for market data operations.
    
    Use Cases:
    1. Download historical data
    2. Update with latest data
    3. Query data for analysis
    4. Manage data lifecycle
    """
    
    def __init__(
        self,
        repository: IMarketDataRepository,
        binance_client: Optional[BinanceDataClient] = None
    ):
        """
        Initialize service.
        
        Args:
            repository: Data repository (hot/warm/hybrid)
            binance_client: Optional Binance client (creates default if None)
        """
        self.repository = repository
        self.binance_client = binance_client or BinanceDataClient()
        
        logger.info("✅ Market Data Service initialized")
    
    def download_historical_data(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        force: bool = False
    ) -> int:
        """
        Download historical data from Binance and store.
        
        Args:
            symbol: Trading pair (e.g., 'btcusdt')
            interval: Time interval (e.g., '1h', '4h', '1d')
            start: Start datetime
            end: End datetime
            force: If True, re-download even if data exists
            
        Returns:
            Number of records downloaded and saved
            
        Example:
            >>> service = MarketDataService(repository)
            >>> count = service.download_historical_data(
            ...     'btcusdt', '1h',
            ...     datetime(2024, 1, 1),
            ...     datetime(2024, 12, 31)
            ... )
            >>> print(f"Downloaded {count} records")
        """
        start = to_utc(start)
        end = to_utc(end)
        
        logger.info(
            "📥 Starting historical download",
            symbol=symbol,
            interval=interval,
            start=start.isoformat(),
            end=end.isoformat()
        )
        
        # Check if data already exists (unless force=True)
        if not force and self.repository.exists(symbol, interval, start, end):
            logger.warning(
                "⚠️ Data already exists (use force=True to re-download)",
                symbol=symbol,
                interval=interval
            )
            return 0
        
        try:
            # Download from Binance
            df = self.binance_client.download_date_range(
                symbol=symbol,
                interval=interval,
                start=start,
                end=end
            )
            
            if df.empty:
                logger.warning("⚠️ No data downloaded")
                return 0
            
            # Convert to domain objects
            market_data_list = self._dataframe_to_domain(df, symbol, interval)
            
            # Save to repository
            count = self.repository.save(market_data_list)
            
            logger.info(
                "✅ Historical download complete",
                symbol=symbol,
                interval=interval,
                records=count
            )
            
            return count
            
        except DataDownloadError as e:
            logger.error(f"❌ Download failed: {e}")
            raise
        except StorageError as e:
            logger.error(f"❌ Storage failed: {e}")
            raise
    
    def update_latest_data(
        self,
        symbol: str,
        interval: str,
        lookback_hours: int = 24,
        limit: int | None = None
    ) -> dict:
        """
        Update with latest data from Binance.
        
        This is for incremental updates (e.g., daily cron job).
        
        Args:
            symbol: Trading pair
            interval: Time interval
            lookback_hours: Hours to look back (default: 24)
            limit: Max number of candles to fetch (overrides lookback_hours if set)
            
        Returns:
            Dict with rows_added count
            
        Example:
            >>> # Daily update job
            >>> service.update_latest_data('btcusdt', '1h', lookback_hours=25)
            >>> # Or with limit
            >>> service.update_latest_data('btcusdt', '1h', limit=10)
        """
        if limit:
            # Use limit mode - fetch N most recent candles
            end = datetime.now(tz=to_utc(datetime.now()).tzinfo)
            start = end - timedelta(hours=limit)  # Rough estimate
        else:
            # Use lookback_hours mode
            end = datetime.now(tz=to_utc(datetime.now()).tzinfo)
            start = end - timedelta(hours=lookback_hours)
        
        logger.info(
            "🔄 Updating latest data",
            symbol=symbol,
            interval=interval,
            lookback_hours=lookback_hours
        )
        
        try:
            # Download latest data
            df = self.binance_client.download_date_range(
                symbol=symbol,
                interval=interval,
                start=start,
                end=end
            )
            
            if df.empty:
                logger.info("ℹ️ No new data available")
                return {"rows_added": 0, "symbol": symbol, "interval": interval}
            
            # Get existing data to avoid duplicates
            existing_data = self.repository.get_by_date_range(
                symbol, interval, start, end
            )
            
            existing_timestamps = {md.timestamp for md in existing_data}
            
            # Filter out existing timestamps
            df = df[~df["timestamp"].isin(existing_timestamps)]
            
            if df.empty:
                logger.info("ℹ️ All data already exists (no new records)")
                return {"rows_added": 0, "symbol": symbol, "interval": interval}
            
            # Convert and save
            market_data_list = self._dataframe_to_domain(df, symbol, interval)
            count = self.repository.save(market_data_list)
            
            logger.info(
                "✅ Update complete",
                symbol=symbol,
                interval=interval,
                new_records=count
            )
            
            return {"rows_added": count, "symbol": symbol, "interval": interval}
            
        except Exception as e:
            logger.error(f"❌ Update failed: {e}")
            raise
    
    def get_data(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> List[MarketData]:
        """
        Get market data for analysis.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            
        Returns:
            List of MarketData objects
        """
        start = to_utc(start)
        end = to_utc(end)
        
        logger.debug(
            "📂 Retrieving data",
            symbol=symbol,
            interval=interval,
            start=start.isoformat(),
            end=end.isoformat()
        )
        
        data = self.repository.get_by_date_range(symbol, interval, start, end)
        
        logger.debug(f"✅ Retrieved {len(data)} records")
        
        return data
    
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
            List of MarketData objects (newest first)
        """
        logger.debug(
            "📂 Retrieving latest data",
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        data = self.repository.get_latest(symbol, interval, limit)
        
        logger.debug(f"✅ Retrieved {len(data)} records")
        
        return data
    
    def get_data_as_dataframe(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """
        Get market data as DataFrame (convenient for analysis).
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            
        Returns:
            DataFrame with OHLCV data
        """
        data = self.get_data(symbol, interval, start, end)
        
        if not data:
            return pd.DataFrame(columns=[
                "timestamp", "open", "high", "low", "close", "volume"
            ])
        
        return self._domain_to_dataframe(data)
    
    def delete_old_data(
        self,
        symbol: str,
        interval: str,
        older_than_days: int
    ) -> int:
        """
        Delete data older than specified days.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            older_than_days: Delete data older than this many days
            
        Returns:
            Number of records deleted
        """
        cutoff = datetime.now() - timedelta(days=older_than_days)
        start = datetime.now() - timedelta(days=365 * 10)  # Go back 10 years
        
        logger.info(
            f"🗑️ Deleting data older than {older_than_days} days",
            symbol=symbol,
            interval=interval,
            cutoff=cutoff.isoformat()
        )
        
        count = self.repository.delete_by_date_range(
            symbol, interval, start, cutoff
        )
        
        logger.info(f"✅ Deleted {count} records")
        
        return count
    
    def get_data_summary(
        self,
        symbol: str,
        interval: str
    ) -> dict:
        """
        Get summary of available data.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            
        Returns:
            Dictionary with summary info
        """
        dates = self.repository.get_available_dates(symbol, interval)
        
        if not dates:
            return {
                "symbol": symbol,
                "interval": interval,
                "available": False,
                "first_date": None,
                "last_date": None,
                "total_days": 0
            }
        
        first_date = min(dates)
        last_date = max(dates)
        total_days = (last_date - first_date).days
        
        return {
            "symbol": symbol,
            "interval": interval,
            "available": True,
            "first_date": first_date,
            "last_date": last_date,
            "total_days": total_days,
            "num_partitions": len(dates)
        }
    
    # ==================== Helper Methods ====================
    
    def _dataframe_to_domain(
        self,
        df: pd.DataFrame,
        symbol: str,
        interval: str
    ) -> List[MarketData]:
        """Convert DataFrame to domain objects."""
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
    
    def _domain_to_dataframe(
        self,
        data: List[MarketData]
    ) -> pd.DataFrame:
        """Convert domain objects to DataFrame."""
        records = []
        
        for md in data:
            records.append({
                "timestamp": md.timestamp,
                "open": md.open,
                "high": md.high,
                "low": md.low,
                "close": md.close,
                "volume": md.volume
            })
        
        return pd.DataFrame(records)
