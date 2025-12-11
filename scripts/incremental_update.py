"""
Incremental Update Bitcoin Data

Download latest Bitcoin data using direct Binance API and append to database.
This is a simplified version that works with current data.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import requests
import pandas as pd
from time import sleep

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import duckdb
from src.shared.config.settings import Settings
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


def fetch_binance_klines(symbol: str, interval: str, start_time: int, end_time: int, limit: int = 1000):
    """
    Fetch klines from Binance API.
    
    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        interval: Timeframe (e.g., 1h)
        start_time: Start timestamp in milliseconds
        end_time: End timestamp in milliseconds
        limit: Number of records per request (max 1000)
    
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
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch data from Binance: {e}")
        return []


def main():
    """Incremental update - download only new data."""
    
    # Configuration
    symbol = "BTCUSDT"
    interval = "1h"
    
    logger.info("=" * 80)
    logger.info("📥 BITCOIN INCREMENTAL UPDATE")
    logger.info("=" * 80)
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Interval: {interval}")
    
    # Connect to database
    settings = Settings()
    db_path = Path(settings.STORAGE_PATH) / "bitcoin_market.db"
    
    if not db_path.exists():
        logger.error("❌ Database not found. Run initial data download first.")
        return
    
    conn = duckdb.connect(str(db_path))
    
    # Get latest timestamp in database
    result = conn.execute("""
        SELECT MAX(timestamp) as latest
        FROM market_data
        WHERE symbol = ? AND interval = ?
    """, [symbol, interval]).fetchone()
    
    if not result[0]:
        logger.error("❌ No existing data found. Run initial data download first.")
        conn.close()
        return
    
    latest_timestamp = result[0]
    logger.info(f"Latest data in database: {latest_timestamp}")
    
    # Calculate download range
    if isinstance(latest_timestamp, str):
        start_dt = datetime.fromisoformat(latest_timestamp) + timedelta(hours=1)
    else:
        start_dt = latest_timestamp + timedelta(hours=1)
    
    end_dt = datetime.now()
    
    # Check if update is needed
    if start_dt >= end_dt:
        logger.info("✅ Database is up-to-date. No new data to download.")
        conn.close()
        return
    
    hours_behind = (end_dt - start_dt).total_seconds() / 3600
    logger.info(f"Database is {hours_behind:.1f} hours behind")
    logger.info(f"Download range: {start_dt.strftime('%Y-%m-%d %H:%M')} to {end_dt.strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 80)
    
    # Convert to milliseconds for Binance API
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    
    # Fetch data from Binance
    logger.info("\n🚀 Fetching new data from Binance...\n")
    
    try:
        all_klines = []
        current_start = start_ms
        
        while current_start < end_ms:
            klines = fetch_binance_klines(symbol, interval, current_start, end_ms, limit=1000)
            
            if not klines:
                break
            
            all_klines.extend(klines)
            logger.info(f"Fetched {len(klines)} records (total: {len(all_klines)})")
            
            # Update start time for next request
            current_start = klines[-1][0] + 1
            
            # Respect rate limits
            sleep(0.5)
        
        if not all_klines:
            logger.info("✅ No new data available")
            conn.close()
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(all_klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Process data
        df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        df['symbol'] = symbol
        df['interval'] = interval
        
        # Select and reorder columns
        df = df[['timestamp', 'symbol', 'interval', 'open', 'high', 'low', 'close', 'volume']]
        
        # Remove any duplicates (shouldn't happen but just in case)
        df = df.drop_duplicates(subset=['timestamp'], keep='last')
        
        # Filter out timestamps that already exist in database
        existing_timestamps = conn.execute("""
            SELECT timestamp FROM market_data
            WHERE symbol = ? AND interval = ?
        """, [symbol, interval]).fetchdf()
        
        if not existing_timestamps.empty:
            df = df[~df['timestamp'].isin(existing_timestamps['timestamp'])]
        
        if df.empty:
            logger.info("\n✅ No new unique data to add (all records already exist)")
            conn.close()
            return
        
        logger.info(f"\n✅ Downloaded {len(df):,} new unique rows")
        logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # Insert new data
        logger.info(f"\n💾 Appending {len(df):,} rows to database...")
        
        conn.execute("""
            INSERT INTO market_data 
            SELECT * FROM df
        """)
        
        # Verify
        total_count = conn.execute("""
            SELECT COUNT(*) FROM market_data 
            WHERE symbol = ? AND interval = ?
        """, [symbol, interval]).fetchone()[0]
        
        new_latest = conn.execute("""
            SELECT MAX(timestamp) FROM market_data 
            WHERE symbol = ? AND interval = ?
        """, [symbol, interval]).fetchone()[0]
        
        logger.info(f"✅ Database updated successfully")
        logger.info(f"Total rows in database: {total_count:,}")
        logger.info(f"Latest timestamp: {new_latest}")
        
        # Show summary
        result = conn.execute(f"""
            SELECT 
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest,
                COUNT(*) as total_rows
            FROM market_data
            WHERE symbol = '{symbol}' AND interval = '{interval}'
        """).fetchone()
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 DATABASE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Earliest: {result[0]}")
        logger.info(f"Latest: {result[1]}")
        logger.info(f"Total Rows: {result[2]:,}")
        logger.info(f"New Rows Added: {len(df):,}")
        logger.info("=" * 80)
        
        conn.close()
        
        logger.info("\n🎉 Incremental update complete!")
        
    except Exception as e:
        logger.error(f"\n❌ Update failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        conn.close()
        raise


if __name__ == "__main__":
    main()
