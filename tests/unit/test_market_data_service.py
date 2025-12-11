"""
Tests for Market Data Service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Test application service operations.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.application.services.market_data_service import MarketDataService
from src.domain.models.market_data import MarketData
from src.shared.exceptions.custom_exceptions import DataDownloadError


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    repo = Mock()
    repo.exists.return_value = False
    repo.save.return_value = 100
    repo.get_by_date_range.return_value = []
    repo.get_latest.return_value = []
    repo.get_available_dates.return_value = []
    return repo


@pytest.fixture
def mock_binance_client():
    """Create mock Binance client."""
    client = Mock()
    
    # Create sample data
    dates = pd.date_range("2024-01-01", periods=100, freq="1h", tz="UTC")
    client.download_date_range.return_value = pd.DataFrame({
        "timestamp": dates,
        "open": 45000.0,
        "high": 45100.0,
        "low": 44900.0,
        "close": 45000.0,
        "volume": 100.5
    })
    
    return client


@pytest.fixture
def service(mock_repository, mock_binance_client):
    """Create market data service with mocks."""
    return MarketDataService(
        repository=mock_repository,
        binance_client=mock_binance_client
    )


class TestMarketDataService:
    """Test MarketDataService functionality."""
    
    def test_initialization(self, service):
        """Test service initialization."""
        assert service.repository is not None
        assert service.binance_client is not None
    
    def test_download_historical_data_success(self, service, mock_repository, mock_binance_client):
        """Test successful historical download."""
        count = service.download_historical_data(
            symbol="btcusdt",
            interval="1h",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31)
        )
        
        assert count == 100
        mock_binance_client.download_date_range.assert_called_once()
        mock_repository.save.assert_called_once()
    
    def test_download_skips_existing_data(self, service, mock_repository):
        """Test that download skips when data exists."""
        mock_repository.exists.return_value = True
        
        count = service.download_historical_data(
            symbol="btcusdt",
            interval="1h",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31)
        )
        
        assert count == 0
        mock_repository.save.assert_not_called()
    
    def test_download_force_redownload(self, service, mock_repository):
        """Test force re-download even when data exists."""
        mock_repository.exists.return_value = True
        
        count = service.download_historical_data(
            symbol="btcusdt",
            interval="1h",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
            force=True
        )
        
        assert count == 100
        mock_repository.save.assert_called_once()
    
    def test_download_handles_empty_data(self, service, mock_binance_client):
        """Test handling of empty download."""
        mock_binance_client.download_date_range.return_value = pd.DataFrame()
        
        count = service.download_historical_data(
            symbol="btcusdt",
            interval="1h",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31)
        )
        
        assert count == 0
    
    def test_download_handles_error(self, service, mock_binance_client):
        """Test error handling during download."""
        mock_binance_client.download_date_range.side_effect = DataDownloadError("Test error")
        
        with pytest.raises(DataDownloadError):
            service.download_historical_data(
                symbol="btcusdt",
                interval="1h",
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 31)
            )
    
    def test_update_latest_data(self, service, mock_repository, mock_binance_client):
        """Test incremental update."""
        # Mock existing data
        mock_repository.get_by_date_range.return_value = []
        
        result = service.update_latest_data(
            symbol="btcusdt",
            interval="1h",
            lookback_hours=24
        )
        
        assert result["rows_added"] == 100
        assert result["symbol"] == "btcusdt"
        assert result["interval"] == "1h"
        mock_binance_client.download_date_range.assert_called_once()
    
    def test_update_filters_existing_data(self, service, mock_repository, mock_binance_client):
        """Test that update filters out existing timestamps."""
        # Mock data has 100 records
        # Let's say 10 already exist
        mock_df = mock_binance_client.download_date_range.return_value
        first_10_timestamps = list(mock_df["timestamp"].iloc[:10])  # Use list to preserve order
        
        # Create existing data with first 10 timestamps
        existing = [
            MarketData(
                symbol="btcusdt",
                interval="1h",
                timestamp=ts,
                open=45000.0,
                high=45100.0,
                low=44900.0,
                close=45000.0,
                volume=100.0
            )
            for ts in first_10_timestamps
        ]
        mock_repository.get_by_date_range.return_value = existing
        
        # Make save() return the actual length of data passed to it
        def save_side_effect(data):
            return len(data)
        mock_repository.save.side_effect = save_side_effect
        
        count = service.update_latest_data(
            symbol="btcusdt",
            interval="1h",
            lookback_hours=24
        )
        
        # Should save 90 records (100 - 10 existing)
        assert count["rows_added"] == 90
        assert count["symbol"] == "btcusdt"
    
    def test_get_data(self, service, mock_repository):
        """Test data retrieval."""
        sample_data = [
            MarketData(
                symbol="btcusdt",
                interval="1h",
                timestamp=datetime(2024, 1, 1),
                open=45000.0,
                high=45100.0,
                low=44900.0,
                close=45000.0,
                volume=100.0
            )
        ]
        mock_repository.get_by_date_range.return_value = sample_data
        
        data = service.get_data(
            "btcusdt", "1h",
            datetime(2024, 1, 1),
            datetime(2024, 1, 31)
        )
        
        assert len(data) == 1
        assert data[0].symbol == "btcusdt"
    
    def test_get_latest(self, service, mock_repository):
        """Test getting latest data."""
        sample_data = [
            MarketData(
                symbol="btcusdt",
                interval="1h",
                timestamp=datetime(2024, 1, 1),
                open=45000.0,
                high=45100.0,
                low=44900.0,
                close=45000.0,
                volume=100.0
            )
        ]
        mock_repository.get_latest.return_value = sample_data
        
        data = service.get_latest("btcusdt", "1h", limit=10)
        
        assert len(data) == 1
        mock_repository.get_latest.assert_called_once_with("btcusdt", "1h", 10)
    
    def test_get_data_as_dataframe(self, service, mock_repository):
        """Test getting data as DataFrame."""
        sample_data = [
            MarketData(
                symbol="btcusdt",
                interval="1h",
                timestamp=pd.Timestamp("2024-01-01", tz="UTC"),
                open=45000.0,
                high=45100.0,
                low=44900.0,
                close=45000.0,
                volume=100.0
            )
        ]
        mock_repository.get_by_date_range.return_value = sample_data
        
        df = service.get_data_as_dataframe(
            "btcusdt", "1h",
            datetime(2024, 1, 1),
            datetime(2024, 1, 31)
        )
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "close" in df.columns
    
    def test_get_data_as_dataframe_empty(self, service, mock_repository):
        """Test getting empty DataFrame when no data."""
        mock_repository.get_by_date_range.return_value = []
        
        df = service.get_data_as_dataframe(
            "btcusdt", "1h",
            datetime(2024, 1, 1),
            datetime(2024, 1, 31)
        )
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert "close" in df.columns
    
    def test_delete_old_data(self, service, mock_repository):
        """Test deleting old data."""
        mock_repository.delete_by_date_range.return_value = 500
        
        count = service.delete_old_data(
            symbol="btcusdt",
            interval="1h",
            older_than_days=90
        )
        
        assert count == 500
        mock_repository.delete_by_date_range.assert_called_once()
    
    def test_get_data_summary(self, service, mock_repository):
        """Test getting data summary."""
        dates = [
            datetime(2024, 1, 1),
            datetime(2024, 2, 1),
            datetime(2024, 3, 1)
        ]
        mock_repository.get_available_dates.return_value = dates
        
        summary = service.get_data_summary("btcusdt", "1h")
        
        assert summary["available"] is True
        assert summary["num_partitions"] == 3
        assert summary["total_days"] == 60
    
    def test_get_data_summary_no_data(self, service, mock_repository):
        """Test summary when no data available."""
        mock_repository.get_available_dates.return_value = []
        
        summary = service.get_data_summary("btcusdt", "1h")
        
        assert summary["available"] is False
        assert summary["first_date"] is None
