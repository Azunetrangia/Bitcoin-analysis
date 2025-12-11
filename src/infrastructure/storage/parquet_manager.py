"""
Parquet Storage Manager
~~~~~~~~~~~~~~~~~~~~~~~

Infrastructure component for reading/writing Parquet files with partitioning.

Features:
- Partitioned storage: symbol/interval/year-month/data.parquet
- Efficient columnar storage (10x smaller than CSV)
- Fast queries (only read needed columns)
- Schema enforcement

Partition Example:
  data/processed/
    btcusdt/
      1h/
        2024-01/data.parquet
        2024-02/data.parquet
        2024-03/data.parquet
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from src.shared.exceptions.custom_exceptions import StorageError, DataParsingError
from src.shared.utils.logging_utils import get_logger
from src.shared.utils.datetime_utils import to_utc

logger = get_logger(__name__)


class ParquetManager:
    """
    Manager for Parquet file storage with partitioning strategy.
    
    Partitioning Strategy:
    - Level 1: Symbol (btcusdt, ethusdt)
    - Level 2: Interval (1h, 4h, 1d)
    - Level 3: Year-Month (2024-01, 2024-02)
    
    Benefits:
    - Efficient pruning (only read needed partitions)
    - Organized structure
    - Easy to manage (delete old data by partition)
    """
    
    # Parquet schema for market data
    SCHEMA = pa.schema([
        ("timestamp", pa.timestamp("ms", tz="UTC")),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.float64()),
    ])
    
    def __init__(self, base_path: Path | str = "data/processed"):
        """
        Initialize Parquet Manager.
        
        Args:
            base_path: Base directory for Parquet files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def get_partition_path(
        self,
        symbol: str,
        interval: str,
        year: int,
        month: int
    ) -> Path:
        """
        Get path for specific partition.
        
        Args:
            symbol: Trading pair (lowercase)
            interval: Time interval
            year: Year
            month: Month (1-12)
            
        Returns:
            Path to partition directory
            
        Example:
            >>> manager.get_partition_path("btcusdt", "1h", 2024, 1)
            Path('data/processed/btcusdt/1h/2024-01')
        """
        symbol_lower = symbol.lower()
        year_month = f"{year}-{month:02d}"
        
        return self.base_path / symbol_lower / interval / year_month
    
    def write_partition(
        self,
        df: pd.DataFrame,
        symbol: str,
        interval: str,
        year: int,
        month: int,
        compression: str = "snappy"
    ) -> Path:
        """
        Write DataFrame to Parquet partition.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Trading pair
            interval: Time interval
            year: Year
            month: Month
            compression: Compression algorithm ('snappy', 'gzip', 'brotli')
            
        Returns:
            Path to written file
            
        Raises:
            StorageError: If write fails
        """
        try:
            partition_path = self.get_partition_path(symbol, interval, year, month)
            partition_path.mkdir(parents=True, exist_ok=True)
            
            file_path = partition_path / "data.parquet"
            
            # Ensure timestamp is datetime
            if "timestamp" in df.columns:
                df = df.copy()
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            
            # Write Parquet
            table = pa.Table.from_pandas(df, schema=self.SCHEMA)
            
            pq.write_table(
                table,
                file_path,
                compression=compression,
                use_dictionary=True,  # Dictionary encoding for strings
                write_statistics=True,  # Write min/max stats for pruning
            )
            
            file_size = file_path.stat().st_size / 1024 / 1024  # MB
            
            logger.info(
                f"💾 Wrote Parquet partition",
                path=str(file_path),
                rows=len(df),
                size_mb=f"{file_size:.2f}"
            )
            
            return file_path
            
        except Exception as e:
            raise StorageError(
                f"Failed to write Parquet: {str(e)}",
                details={
                    "symbol": symbol,
                    "interval": interval,
                    "year_month": f"{year}-{month:02d}"
                }
            )
    
    def read_partition(
        self,
        symbol: str,
        interval: str,
        year: int,
        month: int,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Read Parquet partition.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            year: Year
            month: Month
            columns: Specific columns to read (None = all)
            
        Returns:
            DataFrame with data
            
        Raises:
            StorageError: If read fails or file not found
        """
        try:
            partition_path = self.get_partition_path(symbol, interval, year, month)
            file_path = partition_path / "data.parquet"
            
            if not file_path.exists():
                raise StorageError(
                    f"Partition not found: {file_path}",
                    details={"symbol": symbol, "interval": interval, "year_month": f"{year}-{month:02d}"}
                )
            
            # Read Parquet
            df = pd.read_parquet(file_path, columns=columns)
            
            logger.debug(
                f"📂 Read Parquet partition",
                path=str(file_path),
                rows=len(df),
                columns=len(df.columns)
            )
            
            return df
            
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(
                f"Failed to read Parquet: {str(e)}",
                details={"symbol": symbol, "interval": interval}
            )
    
    def read_date_range(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Read data across multiple partitions for date range.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            columns: Specific columns to read
            
        Returns:
            Concatenated DataFrame
            
        Example:
            >>> manager = ParquetManager()
            >>> df = manager.read_date_range(
            ...     "btcusdt", "1h",
            ...     datetime(2024, 1, 1),
            ...     datetime(2024, 3, 31)
            ... )
        """
        start = to_utc(start)
        end = to_utc(end)
        
        # Generate list of partitions to read
        partitions = []
        current = start.replace(day=1)
        
        while current <= end:
            partitions.append((current.year, current.month))
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        logger.info(
            f"📂 Reading {len(partitions)} partitions",
            symbol=symbol,
            interval=interval,
            partitions=len(partitions)
        )
        
        # Read each partition
        dfs = []
        
        for year, month in partitions:
            try:
                df = self.read_partition(symbol, interval, year, month, columns)
                dfs.append(df)
            except StorageError as e:
                logger.warning(f"⚠️ Partition not found: {year}-{month:02d}")
                continue
        
        if not dfs:
            raise StorageError(
                f"No data found for date range",
                details={
                    "symbol": symbol,
                    "interval": interval,
                    "start": start.isoformat(),
                    "end": end.isoformat()
                }
            )
        
        # Concatenate
        df_all = pd.concat(dfs, ignore_index=True)
        
        # Filter to exact date range
        df_all = df_all[
            (df_all["timestamp"] >= start) & (df_all["timestamp"] <= end)
        ].copy()
        
        # Sort by timestamp
        df_all = df_all.sort_values("timestamp").reset_index(drop=True)
        
        logger.info(
            f"✅ Read {len(df_all)} rows from {len(dfs)} partitions",
            symbol=symbol,
            interval=interval
        )
        
        return df_all
    
    def list_partitions(
        self,
        symbol: str,
        interval: str
    ) -> List[tuple[int, int]]:
        """
        List available partitions for symbol/interval.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            
        Returns:
            List of (year, month) tuples
            
        Example:
            >>> partitions = manager.list_partitions("btcusdt", "1h")
            >>> print(partitions)
            [(2024, 1), (2024, 2), (2024, 3)]
        """
        symbol_lower = symbol.lower()
        interval_path = self.base_path / symbol_lower / interval
        
        if not interval_path.exists():
            return []
        
        partitions = []
        
        for partition_dir in interval_path.iterdir():
            if partition_dir.is_dir():
                try:
                    # Parse year-month from directory name
                    year, month = partition_dir.name.split("-")
                    partitions.append((int(year), int(month)))
                except ValueError:
                    continue
        
        return sorted(partitions)
    
    def delete_partition(
        self,
        symbol: str,
        interval: str,
        year: int,
        month: int
    ) -> bool:
        """
        Delete a partition.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            year: Year
            month: Month
            
        Returns:
            True if deleted, False if not found
        """
        partition_path = self.get_partition_path(symbol, interval, year, month)
        
        if partition_path.exists():
            import shutil
            shutil.rmtree(partition_path)
            
            logger.info(
                f"🗑️ Deleted partition",
                symbol=symbol,
                interval=interval,
                year_month=f"{year}-{month:02d}"
            )
            return True
        
        return False
    
    def get_partition_stats(
        self,
        symbol: str,
        interval: str,
        year: int,
        month: int
    ) -> dict:
        """
        Get statistics about a partition.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            year: Year
            month: Month
            
        Returns:
            Dictionary with stats (rows, size_mb, columns, min_date, max_date)
        """
        partition_path = self.get_partition_path(symbol, interval, year, month)
        file_path = partition_path / "data.parquet"
        
        if not file_path.exists():
            raise StorageError(f"Partition not found: {file_path}")
        
        # Read metadata only (fast)
        parquet_file = pq.ParquetFile(file_path)
        
        # Get row count
        num_rows = parquet_file.metadata.num_rows
        
        # Get file size
        file_size_mb = file_path.stat().st_size / 1024 / 1024
        
        # Get date range from statistics
        first_row_group = parquet_file.metadata.row_group(0)
        timestamp_col = first_row_group.column(0)  # Assuming timestamp is first column
        
        stats = {
            "rows": num_rows,
            "size_mb": round(file_size_mb, 2),
            "columns": len(parquet_file.schema),
            "row_groups": parquet_file.metadata.num_row_groups,
        }
        
        return stats
