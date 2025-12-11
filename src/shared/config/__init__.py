"""
Configuration Management
~~~~~~~~~~~~~~~~~~~~~~~~

Application configuration using Pydantic Settings.

Settings are loaded from:
1. Environment variables (.env file)
2. Default values

Usage:
    from src.shared.config import settings
    
    print(settings.R2_BUCKET_NAME)
    print(settings.SUPABASE_URL)
"""

from src.shared.config.settings import settings, Settings

__all__ = ["settings", "Settings"]
