"""
DuckDB Query Engine
~~~~~~~~~~~~~~~~~~~

Infrastructure component for efficient OLAP queries on Parquet files.

DuckDB is an in-process OLAP database optimized for analytics:
- SQL interface for Parquet files
- Columnar execution (only read needed columns)
- HTTP range requests (query remote Parquet without full download)
- Zero-copy integration with Pandas/Arrow

Use Cases:
1. Local: Query Parquet files on disk
2. Remote: Query Parquet files on R2 via HTTP (saves egress fees)
3. Analytics: Complex aggregations, joins, window functions
"""

import duckdb
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Union

from src.shared.exceptions.custom_exceptions import StorageError
from src.shared.utils.logging_utils import get_logger
from src.shared.utils.datetime_utils import to_utc

logger = get_logger(__name__)


class DuckDBQueryEngine:
    """
    Query engine for Parquet files using DuckDB.
    
    DuckDB provides SQL interface with:
    - Automatic Parquet schema detection
    - Predicate pushdown (filter at file level)
    - Projection pushdown (only read needed columns)
    - Statistics-based pruning
    """
    
    def __init__(self, database: str = ":memory:"):
        """
        Initialize DuckDB Query Engine.
        
        Args:
            database: Database file path (":memory:" for in-memory)
        """
        self.conn = duckdb.connect(database)
        
        # Install and load httpfs extension for remote Parquet
        try:
            self.conn.execute("INSTALL httpfs")
            self.conn.execute("LOAD httpfs")
            logger.debug("✅ DuckDB httpfs extension loaded")
        except Exception as e:
            logger.warning(f"⚠️ Could not load httpfs extension: {e}")
    
    def query(
        self,
        sql: str,
        params: Optional[dict] = None
    ) -> pd.DataFrame:
        """
        Execute SQL query and return DataFrame.
        
        Args:
            sql: SQL query
            params: Query parameters (for parameterized queries)
            
        Returns:
            Query result as DataFrame
            
        Example:
            >>> engine = DuckDBQueryEngine()
            >>> df = engine.query('''
            ...     SELECT * FROM 'data/btcusdt/1h/2024-01/data.parquet'
            ...     WHERE timestamp >= '2024-01-15'
            ... ''')
        """
        try:
            if params:
                result = self.conn.execute(sql, params).df()
            else:
                result = self.conn.execute(sql).df()
            
            logger.debug(f"✅ Query executed", rows=len(result))
            
            return result
            
        except Exception as e:
            raise StorageError(
                f"DuckDB query failed: {str(e)}",
                details={"sql": sql[:200]}  # First 200 chars
            )
    
    def query_parquet_files(
        self,
        file_pattern: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        columns: Optional[List[str]] = None,
        filters: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Query Parquet files with optional filtering.
        
        Args:
            file_pattern: Glob pattern for files (e.g., 'data/btcusdt/1h/**/data.parquet')
            start: Start datetime filter
            end: End datetime filter
            columns: Columns to select (None = all)
            filters: Additional SQL WHERE conditions
            
        Returns:
            Query result as DataFrame
            
        Example:
            >>> engine = DuckDBQueryEngine()
            >>> df = engine.query_parquet_files(
            ...     'data/btcusdt/1h/**/data.parquet',
            ...     start=datetime(2024, 1, 1),
            ...     end=datetime(2024, 1, 31),
            ...     columns=['timestamp', 'close', 'volume']
            ... )
        """
        # Build SELECT clause
        if columns:
            select_clause = ", ".join(columns)
        else:
            select_clause = "*"
        
        # Build WHERE clause
        where_conditions = []
        
        if start:
            start_utc = to_utc(start)
            where_conditions.append(f"timestamp >= '{start_utc.isoformat()}'")
        
        if end:
            end_utc = to_utc(end)
            where_conditions.append(f"timestamp <= '{end_utc.isoformat()}'")
        
        if filters:
            where_conditions.append(filters)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Build SQL query
        sql = f"""
            SELECT {select_clause}
            FROM read_parquet('{file_pattern}')
            WHERE {where_clause}
            ORDER BY timestamp
        """
        
        logger.info(
            f"🔍 Querying Parquet files",
            pattern=file_pattern,
            filters=where_clause
        )
        
        return self.query(sql)
    
    def query_remote_parquet(
        self,
        url: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Query remote Parquet file via HTTP (e.g., from R2).
        
        This uses HTTP range requests to only download needed data.
        
        Args:
            url: HTTP(S) URL to Parquet file
            start: Start datetime filter
            end: End datetime filter
            columns: Columns to select
            
        Returns:
            Query result as DataFrame
            
        Example:
            >>> engine = DuckDBQueryEngine()
            >>> df = engine.query_remote_parquet(
            ...     'https://pub-xxx.r2.dev/btcusdt/1h/2024-01/data.parquet',
            ...     columns=['timestamp', 'close']
            ... )
        """
        # Build SELECT clause
        if columns:
            select_clause = ", ".join(columns)
        else:
            select_clause = "*"
        
        # Build WHERE clause
        where_conditions = []
        
        if start:
            start_utc = to_utc(start)
            where_conditions.append(f"timestamp >= '{start_utc.isoformat()}'")
        
        if end:
            end_utc = to_utc(end)
            where_conditions.append(f"timestamp <= '{end_utc.isoformat()}'")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Build SQL query
        sql = f"""
            SELECT {select_clause}
            FROM read_parquet('{url}')
            WHERE {where_clause}
            ORDER BY timestamp
        """
        
        logger.info(f"🌐 Querying remote Parquet", url=url)
        
        return self.query(sql)
    
    def aggregate(
        self,
        file_pattern: str,
        groupby: List[str],
        aggregations: dict,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Perform aggregation on Parquet files.
        
        Args:
            file_pattern: Glob pattern for files
            groupby: Columns to group by
            aggregations: Dict of {column: agg_function}
                         e.g., {'close': 'avg', 'volume': 'sum'}
            start: Start datetime filter
            end: End datetime filter
            
        Returns:
            Aggregated DataFrame
            
        Example:
            >>> # Daily aggregation from hourly data
            >>> engine = DuckDBQueryEngine()
            >>> df = engine.aggregate(
            ...     'data/btcusdt/1h/**/data.parquet',
            ...     groupby=['DATE_TRUNC(\'day\', timestamp) as day'],
            ...     aggregations={
            ...         'open': 'first',
            ...         'high': 'max',
            ...         'low': 'min',
            ...         'close': 'last',
            ...         'volume': 'sum'
            ...     }
            ... )
        """
        # Build aggregation expressions
        agg_exprs = []
        for col, func in aggregations.items():
            if func == "first":
                agg_exprs.append(f"FIRST({col}) as {col}")
            elif func == "last":
                agg_exprs.append(f"LAST({col}) as {col}")
            elif func == "avg":
                agg_exprs.append(f"AVG({col}) as {col}")
            elif func == "sum":
                agg_exprs.append(f"SUM({col}) as {col}")
            elif func == "max":
                agg_exprs.append(f"MAX({col}) as {col}")
            elif func == "min":
                agg_exprs.append(f"MIN({col}) as {col}")
            else:
                agg_exprs.append(f"{func}({col}) as {col}")
        
        select_clause = ", ".join(groupby + agg_exprs)
        
        # Build WHERE clause
        where_conditions = []
        
        if start:
            start_utc = to_utc(start)
            where_conditions.append(f"timestamp >= '{start_utc.isoformat()}'")
        
        if end:
            end_utc = to_utc(end)
            where_conditions.append(f"timestamp <= '{end_utc.isoformat()}'")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Extract column names for GROUP BY (remove aliases)
        group_cols = []
        for col in groupby:
            # Split on 'as' to get the expression before alias
            if ' as ' in col.lower():
                group_cols.append(col.split(' as ')[0].strip())
            else:
                group_cols.append(col)
        
        group_clause = ", ".join(group_cols)
        
        # Build SQL query
        sql = f"""
            SELECT {select_clause}
            FROM read_parquet('{file_pattern}')
            WHERE {where_clause}
            GROUP BY {group_clause}
            ORDER BY {group_cols[0]}
        """
        
        logger.info(f"📊 Aggregating data", pattern=file_pattern)
        
        return self.query(sql)
    
    def get_stats(self, file_pattern: str) -> dict:
        """
        Get statistics about Parquet files.
        
        Args:
            file_pattern: Glob pattern for files
            
        Returns:
            Dictionary with stats (count, min_date, max_date, etc.)
        """
        sql = f"""
            SELECT
                COUNT(*) as row_count,
                MIN(timestamp) as min_date,
                MAX(timestamp) as max_date,
                MIN(close) as min_price,
                MAX(close) as max_price,
                AVG(close) as avg_price,
                SUM(volume) as total_volume
            FROM read_parquet('{file_pattern}')
        """
        
        result = self.query(sql)
        
        return result.iloc[0].to_dict() if len(result) > 0 else {}
    
    def close(self):
        """Close DuckDB connection."""
        self.conn.close()
        logger.debug("🔌 DuckDB connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
