"""
Domain Interface: Market Data Repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Abstract interface defining the contract for market data access.

This follows the Repository Pattern from Domain-Driven Design.
Implementations live in the infrastructure layer.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from src.domain.models.market_data import MarketData, MarketDataCollection


class IMarketDataRepository(ABC):
    """
    Abstract interface for market data repository.
    
    This interface defines what operations can be performed on market data,
    without specifying HOW they are implemented.
    
    Implementations might use:
    - PostgreSQL (hot storage for recent data)
    - Parquet files (warm storage for historical data)
    - CSV files (local testing)
    - In-memory cache
    """
    
    @abstractmethod
    def get_by_date_range(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> MarketDataCollection:
        """
        Retrieve market data for a specific date range.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Time interval ('1h', '4h', '1d')
            start: Start datetime (inclusive)
            end: End datetime (inclusive)
            
        Returns:
            MarketDataCollection with data in range
            
        Raises:
            DataNotFoundError: If no data found
        """
        pass
    
    @abstractmethod
    def get_latest(
        self,
        symbol: str,
        interval: str,
        limit: int = 100
    ) -> MarketDataCollection:
        """
        Retrieve latest N data points.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            limit: Number of latest points to retrieve
            
        Returns:
            MarketDataCollection with latest data
        """
        pass
    
    @abstractmethod
    def save(self, data: MarketDataCollection) -> None:
        """
        Save market data collection.
        
        Args:
            data: MarketDataCollection to save
            
        Raises:
            StorageError: If save fails
        """
        pass
    
    @abstractmethod
    def exists(
        self,
        symbol: str,
        interval: str,
        timestamp: datetime
    ) -> bool:
        """
        Check if data exists for given timestamp.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            timestamp: Specific timestamp
            
        Returns:
            True if data exists
        """
        pass
    
    @abstractmethod
    def delete_by_date_range(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> int:
        """
        Delete data in date range.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            
        Returns:
            Number of records deleted
        """
        pass
    
    @abstractmethod
    def get_available_dates(
        self,
        symbol: str,
        interval: str
    ) -> List[datetime]:
        """
        Get list of available dates with data.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            
        Returns:
            List of timestamps with available data
        """
        pass
