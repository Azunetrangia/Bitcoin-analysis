"""
Domain Layer
~~~~~~~~~~~~

This layer contains the core business logic and domain models.
It has NO dependencies on external frameworks or infrastructure.

Components:
- models/: Domain entities (MarketData, Regime, RiskMetrics)
- services/: Domain services (RegimeClassifier, RiskCalculator)
- interfaces/: Abstract interfaces (Repository patterns)

Design Principles:
- Pure Python (no framework dependencies)
- Rich domain models with business logic
- Interface-based design for testability
"""

__all__ = [
    "models",
    "services",
    "interfaces",
]
