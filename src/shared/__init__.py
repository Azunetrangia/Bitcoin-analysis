"""
Shared Layer
~~~~~~~~~~~~

Cross-cutting concerns shared across all layers.

Components:
- config/: Configuration management
- utils/: Utility functions
- exceptions/: Custom exception classes

Usage:
    from src.shared.config import settings
    from src.shared.exceptions import DataNotFoundError
"""

__all__ = [
    "config",
    "utils",
    "exceptions",
]
