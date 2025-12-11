"""
Supabase Database Client
~~~~~~~~~~~~~~~~~~~~~~~~~

Infrastructure component for PostgreSQL database via Supabase.

Why Supabase?
- PostgreSQL (powerful, reliable)
- Real-time subscriptions (WebSocket)
- Built-in auth & row-level security
- Free tier: 500MB database, 2GB file storage
- Generous paid tier: $25/month for 8GB

Use Cases:
- Hot storage (last 30 days)
- User preferences & settings
- Trading signals & alerts
- Real-time data streaming
"""

from supabase import create_client, Client
from postgrest.exceptions import APIError
import pandas as pd
from datetime import datetime
from typing import List, Optional, Dict, Any

from src.shared.exceptions.custom_exceptions import StorageError
from src.shared.utils.logging_utils import get_logger
from src.shared.utils.datetime_utils import to_utc

logger = get_logger(__name__)


class SupabaseClient:
    """
    Client for Supabase PostgreSQL database.
    
    Configuration:
        SUPABASE_URL: Your Supabase project URL
        SUPABASE_KEY: Your Supabase anon/service key
    
    Tables:
        - market_data: OHLCV data (hot storage)
        - regime_classifications: Regime predictions
        - risk_metrics: Risk calculations
        - user_preferences: User settings
    """
    
    def __init__(self, url: str, key: str):
        """
        Initialize Supabase client.
        
        Args:
            url: Supabase project URL
            key: Supabase API key (anon or service role)
        """
        self.url = url
        self.client: Client = create_client(url, key)
        
        logger.info(f"✅ Supabase client initialized", url=url)
    
    # ==================== Market Data Operations ====================
    
    def insert_market_data(
        self,
        df: pd.DataFrame,
        table: str = "market_data"
    ) -> int:
        """
        Insert market data into database.
        
        Args:
            df: DataFrame with columns: symbol, interval, timestamp, open, high, low, close, volume
            table: Table name
            
        Returns:
            Number of rows inserted
            
        Example:
            >>> df = pd.DataFrame({
            ...     'symbol': ['btcusdt'] * 100,
            ...     'interval': ['1h'] * 100,
            ...     'timestamp': pd.date_range('2024-01-01', periods=100, freq='1h'),
            ...     'open': 45000.0,
            ...     'high': 45100.0,
            ...     'low': 44900.0,
            ...     'close': 45000.0,
            ...     'volume': 100.5
            ... })
            >>> client.insert_market_data(df)
        """
        try:
            # Convert DataFrame to list of dicts
            records = df.to_dict("records")
            
            # Convert timestamps to ISO format
            for record in records:
                if "timestamp" in record:
                    if isinstance(record["timestamp"], pd.Timestamp):
                        record["timestamp"] = record["timestamp"].isoformat()
                    elif isinstance(record["timestamp"], datetime):
                        record["timestamp"] = to_utc(record["timestamp"]).isoformat()
            
            # Insert in batches (Supabase limit: 1000 per request)
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                
                response = self.client.table(table).insert(batch).execute()
                total_inserted += len(batch)
                
                logger.debug(f"✅ Inserted batch", rows=len(batch))
            
            logger.info(
                f"✅ Inserted market data",
                table=table,
                rows=total_inserted
            )
            
            return total_inserted
            
        except APIError as e:
            raise StorageError(
                f"Supabase insert failed: {str(e)}",
                details={"table": table, "rows": len(df)}
            )
    
    def get_market_data(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        table: str = "market_data"
    ) -> pd.DataFrame:
        """
        Query market data by date range.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            table: Table name
            
        Returns:
            DataFrame with market data
        """
        try:
            start_iso = to_utc(start).isoformat()
            end_iso = to_utc(end).isoformat()
            
            response = (
                self.client.table(table)
                .select("*")
                .eq("symbol", symbol)
                .eq("interval", interval)
                .gte("timestamp", start_iso)
                .lte("timestamp", end_iso)
                .order("timestamp")
                .execute()
            )
            
            if not response.data:
                logger.warning(f"⚠️ No data found", symbol=symbol, interval=interval)
                return pd.DataFrame()
            
            df = pd.DataFrame(response.data)
            
            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            
            logger.info(
                f"✅ Retrieved market data",
                symbol=symbol,
                interval=interval,
                rows=len(df)
            )
            
            return df
            
        except APIError as e:
            raise StorageError(
                f"Supabase query failed: {str(e)}",
                details={"symbol": symbol, "interval": interval}
            )
    
    def get_latest_market_data(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        table: str = "market_data"
    ) -> pd.DataFrame:
        """
        Get latest N rows of market data.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            limit: Number of rows
            table: Table name
            
        Returns:
            DataFrame with latest data
        """
        try:
            response = (
                self.client.table(table)
                .select("*")
                .eq("symbol", symbol)
                .eq("interval", interval)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            
            if not response.data:
                return pd.DataFrame()
            
            df = pd.DataFrame(response.data)
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            
            # Reverse to chronological order
            df = df.sort_values("timestamp").reset_index(drop=True)
            
            return df
            
        except APIError as e:
            raise StorageError(
                f"Supabase query failed: {str(e)}",
                details={"symbol": symbol, "interval": interval}
            )
    
    def delete_market_data_by_date(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        table: str = "market_data"
    ) -> int:
        """
        Delete market data by date range.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start datetime
            end: End datetime
            table: Table name
            
        Returns:
            Number of rows deleted
        """
        try:
            start_iso = to_utc(start).isoformat()
            end_iso = to_utc(end).isoformat()
            
            response = (
                self.client.table(table)
                .delete()
                .eq("symbol", symbol)
                .eq("interval", interval)
                .gte("timestamp", start_iso)
                .lte("timestamp", end_iso)
                .execute()
            )
            
            deleted_count = len(response.data) if response.data else 0
            
            logger.info(
                f"🗑️ Deleted market data",
                symbol=symbol,
                interval=interval,
                rows=deleted_count
            )
            
            return deleted_count
            
        except APIError as e:
            raise StorageError(
                f"Supabase delete failed: {str(e)}",
                details={"symbol": symbol, "interval": interval}
            )
    
    # ==================== Regime Classifications ====================
    
    def insert_regime_classification(
        self,
        symbol: str,
        interval: str,
        timestamp: datetime,
        regime: int,
        probabilities: Dict[int, float],
        features: Dict[str, float],
        table: str = "regime_classifications"
    ) -> Dict[str, Any]:
        """
        Insert regime classification result.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            timestamp: Classification timestamp
            regime: Regime label (0-3)
            probabilities: Dict of {regime: probability}
            features: Dict of feature values
            table: Table name
            
        Returns:
            Inserted record
        """
        try:
            record = {
                "symbol": symbol,
                "interval": interval,
                "timestamp": to_utc(timestamp).isoformat(),
                "regime": regime,
                "probabilities": probabilities,
                "features": features
            }
            
            response = self.client.table(table).insert(record).execute()
            
            logger.debug(
                f"✅ Inserted regime classification",
                symbol=symbol,
                regime=regime
            )
            
            return response.data[0] if response.data else {}
            
        except APIError as e:
            raise StorageError(
                f"Supabase insert failed: {str(e)}",
                details={"symbol": symbol}
            )
    
    def get_latest_regime(
        self,
        symbol: str,
        interval: str,
        table: str = "regime_classifications"
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest regime classification.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            table: Table name
            
        Returns:
            Latest regime record or None
        """
        try:
            response = (
                self.client.table(table)
                .select("*")
                .eq("symbol", symbol)
                .eq("interval", interval)
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            
            if not response.data:
                return None
            
            return response.data[0]
            
        except APIError as e:
            raise StorageError(
                f"Supabase query failed: {str(e)}",
                details={"symbol": symbol}
            )
    
    # ==================== Risk Metrics ====================
    
    def insert_risk_metrics(
        self,
        symbol: str,
        interval: str,
        timestamp: datetime,
        metrics: Dict[str, float],
        table: str = "risk_metrics"
    ) -> Dict[str, Any]:
        """
        Insert risk metrics calculation.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            timestamp: Calculation timestamp
            metrics: Dict of risk metrics (var, es, sharpe, etc.)
            table: Table name
            
        Returns:
            Inserted record
        """
        try:
            record = {
                "symbol": symbol,
                "interval": interval,
                "timestamp": to_utc(timestamp).isoformat(),
                **metrics
            }
            
            response = self.client.table(table).insert(record).execute()
            
            logger.debug(
                f"✅ Inserted risk metrics",
                symbol=symbol
            )
            
            return response.data[0] if response.data else {}
            
        except APIError as e:
            raise StorageError(
                f"Supabase insert failed: {str(e)}",
                details={"symbol": symbol}
            )
    
    # ==================== Utility Methods ====================
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute raw SQL query (requires service role key).
        
        Args:
            query: SQL query string
            
        Returns:
            Query results
        """
        try:
            response = self.client.rpc("execute_sql", {"query": query}).execute()
            return response.data
            
        except APIError as e:
            raise StorageError(
                f"Query execution failed: {str(e)}",
                details={"query": query[:200]}
            )
    
    def get_table_count(self, table: str) -> int:
        """
        Get total row count for a table.
        
        Args:
            table: Table name
            
        Returns:
            Row count
        """
        try:
            response = (
                self.client.table(table)
                .select("*", count="exact")
                .limit(1)
                .execute()
            )
            
            return response.count or 0
            
        except APIError as e:
            raise StorageError(
                f"Count query failed: {str(e)}",
                details={"table": table}
            )
