"""
Custom Exception Classes
~~~~~~~~~~~~~~~~~~~~~~~~~

Domain-specific exceptions for better error handling and debugging.

Exception Hierarchy:
    AppException (base)
    ├── DataException
    │   ├── DataNotFoundError
    │   ├── DataValidationError
    │   └── DataDownloadError
    ├── AnalysisException
    │   ├── RegimeClassificationError
    │   └── RiskCalculationError
    └── InfrastructureException
        ├── StorageError
        └── DatabaseError

Usage:
    from src.shared.exceptions.custom_exceptions import DataNotFoundError
    
    if not data:
        raise DataNotFoundError("No data found for BTCUSDT")
"""

from typing import Any


# ===== Base Exception =====

class AppException(Exception):
    """
    Base exception for all application-specific errors.
    
    Attributes:
        message: Human-readable error message
        details: Additional context (dict, for structured logging)
    """
    
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ===== Data Exceptions =====

class DataException(AppException):
    """Base exception for data-related errors."""
    pass


class DataNotFoundError(DataException):
    """Raised when requested data is not found."""
    pass


class DataValidationError(DataException):
    """Raised when data fails validation checks."""
    pass


class DataDownloadError(DataException):
    """Raised when data download fails."""
    pass


class DataParsingError(DataException):
    """Raised when data parsing fails (CSV, Parquet, etc.)."""
    pass


# ===== Analysis Exceptions =====

class AnalysisException(AppException):
    """Base exception for analytics/modeling errors."""
    pass


class RegimeClassificationError(AnalysisException):
    """Raised when regime classification fails."""
    pass


class RiskCalculationError(AnalysisException):
    """Raised when risk metric calculation fails."""
    pass


class TechnicalIndicatorError(AnalysisException):
    """Raised when technical indicator calculation fails."""
    pass


class ModelFitError(AnalysisException):
    """Raised when model training/fitting fails."""
    pass


# ===== Infrastructure Exceptions =====

class InfrastructureException(AppException):
    """Base exception for infrastructure-related errors."""
    pass


class StorageError(InfrastructureException):
    """Raised when storage operations fail (R2, Parquet, DuckDB)."""
    pass


class DatabaseError(InfrastructureException):
    """Raised when database operations fail (Supabase, PostgreSQL)."""
    pass


class CacheError(InfrastructureException):
    """Raised when caching operations fail."""
    pass


class APIError(InfrastructureException):
    """Raised when external API calls fail."""
    pass


# ===== Configuration Exceptions =====

class ConfigurationError(AppException):
    """Raised when configuration is invalid or missing."""
    pass


# ===== Validation Exceptions =====

class ValidationError(AppException):
    """Raised when input validation fails."""
    pass
