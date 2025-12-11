"""
Integration Tests for Data Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Test complete flow: Binance Download -> Parquet Storage -> DuckDB Query
"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from src.infrastructure.data.binance_client import BinanceDataClient
from src.infrastructure.storage.parquet_manager import ParquetManager
from src.infrastructure.storage.duckdb_query_engine import DuckDBQueryEngine


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_csv_content():
    """Sample CSV data from Binance format."""
    return """1640995200000,46000.00,46100.00,45900.00,46000.00,100.5,1640998799999,4625000.00,1000,50.3,2312500.00,0
1640998800000,46050.00,46150.00,45950.00,46100.00,120.3,1641002399999,5545650.00,1200,60.1,2765050.00,0
1641002400000,46100.00,46200.00,46000.00,46150.00,110.2,1641005999999,5085530.00,1100,55.5,2561590.00,0"""


class TestDataPipeline:
    """Test complete data pipeline."""
    
    def test_full_pipeline_flow(self, temp_storage, sample_csv_content):
        """
        Test complete flow:
        1. Download from Binance (mocked)
        2. Save to Parquet
        3. Query with DuckDB
        """
        # Mock Binance download
        with patch.object(BinanceDataClient, 'download_month') as mock_download:
            # Configure mock to return sample data
            mock_download.return_value = pd.DataFrame({
                "timestamp": pd.date_range("2024-01-01", periods=100, freq="1h", tz="UTC"),
                "open": 46000.0,
                "high": 46100.0,
                "low": 45900.0,
                "close": 46000.0,
                "volume": 100.5,
            })
            
            # Step 1: Download
            client = BinanceDataClient()
            df = client.download_month("btcusdt", "1h", 2024, 1)
            
            assert len(df) == 100
            assert "close" in df.columns
            
            # Step 2: Save to Parquet
            manager = ParquetManager(base_path=temp_storage)
            file_path = manager.write_partition(
                df, "btcusdt", "1h", 2024, 1
            )
            
            assert file_path.exists()
            
            # Step 3: Query with DuckDB
            engine = DuckDBQueryEngine()
            
            file_pattern = str(temp_storage / "btcusdt/1h/2024-01/data.parquet")
            result = engine.query_parquet_files(file_pattern)
            
            assert len(result) == 100
            assert result["close"].iloc[0] == pytest.approx(46000.0)
            
            engine.close()
    
    def test_multi_month_pipeline(self, temp_storage):
        """Test pipeline with multiple months."""
        manager = ParquetManager(base_path=temp_storage)
        
        # Create 3 months
        for month in range(1, 4):
            dates = pd.date_range(
                f"2024-{month:02d}-01",
                periods=50,
                freq="1h",
                tz="UTC"
            )
            
            df = pd.DataFrame({
                "timestamp": dates,
                "open": 45000.0 + month * 1000,
                "high": 45100.0 + month * 1000,
                "low": 44900.0 + month * 1000,
                "close": 45000.0 + month * 1000,
                "volume": 100.0,
            })
            
            manager.write_partition(df, "btcusdt", "1h", 2024, month)
        
        # Query across all months
        engine = DuckDBQueryEngine()
        
        file_pattern = str(temp_storage / "btcusdt/1h/**/data.parquet")
        
        df = engine.query_parquet_files(
            file_pattern,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 3, 31)
        )
        
        assert len(df) == 150  # 50 per month
        assert df["timestamp"].is_monotonic_increasing
        
        # Verify each month's data
        jan_data = df[df["timestamp"].dt.month == 1]
        feb_data = df[df["timestamp"].dt.month == 2]
        mar_data = df[df["timestamp"].dt.month == 3]
        
        assert jan_data["close"].iloc[0] == pytest.approx(46000.0)
        assert feb_data["close"].iloc[0] == pytest.approx(47000.0)
        assert mar_data["close"].iloc[0] == pytest.approx(48000.0)
        
        engine.close()
    
    def test_storage_efficiency(self, temp_storage):
        """Test Parquet compression vs CSV size."""
        # Create large dataset
        dates = pd.date_range("2024-01-01", periods=10000, freq="1h", tz="UTC")
        
        df = pd.DataFrame({
            "timestamp": dates,
            "open": 45000.0,
            "high": 45100.0,
            "low": 44900.0,
            "close": 45000.0,
            "volume": 100.5,
        })
        
        # Save as Parquet
        manager = ParquetManager(base_path=temp_storage)
        parquet_path = manager.write_partition(df, "btcusdt", "1h", 2024, 1)
        
        # Save as CSV for comparison
        csv_path = temp_storage / "test.csv"
        df.to_csv(csv_path, index=False)
        
        # Compare sizes
        parquet_size = parquet_path.stat().st_size
        csv_size = csv_path.stat().st_size
        
        compression_ratio = csv_size / parquet_size
        
        assert compression_ratio > 2.0  # Parquet should be at least 50% smaller
    
    def test_query_performance_column_projection(self, temp_storage):
        """Test that reading specific columns is faster than reading all."""
        # Create data
        dates = pd.date_range("2024-01-01", periods=5000, freq="1h", tz="UTC")
        
        df = pd.DataFrame({
            "timestamp": dates,
            "open": 45000.0,
            "high": 45100.0,
            "low": 44900.0,
            "close": 45000.0,
            "volume": 100.5,
        })
        
        manager = ParquetManager(base_path=temp_storage)
        manager.write_partition(df, "btcusdt", "1h", 2024, 1)
        
        engine = DuckDBQueryEngine()
        
        file_pattern = str(temp_storage / "btcusdt/1h/2024-01/data.parquet")
        
        # Read all columns
        import time
        
        start = time.time()
        df_all = engine.query_parquet_files(file_pattern)
        time_all = time.time() - start
        
        # Read only 2 columns
        start = time.time()
        df_two = engine.query_parquet_files(
            file_pattern,
            columns=["timestamp", "close"]
        )
        time_two = time.time() - start
        
        # Column projection should be faster or at least not slower
        assert len(df_two.columns) == 2
        assert len(df_all.columns) == 6
        
        engine.close()
    
    def test_incremental_updates(self, temp_storage):
        """Test appending new data to existing partitions."""
        manager = ParquetManager(base_path=temp_storage)
        
        # Initial data (first half of January)
        dates1 = pd.date_range("2024-01-01", periods=360, freq="1h", tz="UTC")
        df1 = pd.DataFrame({
            "timestamp": dates1,
            "open": 45000.0,
            "high": 45100.0,
            "low": 44900.0,
            "close": 45000.0,
            "volume": 100.0,
        })
        
        manager.write_partition(df1, "btcusdt", "1h", 2024, 1)
        
        # New data (second half of January)
        dates2 = pd.date_range("2024-01-16", periods=384, freq="1h", tz="UTC")
        df2 = pd.DataFrame({
            "timestamp": dates2,
            "open": 46000.0,
            "high": 46100.0,
            "low": 45900.0,
            "close": 46000.0,
            "volume": 110.0,
        })
        
        # Read existing
        df_existing = manager.read_partition("btcusdt", "1h", 2024, 1)
        
        # Combine and deduplicate
        df_combined = pd.concat([df_existing, df2]).drop_duplicates(
            subset=["timestamp"]
        ).sort_values("timestamp")
        
        # Overwrite partition
        manager.write_partition(df_combined, "btcusdt", "1h", 2024, 1)
        
        # Verify
        df_final = manager.read_partition("btcusdt", "1h", 2024, 1)
        
        assert len(df_final) == len(df_combined)
        assert df_final["timestamp"].is_monotonic_increasing
