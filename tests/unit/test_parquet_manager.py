"""
Tests for Parquet Manager
~~~~~~~~~~~~~~~~~~~~~~~~~

Test partitioned Parquet storage with:
- Write/read operations
- Date range queries
- Partition management
- Statistics
"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from src.infrastructure.storage.parquet_manager import ParquetManager
from src.shared.exceptions.custom_exceptions import StorageError


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_data():
    """Generate sample OHLCV data."""
    dates = pd.date_range("2024-01-01", periods=100, freq="1h", tz="UTC")
    
    return pd.DataFrame({
        "timestamp": dates,
        "open": 45000.0 + pd.Series(range(100)),
        "high": 45100.0 + pd.Series(range(100)),
        "low": 44900.0 + pd.Series(range(100)),
        "close": 45000.0 + pd.Series(range(100)),
        "volume": 1000.0 + pd.Series(range(100)) * 10,
    })


@pytest.fixture
def parquet_manager(temp_storage):
    """Create ParquetManager with temp storage."""
    return ParquetManager(base_path=temp_storage)


class TestParquetManager:
    """Test ParquetManager functionality."""
    
    def test_initialization(self, parquet_manager, temp_storage):
        """Test manager initialization creates base directory."""
        assert parquet_manager.base_path == temp_storage
        assert temp_storage.exists()
    
    def test_get_partition_path(self, parquet_manager, temp_storage):
        """Test partition path generation."""
        path = parquet_manager.get_partition_path("btcusdt", "1h", 2024, 1)
        
        expected = temp_storage / "btcusdt" / "1h" / "2024-01"
        assert path == expected
    
    def test_write_partition(self, parquet_manager, sample_data):
        """Test writing data to partition."""
        file_path = parquet_manager.write_partition(
            sample_data,
            symbol="btcusdt",
            interval="1h",
            year=2024,
            month=1
        )
        
        assert file_path.exists()
        assert file_path.name == "data.parquet"
    
    def test_read_partition(self, parquet_manager, sample_data):
        """Test reading data from partition."""
        # Write first
        parquet_manager.write_partition(
            sample_data, "btcusdt", "1h", 2024, 1
        )
        
        # Read back
        df = parquet_manager.read_partition("btcusdt", "1h", 2024, 1)
        
        assert len(df) == len(sample_data)
        assert list(df.columns) == list(sample_data.columns)
        assert df["close"].iloc[0] == pytest.approx(45000.0)
    
    def test_read_specific_columns(self, parquet_manager, sample_data):
        """Test reading only specific columns."""
        parquet_manager.write_partition(
            sample_data, "btcusdt", "1h", 2024, 1
        )
        
        df = parquet_manager.read_partition(
            "btcusdt", "1h", 2024, 1,
            columns=["timestamp", "close"]
        )
        
        assert list(df.columns) == ["timestamp", "close"]
        assert len(df) == len(sample_data)
    
    def test_read_nonexistent_partition(self, parquet_manager):
        """Test reading non-existent partition raises error."""
        with pytest.raises(StorageError, match="Partition not found"):
            parquet_manager.read_partition("btcusdt", "1h", 2099, 12)
    
    def test_write_multiple_partitions(self, parquet_manager):
        """Test writing multiple partitions."""
        # January data
        jan_dates = pd.date_range("2024-01-01", periods=50, freq="1h", tz="UTC")
        jan_data = pd.DataFrame({
            "timestamp": jan_dates,
            "open": 45000.0,
            "high": 45100.0,
            "low": 44900.0,
            "close": 45000.0,
            "volume": 1000.0,
        })
        
        # February data
        feb_dates = pd.date_range("2024-02-01", periods=50, freq="1h", tz="UTC")
        feb_data = pd.DataFrame({
            "timestamp": feb_dates,
            "open": 46000.0,
            "high": 46100.0,
            "low": 45900.0,
            "close": 46000.0,
            "volume": 1100.0,
        })
        
        # Write both
        parquet_manager.write_partition(jan_data, "btcusdt", "1h", 2024, 1)
        parquet_manager.write_partition(feb_data, "btcusdt", "1h", 2024, 2)
        
        # Read both
        jan_df = parquet_manager.read_partition("btcusdt", "1h", 2024, 1)
        feb_df = parquet_manager.read_partition("btcusdt", "1h", 2024, 2)
        
        assert len(jan_df) == 50
        assert len(feb_df) == 50
        assert jan_df["close"].iloc[0] == pytest.approx(45000.0)
        assert feb_df["close"].iloc[0] == pytest.approx(46000.0)
    
    def test_read_date_range(self, parquet_manager):
        """Test reading data across multiple partitions."""
        # Create 3 months of data
        for month in range(1, 4):
            dates = pd.date_range(
                f"2024-{month:02d}-01",
                periods=100,
                freq="1h",
                tz="UTC"
            )
            
            data = pd.DataFrame({
                "timestamp": dates,
                "open": 45000.0 + month * 1000,
                "high": 45100.0 + month * 1000,
                "low": 44900.0 + month * 1000,
                "close": 45000.0 + month * 1000,
                "volume": 1000.0,
            })
            
            parquet_manager.write_partition(data, "btcusdt", "1h", 2024, month)
        
        # Read across all 3 months
        df = parquet_manager.read_date_range(
            "btcusdt",
            "1h",
            datetime(2024, 1, 1, tzinfo=pd.Timestamp.now(tz="UTC").tz),
            datetime(2024, 3, 31, tzinfo=pd.Timestamp.now(tz="UTC").tz)
        )
        
        assert len(df) == 300  # 100 per month
        assert df["timestamp"].is_monotonic_increasing
    
    def test_read_date_range_partial_months(self, parquet_manager):
        """Test reading date range filters correctly."""
        # Create January data
        jan_dates = pd.date_range("2024-01-01", periods=744, freq="1h", tz="UTC")
        jan_data = pd.DataFrame({
            "timestamp": jan_dates,
            "open": 45000.0,
            "high": 45100.0,
            "low": 44900.0,
            "close": 45000.0,
            "volume": 1000.0,
        })
        
        parquet_manager.write_partition(jan_data, "btcusdt", "1h", 2024, 1)
        
        # Read only Jan 15-20
        df = parquet_manager.read_date_range(
            "btcusdt",
            "1h",
            datetime(2024, 1, 15, tzinfo=pd.Timestamp.now(tz="UTC").tz),
            datetime(2024, 1, 20, tzinfo=pd.Timestamp.now(tz="UTC").tz)
        )
        
        assert df["timestamp"].min() >= pd.Timestamp("2024-01-15", tz="UTC")
        assert df["timestamp"].max() <= pd.Timestamp("2024-01-20", tz="UTC")
    
    def test_list_partitions(self, parquet_manager, sample_data):
        """Test listing available partitions."""
        # Write 3 partitions
        for month in range(1, 4):
            parquet_manager.write_partition(
                sample_data, "btcusdt", "1h", 2024, month
            )
        
        partitions = parquet_manager.list_partitions("btcusdt", "1h")
        
        assert len(partitions) == 3
        assert (2024, 1) in partitions
        assert (2024, 2) in partitions
        assert (2024, 3) in partitions
    
    def test_list_partitions_empty(self, parquet_manager):
        """Test listing partitions when none exist."""
        partitions = parquet_manager.list_partitions("btcusdt", "1h")
        assert partitions == []
    
    def test_delete_partition(self, parquet_manager, sample_data):
        """Test deleting a partition."""
        parquet_manager.write_partition(
            sample_data, "btcusdt", "1h", 2024, 1
        )
        
        # Verify exists
        df = parquet_manager.read_partition("btcusdt", "1h", 2024, 1)
        assert len(df) > 0
        
        # Delete
        deleted = parquet_manager.delete_partition("btcusdt", "1h", 2024, 1)
        assert deleted is True
        
        # Verify gone
        with pytest.raises(StorageError):
            parquet_manager.read_partition("btcusdt", "1h", 2024, 1)
    
    def test_delete_nonexistent_partition(self, parquet_manager):
        """Test deleting non-existent partition returns False."""
        deleted = parquet_manager.delete_partition("btcusdt", "1h", 2099, 12)
        assert deleted is False
    
    def test_compression(self, parquet_manager, sample_data):
        """Test different compression algorithms."""
        # Write with snappy
        path_snappy = parquet_manager.write_partition(
            sample_data, "btcusdt", "1h", 2024, 1, compression="snappy"
        )
        
        # Write with gzip
        path_gzip = parquet_manager.write_partition(
            sample_data, "btcusdt", "4h", 2024, 1, compression="gzip"
        )
        
        # Both should work
        df_snappy = parquet_manager.read_partition("btcusdt", "1h", 2024, 1)
        df_gzip = parquet_manager.read_partition("btcusdt", "4h", 2024, 1)
        
        assert len(df_snappy) == len(sample_data)
        assert len(df_gzip) == len(sample_data)
    
    def test_get_partition_stats(self, parquet_manager, sample_data):
        """Test getting partition statistics."""
        parquet_manager.write_partition(
            sample_data, "btcusdt", "1h", 2024, 1
        )
        
        stats = parquet_manager.get_partition_stats("btcusdt", "1h", 2024, 1)
        
        assert stats["rows"] == len(sample_data)
        assert stats["size_mb"] > 0
        assert stats["columns"] == 6  # timestamp + OHLCV
