"""
Tests for DuckDB Query Engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Test efficient OLAP queries on Parquet files.
"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime

from src.infrastructure.storage.parquet_manager import ParquetManager
from src.infrastructure.storage.duckdb_query_engine import DuckDBQueryEngine


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def setup_partitions(temp_storage):
    """Set up multiple partitions with test data."""
    manager = ParquetManager(base_path=temp_storage)
    
    # Create 3 months of hourly data
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
            "volume": 1000.0 + month * 100,
        })
        
        manager.write_partition(data, "btcusdt", "1h", 2024, month)
    
    return temp_storage


class TestDuckDBQueryEngine:
    """Test DuckDB Query Engine functionality."""
    
    def test_initialization(self):
        """Test query engine initialization."""
        engine = DuckDBQueryEngine()
        assert engine.conn is not None
        engine.close()
    
    def test_simple_query(self, setup_partitions):
        """Test basic SQL query."""
        engine = DuckDBQueryEngine()
        
        file_pattern = str(setup_partitions / "btcusdt/1h/2024-01/data.parquet")
        
        df = engine.query(f"SELECT * FROM '{file_pattern}' LIMIT 10")
        
        assert len(df) == 10
        assert "timestamp" in df.columns
        assert "close" in df.columns
        
        engine.close()
    
    def test_query_parquet_files_with_glob(self, setup_partitions):
        """Test querying multiple partitions with glob pattern."""
        engine = DuckDBQueryEngine()
        
        file_pattern = str(setup_partitions / "btcusdt/1h/**/data.parquet")
        
        df = engine.query_parquet_files(file_pattern)
        
        assert len(df) == 300  # 100 per month × 3 months
        assert df["timestamp"].is_monotonic_increasing
        
        engine.close()
    
    def test_query_with_date_filter(self, setup_partitions):
        """Test date range filtering."""
        engine = DuckDBQueryEngine()
        
        file_pattern = str(setup_partitions / "btcusdt/1h/**/data.parquet")
        
        df = engine.query_parquet_files(
            file_pattern,
            start=datetime(2024, 2, 1),
            end=datetime(2024, 2, 28)
        )
        
        # Should only get February data
        assert len(df) == 100
        assert all(df["timestamp"] >= pd.Timestamp("2024-02-01", tz="UTC"))
        assert all(df["timestamp"] < pd.Timestamp("2024-03-01", tz="UTC"))
        
        engine.close()
    
    def test_query_specific_columns(self, setup_partitions):
        """Test column projection (only read needed columns)."""
        engine = DuckDBQueryEngine()
        
        file_pattern = str(setup_partitions / "btcusdt/1h/2024-01/data.parquet")
        
        df = engine.query_parquet_files(
            file_pattern,
            columns=["timestamp", "close"]
        )
        
        assert list(df.columns) == ["timestamp", "close"]
        assert len(df) == 100
        
        engine.close()
    
    def test_query_with_custom_filter(self, setup_partitions):
        """Test custom SQL WHERE conditions."""
        engine = DuckDBQueryEngine()
        
        file_pattern = str(setup_partitions / "btcusdt/1h/2024-01/data.parquet")
        
        df = engine.query_parquet_files(
            file_pattern,
            filters="close > 45050"
        )
        
        assert all(df["close"] > 45050)
        
        engine.close()
    
    def test_aggregation(self, setup_partitions):
        """Test aggregation queries."""
        engine = DuckDBQueryEngine()
        
        file_pattern = str(setup_partitions / "btcusdt/1h/**/data.parquet")
        
        # Daily aggregation
        df = engine.aggregate(
            file_pattern,
            groupby=["DATE_TRUNC('day', timestamp) as day"],
            aggregations={
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            }
        )
        
        # Should have fewer rows than hourly
        assert len(df) < 300
        assert "day" in df.columns
        
        engine.close()
    
    def test_get_stats(self, setup_partitions):
        """Test statistics calculation."""
        engine = DuckDBQueryEngine()
        
        file_pattern = str(setup_partitions / "btcusdt/1h/**/data.parquet")
        
        stats = engine.get_stats(file_pattern)
        
        assert stats["row_count"] == 300
        assert "min_date" in stats
        assert "max_date" in stats
        assert "avg_price" in stats
        
        engine.close()
    
    def test_context_manager(self, setup_partitions):
        """Test using query engine as context manager."""
        with DuckDBQueryEngine() as engine:
            file_pattern = str(setup_partitions / "btcusdt/1h/2024-01/data.parquet")
            df = engine.query(f"SELECT COUNT(*) as count FROM '{file_pattern}'")
            
            assert df["count"].iloc[0] == 100
        
        # Connection should be closed after context
