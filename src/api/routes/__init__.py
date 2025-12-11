"""
API Routes Module.

Exports all API routers.
"""

from src.api.routes.market_data import router as market_data_router
from src.api.routes.analysis import router as analysis_router
from src.api.routes.scheduler import router as scheduler_router

__all__ = [
    "market_data_router",
    "analysis_router", 
    "scheduler_router"
]
