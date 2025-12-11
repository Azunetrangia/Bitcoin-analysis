"""
Database Layer
~~~~~~~~~~~~~~

Database implementations for hot data (PostgreSQL/Supabase).

Modules:
- supabase_client: Supabase connection and queries
- models: SQLAlchemy ORM models (optional)
- migrations: Database schema migrations
"""

from src.infrastructure.database.supabase_client import SupabaseClient

__all__ = [
    "SupabaseClient",
]  # Database modules will be added as they're implemented
