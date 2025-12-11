"""
Application Layer
~~~~~~~~~~~~~~~~~

Use cases and orchestration logic.

Components:
- use_cases/: Application use cases (AnalyzeRegime, CalculateRisk)
- dto/: Data Transfer Objects for inter-layer communication

Responsibilities:
- Orchestrate domain services
- Handle transaction boundaries
- Convert between domain models and DTOs
"""

__all__ = [
    "use_cases",
    "dto",
]
