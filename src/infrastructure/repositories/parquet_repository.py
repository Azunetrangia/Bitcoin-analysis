"""
Parquet Market Data Repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implementation of IMarketDataRepository using Parquet storage.

This is the warm storage repository (3+ years of historical data).
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.domain.interfaces.market_data_repository import IMarketDataRepository
from src.domain.models.market_data import MarketData
from src.infrastructure.storage.parquet_manager import ParquetManager
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ParquetMarketDataRepository(IMarketDataRepository):
    """
    Repository implementation using Parquet files for warm storage.
    
    Storage Strategy:
    - Partitioned by symbol/interval/year-month
    - Columnar format (10x compression)
    - Fast queries with DuckDB
    
    Use Cases:
    - Historical backtesting (3+ years)
    - Training machine learning models
    - Long-term trend analysis
    """
    
    def __init__(self, base_path: Path | str = "data/processed"):
        """
        Initialize repository.
        
        Args:
            base_path: Base directory for Parquet files
        """
        self.manager = ParquetManager(base_path=base_path)
        logger.info(f"✅ Parquet repository initialized", base_path=base_path)
    
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
        # Read from Parquet
        df = self.manager.read_date_range(
            symbol=symbol,
            interval=interval,
            start=start,
            end=end
        )
        
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
            f"📂 Retrieved from Parquet",
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
        # Get available partitions
        partitions = self.manager.list_partitions(symbol, interval)
        
        if not partitions:
            return []
        
        # Start from latest partition
        partitions = sorted(partitions, reverse=True)
        
        all_data = []
        
        for year, month in partitions:
            df = self.manager.read_partition(symbol, interval, year, month)
            
            # Add to front (newest first)
            all_data.insert(0, df)
            
            # Check if we have enough
            total_rows = sum(len(d) for d in all_data)
            if total_rows >= limit:
                break
        
        if not all_data:
            return []
        
        # Concatenate and take latest N
        df_all = pd.concat(all_data, ignore_index=True)
        df_all = df_all.sort_values("timestamp", ascending=False).head(limit)
        
        # Convert to domain objects
        market_data_list = []
        
        for _, row in df_all.iterrows():
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
                "timestamp": md.timestamp,
                "open": md.open,
                "high": md.high,
                "low": md.low,
                "close": md.close,
                "volume": md.volume
            })
        
        df = pd.DataFrame(records)
        
        # Group by year-month
        df["year"] = df["timestamp"].dt.year
        df["month"] = df["timestamp"].dt.month
        
        symbol = data[0].symbol
        interval = data[0].interval
        
        saved_count = 0
        
        for (year, month), group_df in df.groupby(["year", "month"]):
            # Drop grouping columns
            group_df = group_df.drop(columns=["year", "month"])
            
            # Check if partition exists
            try:
                existing_df = self.manager.read_partition(symbol, interval, year, month)
                
                # Merge with existing (avoid duplicates)
                combined_df = pd.concat([existing_df, group_df])
                combined_df = combined_df.drop_duplicates(subset=["timestamp"])
                combined_df = combined_df.sort_values("timestamp")
                
                group_df = combined_df
                
            except Exception:
                # Partition doesn't exist, use new data
                pass
            
            # Write partition
            self.manager.write_partition(
                group_df,
                symbol=symbol,
                interval=interval,
                year=year,
                month=month
            )
            
            saved_count += len(group_df)
        
        logger.info(
            f"💾 Saved to Parquet",
            symbol=symbol,
            interval=interval,
            rows=saved_count
        )
        
        return saved_count
    
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
        try:
            df = self.manager.read_date_range(symbol, interval, start, end)
            return len(df) > 0
        except Exception:
            return False
    
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
        # Get partitions in range
        current = start.replace(day=1)
        deleted_count = 0
        
        while current <= end:
            year, month = current.year, current.month
            
            try:
                df = self.manager.read_partition(symbol, interval, year, month)
                
                # Filter out data in range
                df_filtered = df[
                    (df["timestamp"] < start) | (df["timestamp"] > end)
                ]
                
                if len(df_filtered) == 0:
                    # Delete entire partition
                    self.manager.delete_partition(symbol, interval, year, month)
                    deleted_count += len(df)
                else:
                    # Overwrite with filtered data
                    deleted = len(df) - len(df_filtered)
                    
                    if deleted > 0:
                        self.manager.write_partition(
                            df_filtered,
                            symbol=symbol,
                            interval=interval,
                            year=year,
                            month=month
                        )
                        deleted_count += deleted
                
            except Exception:
                # Partition doesn't exist
                pass
            
            # Next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return deleted_count
    
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
            List of datetime objects (first timestamp of each partition)
        """
        partitions = self.manager.list_partitions(symbol, interval)
        
        dates = []
        
        for year, month in partitions:
            # Get first date of partition
            df = self.manager.read_partition(
                symbol, interval, year, month,
                columns=["timestamp"]
            )
            
            if len(df) > 0:
                dates.append(df["timestamp"].min())
        
        return sorted(dates)
