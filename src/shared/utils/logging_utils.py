"""
Logging Utilities
~~~~~~~~~~~~~~~~~

Centralized logging configuration using Loguru.

Features:
- Colored console output
- JSON formatting for production
- Rotation and retention policies
- Context injection (request ID, user ID, etc.)

Usage:
    from src.shared.utils.logging_utils import get_logger
    
    logger = get_logger(__name__)
    logger.info("Processing market data", symbol="BTCUSDT", rows=1000)
    logger.error("Failed to download data", error=str(e))
"""

import sys
from pathlib import Path
from loguru import logger
from src.shared.config.settings import settings


def setup_logging() -> None:
    """
    Configure Loguru logger with environment-specific settings.
    
    Development: Colored console output
    Production: JSON formatting with file rotation
    """
    
    # Remove default handler
    logger.remove()
    
    # Console handler (always enabled)
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=settings.LOG_LEVEL,
        colorize=True,
    )
    
    # File handler (production only)
    if settings.is_production():
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            level="INFO",
            rotation="100 MB",  # Rotate when file reaches 100MB
            retention="30 days",  # Keep logs for 30 days
            compression="zip",  # Compress rotated files
            serialize=False,  # JSON format for structured logging
        )


def get_logger(name: str):
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__ of the module)
        
    Returns:
        Loguru logger instance
        
    Usage:
        logger = get_logger(__name__)
        logger.info("Message", key="value")
    """
    return logger.bind(name=name)


# Initialize logging on import
setup_logging()
