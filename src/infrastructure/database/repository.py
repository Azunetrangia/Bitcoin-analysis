"""
Database Repository Layer
Handles all database operations for Bitcoin market intelligence system.

Author: Bitcoin Market Intelligence Team
Created: 2025-12-10
Dependencies: psycopg2-binary>=2.9.0, python-dotenv>=1.0.0
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


@dataclass
class CandleData:
    """Candlestick data model"""
    time: datetime
    symbol: str
    interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Decimal
    trades: int


@dataclass
class TradeData:
    """Trade data model"""
    time: datetime
    symbol: str
    trade_id: int
    price: Decimal
    quantity: Decimal
    is_buyer_maker: bool


@dataclass
class RiskMetrics:
    """Risk metrics data model"""
    time: datetime
    symbol: str
    interval: str
    mean_return: Optional[Decimal] = None
    volatility: Optional[Decimal] = None
    var_95: Optional[Decimal] = None
    var_99: Optional[Decimal] = None
    var_95_modified: Optional[Decimal] = None
    var_99_modified: Optional[Decimal] = None
    expected_shortfall_95: Optional[Decimal] = None
    expected_shortfall_99: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    skewness: Optional[Decimal] = None
    kurtosis: Optional[Decimal] = None
    sample_size: Optional[int] = None


@dataclass
class DerivativesMetrics:
    """Derivatives metrics data model"""
    time: datetime
    symbol: str
    exchange: str
    funding_rate: Optional[Decimal] = None
    funding_rate_annual: Optional[Decimal] = None
    open_interest: Optional[Decimal] = None
    open_interest_value: Optional[Decimal] = None
    long_ratio: Optional[Decimal] = None
    short_ratio: Optional[Decimal] = None
    mark_price: Optional[Decimal] = None
    index_price: Optional[Decimal] = None


@dataclass
class TradingSignalData:
    """Trading signal data model"""
    time: datetime
    symbol: str
    signal_type: str
    strength: str
    direction: str
    price: Decimal
    reason: str
    data: Optional[Dict[str, Any]] = None


class DatabaseRepository:
    """
    Database repository for Bitcoin market intelligence.
    Provides CRUD operations for all data models.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        min_connections: int = 2,
        max_connections: int = 10
    ):
        """
        Initialize database repository with connection pooling.

        Args:
            host: Database host (default from env DB_HOST)
            port: Database port (default from env DB_PORT)
            database: Database name (default from env DB_NAME)
            user: Database user (default from env DB_USER)
            password: Database password (default from env DB_PASSWORD)
            min_connections: Minimum pool connections
            max_connections: Maximum pool connections
        """
        self.host = host or os.getenv('DB_HOST', 'localhost')
        self.port = port or int(os.getenv('DB_PORT', '5432'))
        self.database = database or os.getenv('DB_NAME', 'btc_intelligence')
        self.user = user or os.getenv('DB_USER', 'postgres')
        self.password = password or os.getenv('DB_PASSWORD', 'postgres')

        # Create connection pool
        try:
            self.pool = ThreadedConnectionPool(
                min_connections,
                max_connections,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            logger.info(f"Database pool created: {self.database}@{self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        Automatically returns connection to pool.
        """
        conn = self.pool.getconn()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            self.pool.putconn(conn)

    def close(self):
        """Close all connections in pool"""
        if self.pool:
            self.pool.closeall()
            logger.info("Database pool closed")

    # ============================================================
    # CANDLES OPERATIONS
    # ============================================================

    def insert_candle(self, candle: CandleData) -> bool:
        """Insert single candle into database"""
        return self.insert_candles([candle])

    def insert_candles(self, candles: List[CandleData]) -> bool:
        """
        Bulk insert candles into database.
        Uses ON CONFLICT to update existing records.
        """
        if not candles:
            return False

        query = """
            INSERT INTO candles (
                time, symbol, interval, open, high, low, close,
                volume, quote_volume, trades
            ) VALUES %s
            ON CONFLICT (time, symbol, interval) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                quote_volume = EXCLUDED.quote_volume,
                trades = EXCLUDED.trades
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    values = [
                        (
                            c.time, c.symbol, c.interval, c.open, c.high, c.low,
                            c.close, c.volume, c.quote_volume, c.trades
                        )
                        for c in candles
                    ]
                    execute_values(cur, query, values)
                    conn.commit()
                    logger.info(f"Inserted {len(candles)} candles")
                    return True
        except Exception as e:
            logger.error(f"Failed to insert candles: {e}")
            return False

    def get_candles(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[CandleData]:
        """
        Query candles from database.

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe (e.g., '1m', '5m', '1h')
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Maximum number of records to return

        Returns:
            List of CandleData objects
        """
        query = """
            SELECT time, symbol, interval, open, high, low, close,
                   volume, quote_volume, trades
            FROM candles
            WHERE symbol = %s AND interval = %s
        """
        params = [symbol, interval]

        if start_time:
            query += " AND time >= %s"
            params.append(start_time)
        if end_time:
            query += " AND time <= %s"
            params.append(end_time)

        query += " ORDER BY time DESC LIMIT %s"
        params.append(limit)

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    return [CandleData(**row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query candles: {e}")
            return []

    def get_latest_candle(self, symbol: str, interval: str) -> Optional[CandleData]:
        """Get most recent candle for symbol/interval"""
        candles = self.get_candles(symbol, interval, limit=1)
        return candles[0] if candles else None

    # ============================================================
    # TRADES OPERATIONS
    # ============================================================

    def insert_trade(self, trade: TradeData) -> bool:
        """Insert single trade into database"""
        return self.insert_trades([trade])

    def insert_trades(self, trades: List[TradeData]) -> bool:
        """Bulk insert trades into database"""
        if not trades:
            return False

        query = """
            INSERT INTO trades (time, symbol, trade_id, price, quantity, is_buyer_maker)
            VALUES %s
            ON CONFLICT (time, symbol, trade_id) DO NOTHING
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    values = [
                        (t.time, t.symbol, t.trade_id, t.price, t.quantity, t.is_buyer_maker)
                        for t in trades
                    ]
                    execute_values(cur, query, values)
                    conn.commit()
                    logger.info(f"Inserted {len(trades)} trades")
                    return True
        except Exception as e:
            logger.error(f"Failed to insert trades: {e}")
            return False

    def get_trades(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[TradeData]:
        """Query trades from database"""
        query = "SELECT * FROM trades WHERE symbol = %s"
        params = [symbol]

        if start_time:
            query += " AND time >= %s"
            params.append(start_time)
        if end_time:
            query += " AND time <= %s"
            params.append(end_time)

        query += " ORDER BY time DESC LIMIT %s"
        params.append(limit)

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    return [TradeData(**row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query trades: {e}")
            return []

    def get_large_trades(
        self,
        symbol: str,
        min_quantity: Decimal,
        hours: int = 24,
        limit: int = 100
    ) -> List[TradeData]:
        """Get large trades above threshold quantity"""
        query = """
            SELECT * FROM trades
            WHERE symbol = %s
              AND quantity >= %s
              AND time > NOW() - INTERVAL '%s hours'
            ORDER BY quantity DESC, time DESC
            LIMIT %s
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, [symbol, min_quantity, hours, limit])
                    rows = cur.fetchall()
                    return [TradeData(**row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query large trades: {e}")
            return []

    # ============================================================
    # RISK METRICS OPERATIONS
    # ============================================================

    def insert_risk_metrics(self, metrics: RiskMetrics) -> bool:
        """Insert risk metrics into database"""
        query = """
            INSERT INTO risk_metrics (
                time, symbol, interval, mean_return, volatility,
                var_95, var_99, var_95_modified, var_99_modified,
                expected_shortfall_95, expected_shortfall_99,
                sharpe_ratio, sortino_ratio, max_drawdown,
                skewness, kurtosis, sample_size
            ) VALUES (
                %(time)s, %(symbol)s, %(interval)s, %(mean_return)s, %(volatility)s,
                %(var_95)s, %(var_99)s, %(var_95_modified)s, %(var_99_modified)s,
                %(expected_shortfall_95)s, %(expected_shortfall_99)s,
                %(sharpe_ratio)s, %(sortino_ratio)s, %(max_drawdown)s,
                %(skewness)s, %(kurtosis)s, %(sample_size)s
            )
            ON CONFLICT (time, symbol, interval) DO UPDATE SET
                mean_return = EXCLUDED.mean_return,
                volatility = EXCLUDED.volatility,
                var_95 = EXCLUDED.var_95,
                var_99 = EXCLUDED.var_99,
                var_95_modified = EXCLUDED.var_95_modified,
                var_99_modified = EXCLUDED.var_99_modified,
                expected_shortfall_95 = EXCLUDED.expected_shortfall_95,
                expected_shortfall_99 = EXCLUDED.expected_shortfall_99,
                sharpe_ratio = EXCLUDED.sharpe_ratio,
                sortino_ratio = EXCLUDED.sortino_ratio,
                max_drawdown = EXCLUDED.max_drawdown,
                skewness = EXCLUDED.skewness,
                kurtosis = EXCLUDED.kurtosis,
                sample_size = EXCLUDED.sample_size
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, asdict(metrics))
                    conn.commit()
                    logger.info(f"Inserted risk metrics for {metrics.symbol}")
                    return True
        except Exception as e:
            logger.error(f"Failed to insert risk metrics: {e}")
            return False

    def get_risk_metrics(
        self,
        symbol: str,
        interval: str,
        hours: int = 24
    ) -> List[RiskMetrics]:
        """Get recent risk metrics"""
        query = """
            SELECT * FROM risk_metrics
            WHERE symbol = %s AND interval = %s
              AND time > NOW() - INTERVAL '%s hours'
            ORDER BY time DESC
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, [symbol, interval, hours])
                    rows = cur.fetchall()
                    return [RiskMetrics(**row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query risk metrics: {e}")
            return []

    def get_latest_risk_metrics(
        self,
        symbol: str,
        interval: str
    ) -> Optional[RiskMetrics]:
        """Get most recent risk metrics"""
        metrics = self.get_risk_metrics(symbol, interval, hours=1)
        return metrics[0] if metrics else None

    # ============================================================
    # DERIVATIVES METRICS OPERATIONS
    # ============================================================

    def insert_derivatives_metrics(self, metrics: DerivativesMetrics) -> bool:
        """Insert derivatives metrics into database"""
        query = """
            INSERT INTO derivatives_metrics (
                time, symbol, exchange, funding_rate, funding_rate_annual,
                open_interest, open_interest_value, long_ratio, short_ratio,
                mark_price, index_price
            ) VALUES (
                %(time)s, %(symbol)s, %(exchange)s, %(funding_rate)s, %(funding_rate_annual)s,
                %(open_interest)s, %(open_interest_value)s, %(long_ratio)s, %(short_ratio)s,
                %(mark_price)s, %(index_price)s
            )
            ON CONFLICT (time, symbol, exchange) DO UPDATE SET
                funding_rate = EXCLUDED.funding_rate,
                funding_rate_annual = EXCLUDED.funding_rate_annual,
                open_interest = EXCLUDED.open_interest,
                open_interest_value = EXCLUDED.open_interest_value,
                long_ratio = EXCLUDED.long_ratio,
                short_ratio = EXCLUDED.short_ratio,
                mark_price = EXCLUDED.mark_price,
                index_price = EXCLUDED.index_price
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, asdict(metrics))
                    conn.commit()
                    logger.info(f"Inserted derivatives metrics: {metrics.exchange}")
                    return True
        except Exception as e:
            logger.error(f"Failed to insert derivatives metrics: {e}")
            return False

    def get_derivatives_metrics(
        self,
        symbol: str,
        exchange: Optional[str] = None,
        hours: int = 24
    ) -> List[DerivativesMetrics]:
        """Get recent derivatives metrics"""
        query = """
            SELECT * FROM derivatives_metrics
            WHERE symbol = %s
              AND time > NOW() - INTERVAL '%s hours'
        """
        params = [symbol, hours]

        if exchange:
            query += " AND exchange = %s"
            params.append(exchange)

        query += " ORDER BY time DESC"

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    return [DerivativesMetrics(**row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query derivatives metrics: {e}")
            return []

    def get_latest_derivatives(self, symbol: str) -> List[DerivativesMetrics]:
        """Get latest derivatives metrics from all exchanges"""
        query = """
            SELECT DISTINCT ON (exchange) *
            FROM derivatives_metrics
            WHERE symbol = %s
            ORDER BY exchange, time DESC
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, [symbol])
                    rows = cur.fetchall()
                    return [DerivativesMetrics(**row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query latest derivatives: {e}")
            return []

    # ============================================================
    # TRADING SIGNALS OPERATIONS
    # ============================================================

    def insert_trading_signal(self, signal: TradingSignalData) -> bool:
        """Insert trading signal into database"""
        query = """
            INSERT INTO trading_signals (
                time, symbol, signal_type, strength, direction,
                price, reason, data
            ) VALUES (
                %(time)s, %(symbol)s, %(signal_type)s, %(strength)s, %(direction)s,
                %(price)s, %(reason)s, %(data)s
            )
            ON CONFLICT (time, symbol, signal_type) DO UPDATE SET
                strength = EXCLUDED.strength,
                direction = EXCLUDED.direction,
                price = EXCLUDED.price,
                reason = EXCLUDED.reason,
                data = EXCLUDED.data
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    data_dict = asdict(signal)
                    # Convert data dict to JSON for PostgreSQL JSONB
                    if data_dict['data']:
                        import json
                        data_dict['data'] = json.dumps(data_dict['data'])
                    cur.execute(query, data_dict)
                    conn.commit()
                    logger.info(f"Inserted signal: {signal.signal_type} {signal.strength}")
                    return True
        except Exception as e:
            logger.error(f"Failed to insert trading signal: {e}")
            return False

    def get_trading_signals(
        self,
        symbol: str,
        signal_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[TradingSignalData]:
        """Get recent trading signals"""
        query = """
            SELECT * FROM trading_signals
            WHERE symbol = %s
              AND time > NOW() - INTERVAL '%s hours'
        """
        params = [symbol, hours]

        if signal_type:
            query += " AND signal_type = %s"
            params.append(signal_type)

        query += " ORDER BY time DESC LIMIT %s"
        params.append(limit)

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    return [TradingSignalData(**row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query trading signals: {e}")
            return []

    def get_strong_signals(
        self,
        symbol: str,
        hours: int = 24
    ) -> List[TradingSignalData]:
        """Get strong and very strong signals"""
        query = """
            SELECT * FROM trading_signals
            WHERE symbol = %s
              AND time > NOW() - INTERVAL '%s hours'
              AND strength IN ('STRONG', 'VERY_STRONG')
            ORDER BY time DESC
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, [symbol, hours])
                    rows = cur.fetchall()
                    return [TradingSignalData(**row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query strong signals: {e}")
            return []

    # ============================================================
    # UTILITY METHODS
    # ============================================================

    def get_price_change(
        self,
        symbol: str,
        interval: str,
        hours: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Get price change over period using database function"""
        query = "SELECT * FROM get_price_change(%s, %s, %s)"
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, [symbol, interval, f"{hours} hours"])
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get price change: {e}")
            return None

    def get_volume_stats(
        self,
        symbol: str,
        hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """Get volume statistics using database function"""
        query = "SELECT * FROM get_volume_stats(%s, %s)"
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, [symbol, f"{hours} hours"])
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get volume stats: {e}")
            return None

    def health_check(self) -> bool:
        """Check database connection health"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return cur.fetchone()[0] == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# ============================================================
# EXAMPLE USAGE
# ============================================================

if __name__ == "__main__":
    import asyncio
    from decimal import Decimal

    # Initialize repository
    repo = DatabaseRepository()

    # Check health
    if repo.health_check():
        print("✅ Database connection OK")
    else:
        print("❌ Database connection failed")
        exit(1)

    # Example: Insert candle
    candle = CandleData(
        time=datetime.now(),
        symbol="BTCUSDT",
        interval="1m",
        open=Decimal("92500.00"),
        high=Decimal("92550.00"),
        low=Decimal("92450.00"),
        close=Decimal("92520.00"),
        volume=Decimal("15.5"),
        quote_volume=Decimal("1434300.00"),
        trades=350
    )
    repo.insert_candle(candle)

    # Example: Query recent candles
    candles = repo.get_candles("BTCUSDT", "1m", limit=10)
    print(f"\n📊 Latest {len(candles)} candles:")
    for c in candles[:3]:
        print(f"   {c.time} | Close: ${c.close:,.2f} | Volume: {c.volume:.4f} BTC")

    # Example: Get price change
    change = repo.get_price_change("BTCUSDT", "1m", hours=1)
    if change:
        print(f"\n💹 1-hour price change:")
        print(f"   Current: ${change['current_price']:,.2f}")
        print(f"   Change: {change['change_percent']:.2f}%")

    # Close connections
    repo.close()
    print("\n✅ Repository example complete")
