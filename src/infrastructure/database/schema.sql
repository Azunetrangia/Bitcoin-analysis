-- Bitcoin Market Intelligence Database Schema
-- Author: Bitcoin Market Intelligence Team
-- Created: 2025-12-10
-- Database: PostgreSQL 15+ with TimescaleDB extension
-- Purpose: Store real-time and historical market data for analysis

-- ============================================================
-- ENABLE TIMESCALEDB EXTENSION
-- ============================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- TABLE: candles
-- Purpose: Store OHLCV candlestick data from WebSocket
-- ============================================================

CREATE TABLE IF NOT EXISTS candles (
    time            TIMESTAMPTZ NOT NULL,
    symbol          VARCHAR(20) NOT NULL,
    interval        VARCHAR(10) NOT NULL,
    open            NUMERIC(20, 8) NOT NULL,
    high            NUMERIC(20, 8) NOT NULL,
    low             NUMERIC(20, 8) NOT NULL,
    close           NUMERIC(20, 8) NOT NULL,
    volume          NUMERIC(20, 8) NOT NULL,
    quote_volume    NUMERIC(20, 8) NOT NULL,
    trades          INTEGER NOT NULL,
    PRIMARY KEY (time, symbol, interval)
);

-- Convert to hypertable (TimescaleDB)
SELECT create_hypertable('candles', 'time', if_not_exists => TRUE);

-- Create indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_candles_symbol_time 
    ON candles (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_candles_interval 
    ON candles (interval, time DESC);

-- Add retention policy (keep 1 year of 1-minute data)
SELECT add_retention_policy('candles', INTERVAL '1 year', if_not_exists => TRUE);

-- Add compression policy (compress data older than 7 days)
ALTER TABLE candles SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, interval'
);
SELECT add_compression_policy('candles', INTERVAL '7 days', if_not_exists => TRUE);

-- ============================================================
-- TABLE: trades
-- Purpose: Store individual trade data from WebSocket
-- ============================================================

CREATE TABLE IF NOT EXISTS trades (
    time            TIMESTAMPTZ NOT NULL,
    symbol          VARCHAR(20) NOT NULL,
    trade_id        BIGINT NOT NULL,
    price           NUMERIC(20, 8) NOT NULL,
    quantity        NUMERIC(20, 8) NOT NULL,
    is_buyer_maker  BOOLEAN NOT NULL,  -- TRUE = sell, FALSE = buy
    PRIMARY KEY (time, symbol, trade_id)
);

-- Convert to hypertable
SELECT create_hypertable('trades', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_trades_symbol_time 
    ON trades (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_large 
    ON trades (quantity DESC, time DESC) WHERE quantity > 0.1;

-- Add retention policy (keep 30 days of trades)
SELECT add_retention_policy('trades', INTERVAL '30 days', if_not_exists => TRUE);

-- Add compression
ALTER TABLE trades SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol'
);
SELECT add_compression_policy('trades', INTERVAL '2 days', if_not_exists => TRUE);

-- ============================================================
-- TABLE: risk_metrics
-- Purpose: Store calculated risk metrics (VaR, Sharpe, etc.)
-- ============================================================

CREATE TABLE IF NOT EXISTS risk_metrics (
    time                    TIMESTAMPTZ NOT NULL,
    symbol                  VARCHAR(20) NOT NULL,
    interval                VARCHAR(10) NOT NULL,
    mean_return             NUMERIC(15, 8),
    volatility              NUMERIC(15, 8),
    var_95                  NUMERIC(15, 8),
    var_99                  NUMERIC(15, 8),
    var_95_modified         NUMERIC(15, 8),
    var_99_modified         NUMERIC(15, 8),
    expected_shortfall_95   NUMERIC(15, 8),
    expected_shortfall_99   NUMERIC(15, 8),
    sharpe_ratio            NUMERIC(15, 8),
    sortino_ratio           NUMERIC(15, 8),
    max_drawdown            NUMERIC(15, 8),
    skewness                NUMERIC(15, 8),
    kurtosis                NUMERIC(15, 8),
    sample_size             INTEGER,
    PRIMARY KEY (time, symbol, interval)
);

-- Convert to hypertable
SELECT create_hypertable('risk_metrics', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_risk_metrics_symbol_time 
    ON risk_metrics (symbol, time DESC);

-- Retention: keep 90 days
SELECT add_retention_policy('risk_metrics', INTERVAL '90 days', if_not_exists => TRUE);

-- ============================================================
-- TABLE: derivatives_metrics
-- Purpose: Store derivatives market data (funding, OI, etc.)
-- ============================================================

CREATE TABLE IF NOT EXISTS derivatives_metrics (
    time                TIMESTAMPTZ NOT NULL,
    symbol              VARCHAR(20) NOT NULL,
    exchange            VARCHAR(20) NOT NULL,
    funding_rate        NUMERIC(15, 8),
    funding_rate_annual NUMERIC(15, 8),
    open_interest       NUMERIC(25, 2),
    open_interest_value NUMERIC(25, 8),
    long_ratio          NUMERIC(5, 4),
    short_ratio         NUMERIC(5, 4),
    mark_price          NUMERIC(20, 8),
    index_price         NUMERIC(20, 8),
    PRIMARY KEY (time, symbol, exchange)
);

-- Convert to hypertable
SELECT create_hypertable('derivatives_metrics', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_derivatives_symbol_time 
    ON derivatives_metrics (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_derivatives_exchange 
    ON derivatives_metrics (exchange, time DESC);

-- Retention: keep 180 days
SELECT add_retention_policy('derivatives_metrics', INTERVAL '180 days', if_not_exists => TRUE);

-- ============================================================
-- TABLE: trading_signals
-- Purpose: Store generated trading signals
-- ============================================================

CREATE TABLE IF NOT EXISTS trading_signals (
    time            TIMESTAMPTZ NOT NULL,
    symbol          VARCHAR(20) NOT NULL,
    signal_type     VARCHAR(50) NOT NULL,
    strength        VARCHAR(20) NOT NULL,
    direction       VARCHAR(10) NOT NULL,
    price           NUMERIC(20, 8) NOT NULL,
    reason          TEXT NOT NULL,
    data            JSONB,
    PRIMARY KEY (time, symbol, signal_type)
);

-- Convert to hypertable
SELECT create_hypertable('trading_signals', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_signals_symbol_time 
    ON trading_signals (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_signals_type 
    ON trading_signals (signal_type, time DESC);
CREATE INDEX IF NOT EXISTS idx_signals_direction 
    ON trading_signals (direction, time DESC);

-- Retention: keep 1 year
SELECT add_retention_policy('trading_signals', INTERVAL '1 year', if_not_exists => TRUE);

-- ============================================================
-- CONTINUOUS AGGREGATES (Pre-computed views for performance)
-- ============================================================

-- 5-minute candles from 1-minute data
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS time,
    symbol,
    '5m' AS interval,
    FIRST(open, time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS volume,
    SUM(quote_volume) AS quote_volume,
    SUM(trades) AS trades
FROM candles
WHERE interval = '1m'
GROUP BY time_bucket('5 minutes', time), symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('candles_5m',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE
);

-- 15-minute candles
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_15m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('15 minutes', time) AS time,
    symbol,
    '15m' AS interval,
    FIRST(open, time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS volume,
    SUM(quote_volume) AS quote_volume,
    SUM(trades) AS trades
FROM candles
WHERE interval = '1m'
GROUP BY time_bucket('15 minutes', time), symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('candles_15m',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '15 minutes',
    schedule_interval => INTERVAL '15 minutes',
    if_not_exists => TRUE
);

-- Hourly candles
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS time,
    symbol,
    '1h' AS interval,
    FIRST(open, time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS volume,
    SUM(quote_volume) AS quote_volume,
    SUM(trades) AS trades
FROM candles
WHERE interval = '1m'
GROUP BY time_bucket('1 hour', time), symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('candles_1h',
    start_offset => INTERVAL '4 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- ============================================================
-- VIEWS: Convenient query interfaces
-- ============================================================

-- Latest derivatives summary
CREATE OR REPLACE VIEW latest_derivatives AS
SELECT DISTINCT ON (symbol, exchange)
    time,
    symbol,
    exchange,
    funding_rate,
    funding_rate_annual,
    open_interest,
    long_ratio,
    short_ratio
FROM derivatives_metrics
ORDER BY symbol, exchange, time DESC;

-- Latest risk metrics
CREATE OR REPLACE VIEW latest_risk_metrics AS
SELECT DISTINCT ON (symbol, interval)
    time,
    symbol,
    interval,
    var_95,
    var_95_modified,
    var_99,
    var_99_modified,
    expected_shortfall_95,
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    skewness,
    kurtosis
FROM risk_metrics
ORDER BY symbol, interval, time DESC;

-- Recent signals (last 24 hours)
CREATE OR REPLACE VIEW recent_signals AS
SELECT
    time,
    symbol,
    signal_type,
    strength,
    direction,
    price,
    reason
FROM trading_signals
WHERE time > NOW() - INTERVAL '24 hours'
ORDER BY time DESC;

-- ============================================================
-- FUNCTIONS: Utility functions for queries
-- ============================================================

-- Get price change over period
CREATE OR REPLACE FUNCTION get_price_change(
    p_symbol VARCHAR,
    p_interval VARCHAR,
    p_period INTERVAL
)
RETURNS TABLE(
    current_price NUMERIC,
    previous_price NUMERIC,
    change_amount NUMERIC,
    change_percent NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH latest AS (
        SELECT close
        FROM candles
        WHERE symbol = p_symbol AND interval = p_interval
        ORDER BY time DESC
        LIMIT 1
    ),
    previous AS (
        SELECT close
        FROM candles
        WHERE symbol = p_symbol 
          AND interval = p_interval
          AND time <= NOW() - p_period
        ORDER BY time DESC
        LIMIT 1
    )
    SELECT
        l.close AS current_price,
        p.close AS previous_price,
        l.close - p.close AS change_amount,
        ((l.close - p.close) / p.close * 100) AS change_percent
    FROM latest l, previous p;
END;
$$ LANGUAGE plpgsql;

-- Get volume statistics
CREATE OR REPLACE FUNCTION get_volume_stats(
    p_symbol VARCHAR,
    p_period INTERVAL
)
RETURNS TABLE(
    total_volume NUMERIC,
    avg_volume NUMERIC,
    max_volume NUMERIC,
    trade_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        SUM(volume)::NUMERIC AS total_volume,
        AVG(volume)::NUMERIC AS avg_volume,
        MAX(volume)::NUMERIC AS max_volume,
        COUNT(*)::BIGINT AS trade_count
    FROM candles
    WHERE symbol = p_symbol
      AND time > NOW() - p_period;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- COMMENTS & DOCUMENTATION
-- ============================================================

COMMENT ON TABLE candles IS 'Real-time OHLCV candlestick data from WebSocket streams';
COMMENT ON TABLE trades IS 'Individual trade executions for volume analysis';
COMMENT ON TABLE risk_metrics IS 'Calculated risk metrics (VaR, Sharpe, Sortino, etc.)';
COMMENT ON TABLE derivatives_metrics IS 'Derivatives market data (funding rates, OI, long/short)';
COMMENT ON TABLE trading_signals IS 'Generated trading signals with reasoning';

COMMENT ON COLUMN candles.interval IS 'Timeframe: 1m, 5m, 15m, 1h, 4h, 1d';
COMMENT ON COLUMN trades.is_buyer_maker IS 'TRUE = sell order (maker sells), FALSE = buy order';
COMMENT ON COLUMN risk_metrics.var_95_modified IS 'Cornish-Fisher adjusted VaR for fat tails';
COMMENT ON COLUMN derivatives_metrics.funding_rate IS '8-hour funding rate (positive = longs pay shorts)';
COMMENT ON COLUMN trading_signals.strength IS 'WEAK, MODERATE, STRONG, VERY_STRONG';

-- ============================================================
-- GRANTS (Adjust as needed for your security model)
-- ============================================================

-- Create read-only user for dashboards
-- CREATE USER btc_readonly WITH PASSWORD 'your_password';
-- GRANT CONNECT ON DATABASE btc_intelligence TO btc_readonly;
-- GRANT USAGE ON SCHEMA public TO btc_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO btc_readonly;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO btc_readonly;

-- ============================================================
-- SAMPLE QUERIES
-- ============================================================

-- Get latest 100 candles
-- SELECT * FROM candles WHERE symbol = 'BTCUSDT' AND interval = '1m' ORDER BY time DESC LIMIT 100;

-- Get current funding rates across exchanges
-- SELECT * FROM latest_derivatives WHERE symbol = 'BTCUSDT';

-- Get recent high-risk periods
-- SELECT * FROM risk_metrics WHERE symbol = 'BTCUSDT' AND ABS(var_95_modified) > 0.03 ORDER BY time DESC;

-- Get strong trading signals from last 24 hours
-- SELECT * FROM recent_signals WHERE strength IN ('STRONG', 'VERY_STRONG');

-- Get price change over last hour
-- SELECT * FROM get_price_change('BTCUSDT', '1m', '1 hour');

-- ============================================================
-- END OF SCHEMA
-- ============================================================
