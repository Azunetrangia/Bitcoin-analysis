"""
Custom Exceptions
~~~~~~~~~~~~~~~~~

Domain-specific exception classes.

Exception Hierarchy:
- AppException (base)
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
"""

from src.shared.exceptions.custom_exceptions import (
    AppException,
    DataException,
    DataNotFoundError,
    DataValidationError,
    DataDownloadError,
    DataParsingError,
    AnalysisException,
    RegimeClassificationError,
    RiskCalculationError,
    TechnicalIndicatorError,
    ModelFitError,
    InfrastructureException,
    StorageError,
    DatabaseError,
    CacheError,
    APIError,
    ConfigurationError,
    ValidationError,
)

__all__ = [
    "AppException",
    "DataException",
    "DataNotFoundError",
    "DataValidationError",
    "DataDownloadError",
    "DataParsingError",
    "AnalysisException",
    "RegimeClassificationError",
    "RiskCalculationError",
    "TechnicalIndicatorError",
    "ModelFitError",
    "InfrastructureException",
    "StorageError",
    "DatabaseError",
    "CacheError",
    "APIError",
    "ConfigurationError",
    "ValidationError",
]
