"""
Update 2025 Bitcoin Data

Download Bitcoin data for 2025 (Jan - Dec 10, 2025) and append to database.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.data.binance_client import BinanceDataClient
import duckdb
from src.shared.config.settings import Settings
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


def main():
    """Download 2025 Bitcoin data."""
    
    # Configuration
    symbol = "BTCUSDT"
    interval = "1h"
    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime.now()  # Up to today
    
    logger.info("=" * 80)
    logger.info("📥 BITCOIN 2025 DATA UPDATE")
    logger.info("=" * 80)
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Interval: {interval}")
    logger.info(f"Start: {start.strftime('%Y-%m-%d')}")
    logger.info(f"End: {end.strftime('%Y-%m-%d')}")
    logger.info("=" * 80)
    
    # Initialize client
    binance = BinanceDataClient()
    
    # Download data
    logger.info("\n🚀 Starting download from Binance...\n")
    
    try:
        df = binance.download_date_range(
            symbol=symbol,
            interval=interval,
            start=start,
            end=end,
            show_progress=True
        )
        
        if df.empty:
            logger.warning("⚠️  No data downloaded")
            return
        
        logger.info(f"\n✅ Downloaded {len(df):,} rows")
        logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # Prepare data for DuckDB
        df['symbol'] = symbol
        df['interval'] = interval
        
        # Reorder columns
        df = df[['timestamp', 'symbol', 'interval', 'open', 'high', 'low', 'close', 'volume']]
        
        # Save to DuckDB
        settings = Settings()
        db_path = Path(settings.STORAGE_PATH) / "bitcoin_market.db"
        
        logger.info(f"\n💾 Appending to DuckDB: {db_path}")
        
        conn = duckdb.connect(str(db_path))
        
        # Check existing data
        existing_count = conn.execute("""
            SELECT COUNT(*) FROM market_data 
            WHERE symbol = ? AND interval = ? AND timestamp >= ?
        """, [symbol, interval, start]).fetchone()[0]
        
        if existing_count > 0:
            logger.info(f"🗑️  Removing {existing_count} existing 2025 rows...")
            conn.execute("""
                DELETE FROM market_data 
                WHERE symbol = ? AND interval = ? AND timestamp >= ?
            """, [symbol, interval, start])
        
        # Insert new data
        logger.info("📝 Inserting new 2025 data...")
        conn.execute("""
            INSERT INTO market_data 
            SELECT * FROM df
        """)
        
        # Verify
        total_count = conn.execute("""
            SELECT COUNT(*) FROM market_data 
            WHERE symbol = ? AND interval = ?
        """, [symbol, interval]).fetchone()[0]
        
        logger.info(f"\n✅ Database updated successfully")
        logger.info(f"Total rows in database: {total_count:,}")
        
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
        logger.info("📊 FINAL DATABASE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Earliest: {result[0]}")
        logger.info(f"Latest: {result[1]}")
        logger.info(f"Total Rows: {result[2]:,}")
        logger.info("=" * 80)
        
        conn.close()
        
        logger.info("\n🎉 Update complete!")
        
    except Exception as e:
        logger.error(f"\n❌ Update failed: {e}")
        raise


if __name__ == "__main__":
    main()
