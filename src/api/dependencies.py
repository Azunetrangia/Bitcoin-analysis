"""
API Dependencies - Service injection for FastAPI.

This provides dependency injection for application services,
making them available to API route handlers.
"""

from functools import lru_cache
from typing import Tuple

from src.application.services.market_data_service import MarketDataService
from src.application.services.analysis_service import AnalysisService
from src.application.services.scheduler_service import SchedulerService
from src.application.services.pipeline_orchestrator import PipelineOrchestrator
from src.infrastructure.data.binance_client import BinanceDataClient
from src.infrastructure.repositories.parquet_repository import ParquetMarketDataRepository
from src.infrastructure.storage.parquet_manager import ParquetManager
from src.infrastructure.storage.duckdb_query_engine import DuckDBQueryEngine
from src.domain.services.technical_analysis import TechnicalAnalysisService
from src.domain.services.regime_classifier import RegimeClassifierService
from src.domain.services.risk_calculator import RiskCalculatorService
from src.shared.config.settings import Settings


class ServiceContainer:
    """Container for application services (singleton)."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize all services."""
        # Settings
        self.settings = Settings()
        
        # Infrastructure
        self.binance = BinanceDataClient()
        
        # Keep parquet repository for backward compatibility
        self.repository = ParquetMarketDataRepository(self.settings.STORAGE_PATH)
        
        # Domain services
        self.ta_service = TechnicalAnalysisService()
        self.regime_classifier = RegimeClassifierService(self.ta_service)
        self.risk_calculator = RiskCalculatorService()
        
        # Application services
        self.market_service = MarketDataService(
            self.repository,
            self.binance
        )
        self.analysis_service = AnalysisService(
            self.market_service,
            self.ta_service,
            self.risk_calculator,
            self.regime_classifier
        )
        self.scheduler_service = SchedulerService(
            self.market_service,
            self.analysis_service
        )
        self.orchestrator = PipelineOrchestrator(
            self.market_service,
            self.analysis_service
        )


# Global service container
_container: ServiceContainer = None


def get_container() -> ServiceContainer:
    """Get or create service container."""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


# Dependency functions for FastAPI
def get_market_service() -> MarketDataService:
    """Get market data service instance."""
    return get_container().market_service


def get_analysis_service() -> AnalysisService:
    """Get analysis service instance."""
    return get_container().analysis_service


def get_scheduler_service() -> SchedulerService:
    """Get scheduler service instance."""
    return get_container().scheduler_service


def get_orchestrator() -> PipelineOrchestrator:
    """Get pipeline orchestrator instance."""
    return get_container().orchestrator


def get_services() -> Tuple[MarketDataService, AnalysisService]:
    """
    Get multiple services at once.
    
    Returns:
        Tuple of (market_service, analysis_service)
    """
    container = get_container()
    return container.market_service, container.analysis_service
