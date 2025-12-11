"""
Hybrid Market Data Repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implementation combining hot (PostgreSQL) and warm (Parquet) storage.

Auto-routing Strategy:
- Recent data (< 30 days): PostgreSQL (fast reads/writes)
- Historical data (> 30 days): Parquet (efficient storage)
- Seamless queries across both storages
"""

from datetime import datetime, timedelta
from typing import List

from src.domain.interfaces.market_data_repository import IMarketDataRepository
from src.domain.models.market_data import MarketData
from src.infrastructure.repositories.parquet_repository import ParquetMarketDataRepository
from src.infrastructure.repositories.postgres_repository import PostgresMarketDataRepository
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class HybridMarketDataRepository(IMarketDataRepository):
    """
    Repository that automatically routes queries to hot or warm storage.
    
    Architecture:
    ┌─────────────────────────────────────┐
    │   HybridMarketDataRepository       │
    │  (Auto-routing & query merging)    │
    └───────────┬─────────────────────────┘
                │
        ┌───────┴───────┐
        │               │
        ▼               ▼
    ┌──────┐      ┌─────────┐
    │ Hot  │      │  Warm   │
    │ PG   │      │ Parquet │
    │30days│      │ 3 years │
    └──────┘      └─────────┘
    
    Benefits:
    - Best of both worlds (fast recent + cheap historical)
    - Transparent to application layer
    - Automatic data lifecycle management
    """
    
    HOT_STORAGE_DAYS = 30  # Last 30 days in PostgreSQL
    
    def __init__(
        self,
        postgres_repo: PostgresMarketDataRepository,
        parquet_repo: ParquetMarketDataRepository
    ):
        """
        Initialize hybrid repository.
        
        Args:
            postgres_repo: Hot storage repository
            parquet_repo: Warm storage repository
        """
        self.postgres_repo = postgres_repo
        self.parquet_repo = parquet_repo
        
        logger.info(
            f"✅ Hybrid repository initialized",
            hot_days=self.HOT_STORAGE_DAYS
        )
    
    def get_by_date_range(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> List[MarketData]:
        """
        Get market data with auto-routing.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            
        Returns:
            Combined list from hot and warm storage
        """
        cutoff = datetime.now() - timedelta(days=self.HOT_STORAGE_DAYS)
        
        # Case 1: All recent (< 30 days) - use PostgreSQL only
        if start >= cutoff:
            logger.debug(f"🔥 Query: All hot storage")
            return self.postgres_repo.get_by_date_range(symbol, interval, start, end)
        
        # Case 2: All historical (> 30 days) - use Parquet only
        if end < cutoff:
            logger.debug(f"❄️ Query: All warm storage")
            return self.parquet_repo.get_by_date_range(symbol, interval, start, end)
        
        # Case 3: Spans both - query both and merge
        logger.debug(f"🔀 Query: Hybrid (hot + warm)")
        
        # Historical part from Parquet
        historical_data = self.parquet_repo.get_by_date_range(
            symbol, interval, start, cutoff
        )
        
        # Recent part from PostgreSQL
        recent_data = self.postgres_repo.get_by_date_range(
            symbol, interval, cutoff, end
        )
        
        # Merge and sort
        combined = historical_data + recent_data
        combined.sort(key=lambda x: x.timestamp)
        
        logger.info(
            f"✅ Hybrid query complete",
            symbol=symbol,
            interval=interval,
            total_rows=len(combined),
            historical_rows=len(historical_data),
            recent_rows=len(recent_data)
        )
        
        return combined
    
    def get_latest(
        self,
        symbol: str,
        interval: str,
        limit: int = 100
    ) -> List[MarketData]:
        """
        Get latest N records (always from hot storage).
        
        Args:
            symbol: Trading pair
            interval: Time interval
            limit: Number of records
            
        Returns:
            List of latest MarketData objects
        """
        # Latest data is always in PostgreSQL
        return self.postgres_repo.get_latest(symbol, interval, limit)
    
    def save(self, data: List[MarketData]) -> int:
        """
        Save market data with auto-routing.
        
        Args:
            data: List of MarketData objects
            
        Returns:
            Number of records saved
        """
        if not data:
            return 0
        
        cutoff = datetime.now() - timedelta(days=self.HOT_STORAGE_DAYS)
        
        # Split into hot and warm
        hot_data = [d for d in data if d.timestamp >= cutoff]
        warm_data = [d for d in data if d.timestamp < cutoff]
        
        saved_count = 0
        
        # Save to appropriate storage
        if hot_data:
            count = self.postgres_repo.save(hot_data)
            saved_count += count
            logger.debug(f"💾 Saved {count} rows to hot storage")
        
        if warm_data:
            count = self.parquet_repo.save(warm_data)
            saved_count += count
            logger.debug(f"💾 Saved {count} rows to warm storage")
        
        return saved_count
    
    def exists(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> bool:
        """
        Check if data exists (checks both storages).
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            
        Returns:
            True if data exists in either storage
        """
        cutoff = datetime.now() - timedelta(days=self.HOT_STORAGE_DAYS)
        
        # Check hot storage if range overlaps
        if end >= cutoff:
            if self.postgres_repo.exists(symbol, interval, max(start, cutoff), end):
                return True
        
        # Check warm storage if range overlaps
        if start < cutoff:
            if self.parquet_repo.exists(symbol, interval, start, min(end, cutoff)):
                return True
        
        return False
    
    def delete_by_date_range(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> int:
        """
        Delete data from both storages.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            
        Returns:
            Total number of records deleted
        """
        cutoff = datetime.now() - timedelta(days=self.HOT_STORAGE_DAYS)
        
        deleted_count = 0
        
        # Delete from hot storage if range overlaps
        if end >= cutoff:
            count = self.postgres_repo.delete_by_date_range(
                symbol, interval, max(start, cutoff), end
            )
            deleted_count += count
        
        # Delete from warm storage if range overlaps
        if start < cutoff:
            count = self.parquet_repo.delete_by_date_range(
                symbol, interval, start, min(end, cutoff)
            )
            deleted_count += count
        
        return deleted_count
    
    def get_available_dates(
        self,
        symbol: str,
        interval: str
    ) -> List[datetime]:
        """
        Get available dates from both storages.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            
        Returns:
            Combined list of dates from both storages
        """
        # Get from both storages
        hot_dates = self.postgres_repo.get_available_dates(symbol, interval)
        warm_dates = self.parquet_repo.get_available_dates(symbol, interval)
        
        # Combine and sort
        all_dates = list(set(hot_dates + warm_dates))
        all_dates.sort()
        
        return all_dates
    
    def migrate_to_warm_storage(
        self,
        symbol: str,
        interval: str,
        cutoff_days: int = None
    ) -> int:
        """
        Migrate old data from hot to warm storage.
        
        This should be run periodically to keep hot storage lean.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            cutoff_days: Days to keep in hot storage (default: HOT_STORAGE_DAYS)
            
        Returns:
            Number of records migrated
        """
        if cutoff_days is None:
            cutoff_days = self.HOT_STORAGE_DAYS
        
        cutoff = datetime.now() - timedelta(days=cutoff_days)
        
        # Get old data from hot storage
        start = datetime.now() - timedelta(days=365)  # Go back 1 year
        
        old_data = self.postgres_repo.get_by_date_range(
            symbol, interval, start, cutoff
        )
        
        if not old_data:
            logger.info(f"ℹ️ No data to migrate")
            return 0
        
        # Save to warm storage
        count = self.parquet_repo.save(old_data)
        
        # Delete from hot storage
        self.postgres_repo.delete_by_date_range(
            symbol, interval, start, cutoff
        )
        
        logger.info(
            f"📦 Migrated to warm storage",
            symbol=symbol,
            interval=interval,
            rows=count
        )
        
        return count
