"""
FastAPI Main Application - Bitcoin Market Intelligence API.

This provides RESTful endpoints for:
- Market data queries
- Technical analysis
- Regime classification
- Risk metrics
- Portfolio insights
"""

from datetime import datetime
from typing import Optional
import logging

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import market_data_router, analysis_router, scheduler_router
from src.api.dependencies import get_services
from src.shared.config.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize settings
settings = Settings()

# Create FastAPI app
app = FastAPI(
    title="Bitcoin Market Intelligence API",
    description="""
    Bitcoin Market Intelligence & Risk Management Platform
    
    ## Features
    
    * **Market Data**: Query historical OHLCV data with flexible filters
    * **Technical Analysis**: RSI, MACD, ATR, Bollinger Bands
    * **Regime Classification**: Bull/Bear/Neutral/High Volatility detection using HMM
    * **Risk Metrics**: Drawdown, Sharpe ratio, VaR, volatility analysis
    * **Scheduler**: Automated data pipeline management
    
    ## Authentication
    
    Currently no authentication required (add in production).
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with prefixes and tags
app.include_router(
    market_data_router,
    prefix="/api/v1/market-data",
    tags=["Market Data"]
)
app.include_router(
    analysis_router,
    prefix="/api/v1/analysis",
    tags=["Analysis"]
)
app.include_router(
    scheduler_router,
    prefix="/api/v1/scheduler",
    tags=["Scheduler"]
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns API status and version.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "Bitcoin Market Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "market_data": "/api/v1/market-data",
            "analysis": "/api/v1/analysis",
            "scheduler": "/api/v1/scheduler"
        }
    }


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("🚀 Starting Bitcoin Market Intelligence API")
    logger.info(f"📁 Storage path: {settings.STORAGE_PATH}")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("🛑 Shutting down Bitcoin Market Intelligence API")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
