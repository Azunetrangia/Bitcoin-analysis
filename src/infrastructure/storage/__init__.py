"""
Storage Layer
~~~~~~~~~~~~~

Storage implementations for warm data (Parquet, R2).

Modules:
- parquet_manager: Read/write Parquet files with partitioning
- r2_client: Cloudflare R2 integration (S3-compatible)
- duckdb_query_engine: Efficient OLAP queries on Parquet
"""

from src.infrastructure.storage.parquet_manager import ParquetManager
from src.infrastructure.storage.duckdb_query_engine import DuckDBQueryEngine
from src.infrastructure.storage.r2_client import R2Client

__all__ = [
    "ParquetManager",
    "DuckDBQueryEngine",
    "R2Client",
]  # Storage modules will be added as they're implemented
