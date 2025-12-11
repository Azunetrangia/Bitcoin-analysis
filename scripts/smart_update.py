"""
Smart Update Bitcoin Data

Download only NEW Bitcoin data since last update and append to database.
This script checks the latest timestamp in database and only downloads new data.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.data.binance_client import BinanceDataClient
import duckdb
from src.shared.config.settings import Settings
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


def main():
    """Smart update - download only new data."""
    
    # Configuration
    symbol = "BTCUSDT"
    interval = "1h"
    
    logger.info("=" * 80)
    logger.info("📥 BITCOIN SMART DATA UPDATE")
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
        return
    
    latest_timestamp = result[0]
    logger.info(f"Latest data in database: {latest_timestamp}")
    
    # Calculate download range
    # Start from 1 hour after latest timestamp (to avoid duplicates)
    if isinstance(latest_timestamp, str):
        start = datetime.fromisoformat(latest_timestamp) + timedelta(hours=1)
    else:
        start = latest_timestamp + timedelta(hours=1)
    end = datetime.now()
    
    # Check if update is needed
    if start >= end:
        logger.info("✅ Database is up-to-date. No new data to download.")
        conn.close()
        return
    
    hours_behind = (end - start).total_seconds() / 3600
    logger.info(f"Database is {hours_behind:.1f} hours behind")
    logger.info(f"Download range: {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 80)
    
    # Initialize client
    binance = BinanceDataClient()
    
    # Download new data
    logger.info("\n🚀 Downloading new data from Binance...\n")
    
    try:
        df = binance.download_date_range(
            symbol=symbol,
            interval=interval,
            start=start,
            end=end,
            show_progress=True
        )
        
        if df.empty:
            logger.info("✅ No new data available (market may be closed or data not ready yet)")
            conn.close()
            return
        
        logger.info(f"\n✅ Downloaded {len(df):,} new rows")
        logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # Prepare data for DuckDB
        df['symbol'] = symbol
        df['interval'] = interval
        
        # Reorder columns
        df = df[['timestamp', 'symbol', 'interval', 'open', 'high', 'low', 'close', 'volume']]
        
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
        
        logger.info("\n🎉 Smart update complete!")
        
    except Exception as e:
        logger.error(f"\n❌ Update failed: {e}")
        conn.close()
        raise


if __name__ == "__main__":
    main()
