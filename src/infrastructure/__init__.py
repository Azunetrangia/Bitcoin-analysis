"""
Infrastructure Layer
~~~~~~~~~~~~~~~~~~~

External integrations and implementations of domain interfaces.

Components:
- data/: Data source integrations (Binance API, file loaders)
- storage/: Storage implementations (R2, Parquet, DuckDB)
- database/: Database implementations (Supabase/PostgreSQL)

Design Patterns:
- Repository pattern implementations
- Strategy pattern for different data sources
- Factory pattern for database connections
"""

__all__ = [
    "data",
    "storage",
    "database",
]
