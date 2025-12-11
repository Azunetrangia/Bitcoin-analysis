"""
Download Historical Data from Binance
Fetch real BTC/USDT historical data and save to Parquet.
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
import os
from pathlib import Path

def download_binance_klines(symbol='BTCUSDT', interval='1h', days=30):
    """
    Download historical klines from Binance.
    
    Args:
        symbol: Trading pair (default: BTCUSDT)
        interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d)
        days: Number of days to fetch
    """
    
    print(f"📥 Downloading {days} days of {symbol} {interval} data from Binance...")
    
    # Calculate timestamps
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    # Binance API endpoint
    url = "https://api.binance.com/api/v3/klines"
    
    all_klines = []
    current_start = start_ms
    
    while current_start < end_ms:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_start,
            'endTime': end_ms,
            'limit': 1000  # Max limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            klines = response.json()
            
            if not klines:
                break
            
            all_klines.extend(klines)
            
            # Update start time for next batch
            current_start = klines[-1][0] + 1
            
            print(f"   Fetched {len(klines)} candles... (Total: {len(all_klines)})")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            break
    
    if not all_klines:
        print("❌ No data fetched!")
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
    
    print(f"✅ Downloaded {len(df)} candles")
    print(f"   Date range: {df['time'].min()} → {df['time'].max()}")
    print(f"   Price range: ${df['close'].min():,.2f} → ${df['close'].max():,.2f}")
    
    return df


def save_to_parquet(df, symbol='BTCUSDT', interval='1h'):
    """Save DataFrame to Parquet file"""
    
    # Create data directory
    data_dir = Path('data/hot')
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # File path
    filepath = data_dir / f"{symbol}_{interval}.parquet"
    
    # Save
    df.to_parquet(filepath, engine='pyarrow', compression='snappy', index=False)
    
    print(f"💾 Saved to: {filepath}")
    print(f"   File size: {filepath.stat().st_size / 1024:.1f} KB")
    
    return filepath


if __name__ == "__main__":
    print("=" * 60)
    print("📊 Binance Historical Data Downloader")
    print("=" * 60)
    
    # Download different intervals
    intervals = [
        ('1h', 30),   # 1 hour candles, 30 days
        ('4h', 90),   # 4 hour candles, 90 days
        ('1d', 365),  # Daily candles, 1 year
    ]
    
    for interval, days in intervals:
        print(f"\n📥 Downloading {interval} data ({days} days)...")
        
        df = download_binance_klines(
            symbol='BTCUSDT',
            interval=interval,
            days=days
        )
        
        if df is not None:
            filepath = save_to_parquet(df, 'BTCUSDT', interval)
            print(f"✅ Success: {interval}")
        else:
            print(f"❌ Failed: {interval}")
        
        print("-" * 60)
    
    print("\n" + "=" * 60)
    print("✅ Download complete!")
    print("=" * 60)
    print("\n📁 Data saved to: data/hot/")
    print("\n🔄 Restart Streamlit to see data in other pages")
    print("=" * 60)
