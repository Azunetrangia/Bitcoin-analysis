"""
Auto Update Market Data
Automatically fetch new data from last timestamp to now.
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def get_last_timestamp(symbol='BTCUSDT', interval='1h'):
    """Get the last timestamp from existing parquet file"""
    filepath = Path(f'data/hot/{symbol}_{interval}.parquet')
    
    if not filepath.exists():
        logger.info(f"No existing data found for {symbol} {interval}")
        return None
    
    try:
        df = pd.read_parquet(filepath)
        if 'time' in df.columns:
            last_time = pd.to_datetime(df['time']).max()
        elif 'timestamp' in df.columns:
            last_time = pd.to_datetime(df['timestamp']).max()
        else:
            logger.error(f"No time column found in {filepath}")
            return None
        
        logger.info(f"Last timestamp in {symbol} {interval}: {last_time}")
        return last_time
    
    except Exception as e:
        logger.error(f"Error reading parquet: {e}")
        return None


def fetch_new_data(symbol='BTCUSDT', interval='1h', start_time=None):
    """
    Fetch new data from Binance starting from start_time to now.
    
    Args:
        symbol: Trading pair (BTCUSDT)
        interval: Candle interval (1h, 4h, 1d)
        start_time: Start datetime (if None, fetch last 30 days)
    
    Returns:
        DataFrame with new data or None
    """
    
    url = "https://api.binance.com/api/v3/klines"
    
    # If no start_time, default to 30 days ago
    if start_time is None:
        start_time = datetime.now() - timedelta(days=30)
    
    # Convert to timestamp
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(datetime.now().timestamp() * 1000)
    
    # Check if we need to fetch (at least 1 hour difference)
    time_diff = (datetime.now() - start_time).total_seconds() / 3600
    if time_diff < 1 and interval == '1h':
        logger.info(f"Data is up-to-date (less than 1 hour old)")
        return None
    
    logger.info(f"📥 Fetching new {symbol} {interval} data from {start_time} to now...")
    
    all_klines = []
    current_start = start_ms
    
    while current_start < end_ms:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_start,
            'endTime': end_ms,
            'limit': 1000
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            klines = response.json()
            
            if not klines:
                break
            
            all_klines.extend(klines)
            current_start = klines[-1][0] + 1
            
            logger.info(f"   Fetched {len(klines)} candles... (Total: {len(all_klines)})")
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            break
    
    if not all_klines:
        logger.info("No new data to fetch")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(all_klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Convert data types
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    
    for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
        df[col] = df[col].astype(float)
    
    df['trades'] = df['trades'].astype(int)
    
    # Select and rename columns
    df = df[[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'quote_volume', 'trades'
    ]].rename(columns={'timestamp': 'time'})
    
    df['symbol'] = symbol
    df['interval'] = interval
    
    logger.info(f"✅ Fetched {len(df)} new candles")
    
    return df


def merge_and_save(new_df, symbol='BTCUSDT', interval='1h'):
    """
    Merge new data with existing parquet and save.
    
    Args:
        new_df: New DataFrame to append
        symbol: Trading pair
        interval: Candle interval
    """
    
    filepath = Path(f'data/hot/{symbol}_{interval}.parquet')
    
    if filepath.exists():
        # Load existing data
        existing_df = pd.read_parquet(filepath)
        
        # Merge (concat and remove duplicates)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        
        # Remove duplicates based on 'time' column
        time_col = 'time' if 'time' in combined_df.columns else 'timestamp'
        combined_df = combined_df.drop_duplicates(subset=[time_col], keep='last')
        
        # Sort by time
        combined_df = combined_df.sort_values(time_col).reset_index(drop=True)
        
        logger.info(f"📊 Total candles after merge: {len(combined_df)} (added {len(new_df)} new)")
    else:
        # No existing file, use new data
        combined_df = new_df
        logger.info(f"📊 Creating new file with {len(combined_df)} candles")
    
    # Save to parquet
    filepath.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_parquet(filepath, engine='pyarrow', compression='snappy', index=False)
    
    logger.info(f"💾 Saved to: {filepath}")
    logger.info(f"   File size: {filepath.stat().st_size / 1024:.1f} KB")
    logger.info(f"   Date range: {combined_df['time'].min()} → {combined_df['time'].max()}")


def auto_update_all_intervals():
    """
    Auto-update all configured intervals.
    Called at startup or on schedule.
    """
    
    logger.info("=" * 60)
    logger.info("🔄 AUTO UPDATE - Checking for new data...")
    logger.info("=" * 60)
    
    intervals = ['1h', '4h', '1d']
    symbol = 'BTCUSDT'
    
    updated_count = 0
    
    for interval in intervals:
        logger.info(f"\n📊 Checking {symbol} {interval}...")
        
        # Get last timestamp
        last_time = get_last_timestamp(symbol, interval)
        
        # Fetch new data
        new_df = fetch_new_data(symbol, interval, last_time)
        
        if new_df is not None and len(new_df) > 0:
            # Merge and save
            merge_and_save(new_df, symbol, interval)
            updated_count += 1
            logger.info(f"✅ Updated {interval}")
        else:
            logger.info(f"⏭️  No update needed for {interval}")
        
        logger.info("-" * 60)
    
    logger.info("\n" + "=" * 60)
    if updated_count > 0:
        logger.info(f"✅ AUTO UPDATE COMPLETE - {updated_count} intervals updated")
    else:
        logger.info("ℹ️  All data is up-to-date")
    logger.info("=" * 60)
    
    return updated_count


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run auto update
    auto_update_all_intervals()
