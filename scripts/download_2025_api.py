"""
Download 2025 Bitcoin Data via Binance REST API

Uses /api/v3/klines endpoint for fast download without ZIP archives.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import requests
from tqdm import tqdm
import duckdb

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.shared.config.settings import Settings
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


def download_klines(symbol: str, interval: str, start_time: int, end_time: int, limit: int = 1000):
    """
    Download klines from Binance REST API.
    
    Args:
        symbol: Trading pair (BTCUSDT)
        interval: Time interval (1h)
        start_time: Start timestamp in milliseconds
        end_time: End timestamp in milliseconds
        limit: Max rows per request (1000 max)
    
    Returns:
        List of klines
    """
    url = "https://api.binance.com/api/v3/klines"
    
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time,
        "endTime": end_time,
        "limit": limit
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.json()


def main():
    """Download 2025 Bitcoin data via API."""
    
    # Configuration
    symbol = "BTCUSDT"
    interval = "1h"
    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime.now()
    
    logger.info("=" * 80)
    logger.info("📥 BITCOIN 2025 DATA UPDATE (via REST API)")
    logger.info("=" * 80)
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Interval: {interval}")
    logger.info(f"Start: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"End: {end.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # Convert to milliseconds
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    
    # Calculate expected rows (1 hour per row)
    expected_rows = int((end - start).total_seconds() / 3600)
    logger.info(f"\nExpected rows: ~{expected_rows:,}")
    
    # Download in batches
    logger.info("\n🚀 Downloading from Binance API...\n")
    
    all_data = []
    current_start = start_ms
    batch_size = 1000  # API limit
    
    with tqdm(total=expected_rows, desc="Downloading") as pbar:
        while current_start < end_ms:
            try:
                # Download batch
                klines = download_klines(symbol, interval, current_start, end_ms, batch_size)
                
                if not klines:
                    break
                
                all_data.extend(klines)
                pbar.update(len(klines))
                
                # Update start time for next batch (last timestamp + 1ms)
                current_start = int(klines[-1][0]) + 1
                
                # If we got less than batch_size, we're done
                if len(klines) < batch_size:
                    break
                
            except Exception as e:
                logger.error(f"❌ Download failed: {e}")
                break
    
    if not all_data:
        logger.warning("⚠️  No data downloaded")
        return
    
    logger.info(f"\n✅ Downloaded {len(all_data):,} rows")
    
    # Convert to DataFrame
    logger.info("\n📊 Converting to DataFrame...")
    
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    
    # Convert timestamp from milliseconds to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Convert price columns to float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    # Add metadata
    df['symbol'] = symbol
    df['interval'] = interval
    
    # Select columns
    df = df[['timestamp', 'symbol', 'interval', 'open', 'high', 'low', 'close', 'volume']]
    
    logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    logger.info(f"Price range: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")
    
    # Save to DuckDB
    settings = Settings()
    db_path = Path(settings.STORAGE_PATH) / "bitcoin_market.db"
    
    logger.info(f"\n💾 Updating DuckDB: {db_path}")
    
    conn = duckdb.connect(str(db_path))
    
    # Check existing data
    existing_count = conn.execute("""
        SELECT COUNT(*) FROM market_data 
        WHERE symbol = ? AND interval = ? AND timestamp >= ?
    """, [symbol, interval, df['timestamp'].min()]).fetchone()[0]
    
    if existing_count > 0:
        logger.info(f"🗑️  Removing {existing_count:,} existing rows from {df['timestamp'].min()}...")
        conn.execute("""
            DELETE FROM market_data 
            WHERE symbol = ? AND interval = ? AND timestamp >= ?
        """, [symbol, interval, df['timestamp'].min()])
    
    # Insert new data
    logger.info(f"📝 Inserting {len(df):,} new rows...")
    conn.execute("INSERT INTO market_data SELECT * FROM df")
    
    # Verify
    total_count = conn.execute("""
        SELECT COUNT(*) FROM market_data 
        WHERE symbol = ? AND interval = ?
    """, [symbol, interval]).fetchone()[0]
    
    logger.info(f"\n✅ Database updated successfully")
    logger.info(f"Total rows in database: {total_count:,}")
    
    # Show final summary
    result = conn.execute(f"""
        SELECT 
            MIN(timestamp) as earliest,
            MAX(timestamp) as latest,
            COUNT(*) as total_rows,
            MIN(close) as min_price,
            MAX(close) as max_price
        FROM market_data
        WHERE symbol = '{symbol}' AND interval = '{interval}'
    """).fetchone()
    
    logger.info("\n" + "=" * 80)
    logger.info("📊 FINAL DATABASE SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Earliest: {result[0]}")
    logger.info(f"Latest: {result[1]}")
    logger.info(f"Total Rows: {result[2]:,}")
    logger.info(f"Price Range: ${result[3]:,.2f} - ${result[4]:,.2f}")
    logger.info("=" * 80)
    
    conn.close()
    
    logger.info("\n🎉 Update complete!")


if __name__ == "__main__":
    main()
