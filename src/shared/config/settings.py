"""
Application Settings Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Centralized configuration using Pydantic Settings.
Environment variables are loaded from .env file.

Usage:
    from src.shared.config.settings import settings
    
    # Access configuration
    print(settings.R2_BUCKET_NAME)
    print(settings.SUPABASE_URL)
    
    # Settings are validated at startup
    if settings.ENVIRONMENT == "production":
        # Production-specific logic
        pass
"""

from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden by creating a .env file
    or setting environment variables.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # ===== Application Settings =====
    APP_NAME: str = "Bitcoin Market Intelligence"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # ===== Cloudflare R2 Storage =====
    R2_ACCOUNT_ID: str = Field(default="", description="Cloudflare R2 Account ID")
    R2_ACCESS_KEY_ID: str = Field(default="", description="R2 Access Key")
    R2_SECRET_ACCESS_KEY: str = Field(default="", description="R2 Secret Key")
    R2_BUCKET_NAME: str = Field(default="bitcoin-market-data", description="R2 Bucket Name")
    R2_PUBLIC_URL: str | None = Field(default=None, description="Public URL if using public bucket")
    R2_ENDPOINT_URL: str = Field(
        default="https://ACCOUNT_ID.r2.cloudflarestorage.com",
        description="R2 S3-compatible endpoint"
    )
    
    # ===== Supabase Database =====
    SUPABASE_URL: str = Field(default="", description="Supabase Project URL")
    SUPABASE_KEY: str = Field(default="", description="Supabase Anonymous Key")
    SUPABASE_SERVICE_KEY: str = Field(default="", description="Supabase Service Role Key (admin)")
    
    # ===== Data Sources =====
    BINANCE_DATA_BASE_URL: str = "https://data.binance.vision"
    DEFAULT_SYMBOL: str = "BTCUSDT"
    DEFAULT_INTERVAL: str = "1h"
    
    # ===== Storage Paths =====
    STORAGE_PATH: str = Field(default="./data/parquet", description="Local Parquet storage path")
    
    # ===== Data Processing =====
    CACHE_TTL: int = Field(default=3600, description="Cache TTL in seconds")
    MAX_QUERY_ROWS: int = Field(default=100000, description="Max rows per query")
    HISTORICAL_DATA_YEARS: int = Field(default=3, description="Years of historical data to maintain")
    HOT_DATA_DAYS: int = Field(default=30, description="Days of recent data in hot storage (PostgreSQL)")
    
    # ===== Analytics Settings =====
    GMM_N_COMPONENTS: int = Field(default=4, description="Number of GMM clusters (Bull/Bear/Neutral/HighVol)")
    HMM_N_STATES: int = Field(default=4, description="Number of HMM states for smoothing")
    VAR_CONFIDENCE_LEVEL: float = Field(default=0.95, description="VaR confidence level (95%)")
    RISK_FREE_RATE: float = Field(default=0.02, description="Annual risk-free rate for Sharpe ratio")
    
    # ===== Visualization Settings =====
    PLOTLY_MAX_POINTS: int = Field(default=2000, description="Max points before resampling kicks in")
    STREAMLIT_PORT: int = Field(default=8501, description="Streamlit server port")
    
    @property
    def r2_endpoint_url_formatted(self) -> str:
        """Get properly formatted R2 endpoint URL."""
        return self.R2_ENDPOINT_URL.replace("ACCOUNT_ID", self.R2_ACCOUNT_ID)
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"


# Global settings instance
settings = Settings()


# Validation on import
if __name__ != "__main__":
    # Warn if critical settings are missing in production
    if settings.is_production():
        critical_settings = [
            "R2_ACCOUNT_ID",
            "R2_ACCESS_KEY_ID", 
            "R2_SECRET_ACCESS_KEY",
            "SUPABASE_URL",
            "SUPABASE_KEY",
        ]
        
        missing = [s for s in critical_settings if not getattr(settings, s)]
        if missing:
            import warnings
            warnings.warn(
                f"⚠️ Production environment detected but missing critical settings: {missing}"
            )
