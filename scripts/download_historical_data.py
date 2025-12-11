"""
Download Historical Bitcoin Data (2020-Present)

This script downloads BTCUSDT 1h data from 2020 to present and stores it in DuckDB.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.data.binance_client import BinanceDataClient
from src.infrastructure.storage.duckdb_query_engine import DuckDBQueryEngine
from src.shared.config.settings import Settings
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


def main():
    """Download 2020-2025 Bitcoin data."""
    
    # Configuration
    symbol = "BTCUSDT"
    interval = "1h"
    start = datetime(2020, 1, 1, 0, 0, 0)
    end = datetime.now()
    
    logger.info("=" * 80)
    logger.info("📥 BITCOIN HISTORICAL DATA DOWNLOAD")
    logger.info("=" * 80)
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Interval: {interval}")
    logger.info(f"Start: {start.strftime('%Y-%m-%d')}")
    logger.info(f"End: {end.strftime('%Y-%m-%d')}")
    logger.info(f"Estimated rows: ~{(end - start).days * 24:,}")
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
        
        logger.info(f"\n💾 Saving to DuckDB: {db_path}")
        
        db = DuckDBQueryEngine(str(db_path))
        
        # Create table if not exists
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                timestamp TIMESTAMP,
                symbol VARCHAR,
                interval VARCHAR,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                PRIMARY KEY (timestamp, symbol, interval)
            )
        """)
        
        # Clear existing data first (to avoid duplicates)
        logger.info("🗑️  Clearing existing data...")
        db.conn.execute(f"""
            DELETE FROM market_data 
            WHERE symbol = '{symbol}' 
            AND interval = '{interval}'
        """)
        
        # Insert new data
        logger.info("📝 Inserting new data...")
        db.conn.execute("""
            INSERT INTO market_data 
            SELECT * FROM df
        """)
        
        # Verify
        count = db.conn.execute("""
            SELECT COUNT(*) FROM market_data 
            WHERE symbol = ? AND interval = ?
        """, [symbol, interval]).fetchone()[0]
        
        logger.info(f"\n✅ Successfully saved {count:,} rows to database")
        
        # Show summary
        result = db.conn.execute(f"""
            SELECT 
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest,
                COUNT(*) as total_rows,
                MIN(close) as min_price,
                MAX(close) as max_price,
                AVG(volume) as avg_volume
            FROM market_data
            WHERE symbol = '{symbol}' AND interval = '{interval}'
        """).fetchone()
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 DATABASE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Earliest: {result[0]}")
        logger.info(f"Latest: {result[1]}")
        logger.info(f"Total Rows: {result[2]:,}")
        logger.info(f"Price Range: ${result[3]:,.2f} - ${result[4]:,.2f}")
        logger.info(f"Avg Volume: {result[5]:,.2f}")
        logger.info("=" * 80)
        
        db.close()
        
        logger.info("\n🎉 Download complete!")
        
    except Exception as e:
        logger.error(f"\n❌ Download failed: {e}")
        raise


if __name__ == "__main__":
    main()
