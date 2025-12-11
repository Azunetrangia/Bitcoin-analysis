"""
Bitcoin Market Intelligence Platform
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A production-grade analytics platform for Bitcoin market analysis,
focusing on Market Regime Classification and Risk Management.

Key Components:
- Domain: Core business logic (models, services, repositories)
- Infrastructure: External integrations (data sources, storage)
- Application: Use cases and orchestration
- Presentation: Streamlit dashboard UI
- Shared: Cross-cutting concerns (config, utils, exceptions)

Clean Architecture Principles:
- Dependency inversion (outer layers depend on inner)
- Testability (business logic independent of frameworks)
- Maintainability (separation of concerns)

Usage:
    from src.domain.models import MarketData
    from src.application.use_cases import AnalyzeRegimeUseCase
"""

__version__ = "0.1.0"
__author__ = "Your Name"

# Package metadata
__all__ = [
    "domain",
    "infrastructure",
    "application",
    "presentation",
    "shared",
]
