"""
Simple API Server using Parquet files (no database required)
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import sys
import requests

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Bitcoin Market Intelligence API (Parquet)",
    description="API using Parquet files - No database required",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event - Auto update data
@app.on_event("startup")
async def startup_event():
    """Run on server startup - auto-update market data"""
    logger.info("🚀 Starting Bitcoin Market Intelligence API...")
    
    try:
        from services.auto_update_data import auto_update_all_intervals
        
        logger.info("🔄 Running auto-update on startup...")
        updated_count = auto_update_all_intervals()
        
        if updated_count > 0:
            logger.info(f"✅ Auto-update complete: {updated_count} intervals updated")
            # Clear cache to reload updated data
            global _data_cache
            _data_cache.clear()
        else:
            logger.info("ℹ️  Data is already up-to-date")
    
    except Exception as e:
        logger.warning(f"⚠️  Auto-update failed (will use existing data): {e}")
    
    logger.info("✅ Server ready!")


# Data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "hot"

# Cache for loaded data
_data_cache = {}


def get_live_price(symbol: str = "BTCUSDT") -> float:
    """Fetch live price from Binance API"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        price = float(data['price'])
        logger.info(f"Fetched live {symbol} price: ${price:,.2f}")
        return price
    except Exception as e:
        logger.error(f"Error fetching live price for {symbol}: {e}")
        # Fallback to latest parquet price if API fails
        return None


def load_parquet_data(symbol: str = "BTCUSDT", interval: str = "1h"):
    """Load data from Parquet file"""
    cache_key = f"{symbol}_{interval}"
    
    if cache_key in _data_cache:
        return _data_cache[cache_key]
    
    file_path = DATA_DIR / f"{symbol}_{interval}.parquet"
    
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return None
    
    try:
        df = pd.read_parquet(file_path)
        # Use 'time' column if exists, else 'timestamp'
        time_col = 'time' if 'time' in df.columns else 'timestamp'
        df['timestamp'] = pd.to_datetime(df[time_col])
        _data_cache[cache_key] = df
        logger.info(f"Loaded {len(df)} rows from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return None


@app.get("/")
async def root():
    return {
        "message": "Bitcoin Market Intelligence API (Parquet)",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "parquet-files",
        "timestamp": datetime.now()
    }


@app.post("/api/v1/refresh-data")
async def refresh_data():
    """
    Manually trigger data refresh.
    Fetches new candles from Binance and updates parquet files.
    """
    try:
        from services.auto_update_data import auto_update_all_intervals
        
        logger.info("🔄 Manual refresh triggered...")
        updated_count = auto_update_all_intervals()
        
        # Clear cache to reload updated data
        global _data_cache
        _data_cache.clear()
        
        return {
            "success": True,
            "message": f"Updated {updated_count} intervals",
            "timestamp": datetime.now()
        }
    
    except Exception as e:
        logger.error(f"Refresh failed: {e}")
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")


@app.get("/api/v1/candles/{symbol}")
async def get_candles(
    symbol: str,
    interval: str = Query("1h"),
    limit: int = Query(100, ge=1, le=1000),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    """Get candlestick data from Parquet"""
    df = load_parquet_data(symbol.upper(), interval)
    
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol} {interval}")
    
    # Filter by time range
    if start_time:
        df = df[df['timestamp'] >= start_time]
    if end_time:
        df = df[df['timestamp'] <= end_time]
    
    # Limit results
    df = df.tail(limit)
    
    # Convert to JSON
    result = []
    for _, row in df.iterrows():
        result.append({
            "time": row['timestamp'].isoformat(),
            "symbol": symbol.upper(),
            "interval": interval,
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close']),
            "volume": float(row['volume']),
            "quote_volume": float(row.get('quote_volume', row['volume'] * row['close'])),
            "trades": int(row.get('trades', 0))
        })
    
    return result


@app.get("/api/v1/market-data/")
async def get_market_data(
    symbol: str = Query("BTCUSDT"),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    interval: str = Query("1h"),
    limit: int = Query(500)
):
    """Get market data for calculations"""
    df = load_parquet_data(symbol.upper(), interval)
    
    if df is None or df.empty:
        # Try other intervals
        for alt_interval in ["1h", "4h", "1d"]:
            df = load_parquet_data(symbol.upper(), alt_interval)
            if df is not None and not df.empty:
                interval = alt_interval
                break
    
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No data available")
    
    # Filter by time
    if start:
        df = df[df['timestamp'] >= start]
    if end:
        df = df[df['timestamp'] <= end]
    
    df = df.tail(limit)
    
    result = []
    for _, row in df.iterrows():
        result.append({
            "timestamp": row['timestamp'].isoformat(),
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close']),
            "volume": float(row['volume'])
        })
    
    return {"data": result, "count": len(result)}


@app.get("/api/v1/analysis/regimes")
async def get_regimes(
    symbol: str = Query("BTCUSDT"),
    start: datetime = Query(...),
    end: datetime = Query(...),
    interval: str = Query("1h")
):
    """Calculate regime classification"""
    df = load_parquet_data(symbol.upper(), interval)
    
    if df is None or df.empty:
        # Try other intervals
        for alt_interval in ["1h", "4h", "1d"]:
            df = load_parquet_data(symbol.upper(), alt_interval)
            if df is not None and not df.empty:
                break
    
    if df is None or df.empty or len(df) < 30:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data. Need 30+ points, found {len(df) if df is not None else 0}"
        )
    
    # Convert timezone-aware datetimes to naive
    start_naive = start.replace(tzinfo=None) if start.tzinfo else start
    end_naive = end.replace(tzinfo=None) if end.tzinfo else end
    
    # Filter by date range
    df = df[(df['timestamp'] >= start_naive) & (df['timestamp'] <= end_naive)]
    
    if len(df) < 30:
        raise HTTPException(status_code=400, detail=f"Need at least 30 candles in range, found {len(df)}")
    
    # Calculate indicators
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(20).std()
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    
    # Classify regimes using trend + volatility
    regimes = []
    regime_names = {0: "High Volatility", 1: "Bearish", 2: "Sideways", 3: "Bullish"}
    regime_colors = {0: "#f59e0b", 1: "#ef4444", 2: "#6b7280", 3: "#22c55e"}
    
    for idx, row in df.iterrows():
        if pd.isna(row['volatility']) or pd.isna(row['sma_20']):
            regime = 2
        else:
            vol_threshold = df['volatility'].quantile(0.75)
            
            # High volatility regime
            if row['volatility'] > vol_threshold:
                regime = 0
            # Bullish: price above SMA20 and positive returns
            elif row['close'] > row['sma_20'] and row['returns'] > 0:
                regime = 3
            # Bearish: price below SMA20 and negative returns
            elif row['close'] < row['sma_20'] and row['returns'] < 0:
                regime = 1
            # Sideways: everything else
            else:
                regime = 2
        
        regimes.append({
            'timestamp': row['timestamp'].isoformat(),
            'regime': regime,
            'regime_name': regime_names[regime],
            'regime_color': regime_colors[regime],
            'close': float(row['close']),
            'volatility': float(row['volatility']) if not pd.isna(row['volatility']) else None
        })
    
    # Calculate distribution
    regime_counts = pd.Series([r['regime'] for r in regimes]).value_counts()
    total = len(regimes)
    distribution = {
        regime_names[k]: {
            'count': int(v),
            'percentage': float(v / total * 100),
            'color': regime_colors[k]
        } for k, v in regime_counts.items()
    }
    
    # Current regime
    current = regimes[-1] if regimes else None
    
    return {
        'regimes': regimes,
        'stats': {
            'total_periods': len(regimes),
            'distribution': distribution,
            'current_regime': current['regime_name'] if current else 'Unknown',
            'current_regime_color': current['regime_color'] if current else '#6b7280'
        }
    }


@app.get("/api/v1/summary/{symbol}")
async def get_summary(symbol: str, interval: str = Query("1h")):
    """Get market summary with latest metrics"""
    df = load_parquet_data(symbol.upper(), interval)
    
    if df is None or df.empty:
        for alt_interval in ["1h", "4h", "1d"]:
            df = load_parquet_data(symbol.upper(), alt_interval)
            if df is not None and not df.empty:
                break
    
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No data available")
    
    # Get latest candle
    latest = df.iloc[-1]
    
    # Calculate 24h change (last 24 rows for 1h data)
    lookback = min(24, len(df) - 1)
    prev = df.iloc[-lookback-1]
    
    return {
        "symbol": symbol.upper(),
        "timestamp": latest['timestamp'].isoformat(),
        "price": {
            "time": latest['timestamp'].isoformat(),
            "open": float(latest['open']),
            "high": float(latest['high']),
            "low": float(latest['low']),
            "close": float(latest['close']),
            "volume": float(latest['volume'])
        },
        "price_change_24h": {
            "current_price": float(latest['close']),
            "previous_price": float(prev['close']),
            "change_amount": float(latest['close'] - prev['close']),
            "change_percent": float((latest['close'] - prev['close']) / prev['close'] * 100)
        }
    }


@app.get("/api/v1/analysis/indicators")
async def get_indicators(
    symbol: str = Query("BTCUSDT"),
    start: datetime = Query(...),
    end: datetime = Query(...),
    interval: str = Query("1h"),
    limit: int = Query(1000, le=2000)  # Max 2000 points
):
    """Calculate technical indicators"""
    df = load_parquet_data(symbol.upper(), interval)
    
    if df is None or df.empty:
        for alt_interval in ["1h", "4h", "1d"]:
            df = load_parquet_data(symbol.upper(), alt_interval)
            if df is not None and not df.empty:
                break
    
    if df is None or df.empty or len(df) < 50:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data. Need 50+ points, found {len(df) if df is not None else 0}"
        )
    
    # Convert timezone-aware datetimes to naive (remove timezone info)
    start_naive = start.replace(tzinfo=None) if start.tzinfo else start
    end_naive = end.replace(tzinfo=None) if end.tzinfo else end
    
    # Filter by date range FIRST to reduce data
    df = df[(df['timestamp'] >= start_naive) & (df['timestamp'] <= end_naive)]
    
    # Take latest N points if still too many
    if len(df) > limit:
        df = df.tail(limit)
    
    if len(df) < 50:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough data in date range. Found {len(df)}, need 50+"
        )
    
    logger.info(f"Processing {len(df)} candles for indicators")
    
    # Calculate indicators
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['ema_12'] = df['close'].ewm(span=12).mean()
    df['ema_26'] = df['close'].ewm(span=26).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
    
    # Convert to response
    indicators = []
    for idx, row in df.iterrows():
        indicators.append({
            'timestamp': row['timestamp'].isoformat(),
            'close': float(row['close']),
            'high': float(row['high']),
            'low': float(row['low']),
            'open': float(row['open']),
            'volume': float(row['volume']),
            'sma_20': float(row['sma_20']) if not pd.isna(row['sma_20']) else None,
            'sma_50': float(row['sma_50']) if not pd.isna(row['sma_50']) else None,
            'ema_12': float(row['ema_12']) if not pd.isna(row['ema_12']) else None,
            'ema_26': float(row['ema_26']) if not pd.isna(row['ema_26']) else None,
            'rsi': float(row['rsi']) if not pd.isna(row['rsi']) else None,
            'macd': float(row['macd']) if not pd.isna(row['macd']) else None,
            'macd_signal': float(row['macd_signal']) if not pd.isna(row['macd_signal']) else None,
            'macd_histogram': float(row['macd_histogram']) if not pd.isna(row['macd_histogram']) else None,
            'bb_upper': float(row['bb_upper']) if not pd.isna(row['bb_upper']) else None,
            'bb_middle': float(row['bb_middle']) if not pd.isna(row['bb_middle']) else None,
            'bb_lower': float(row['bb_lower']) if not pd.isna(row['bb_lower']) else None
        })
    
    return {'indicators': indicators}


@app.get("/api/v1/analysis/risk")
async def get_risk_metrics(
    symbol: str = Query("BTCUSDT"),
    start: datetime = Query(...),
    end: datetime = Query(...),
    interval: str = Query("1h")
):
    """Calculate risk metrics: VaR, Sharpe, Drawdown"""
    df = load_parquet_data(symbol.upper(), interval)
    
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No data found")
    
    # Convert timezone-aware datetimes to naive
    start_naive = start.replace(tzinfo=None) if start.tzinfo else start
    end_naive = end.replace(tzinfo=None) if end.tzinfo else end
    
    # Filter by date range
    df = df[(df['timestamp'] >= start_naive) & (df['timestamp'] <= end_naive)]
    
    if len(df) < 30:
        raise HTTPException(status_code=400, detail=f"Need at least 30 candles, found {len(df)}")
    
    # Calculate returns
    df['returns'] = df['close'].pct_change()
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    
    # Calculate cumulative returns for drawdown
    df['cumulative'] = (1 + df['returns']).cumprod()
    df['running_max'] = df['cumulative'].expanding().max()
    df['drawdown'] = (df['cumulative'] - df['running_max']) / df['running_max']
    
    # VaR calculations (95% and 99% confidence)
    returns_clean = df['returns'].dropna()
    var_95 = np.percentile(returns_clean, 5)
    var_99 = np.percentile(returns_clean, 1)
    
    # Sharpe Ratio (annualized, assuming 365*24 hourly periods per year)
    periods_per_year = 365 * 24 if interval == "1h" else 365
    mean_return = returns_clean.mean()
    std_return = returns_clean.std()
    sharpe_ratio = (mean_return / std_return) * np.sqrt(periods_per_year) if std_return > 0 else 0
    
    # Max Drawdown
    max_drawdown = df['drawdown'].min()
    max_drawdown_idx = df['drawdown'].idxmin()
    max_drawdown_date = df.loc[max_drawdown_idx, 'timestamp'].isoformat() if pd.notna(max_drawdown_idx) else None
    
    # Volatility (annualized)
    volatility = std_return * np.sqrt(periods_per_year)
    
    # Current metrics
    current_price = float(df['close'].iloc[-1])
    price_change_pct = float(((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100)
    
    # Historical data for charts
    risk_data = []
    for idx, row in df.iterrows():
        risk_data.append({
            'timestamp': row['timestamp'].isoformat(),
            'close': float(row['close']),
            'returns': float(row['returns']) if not pd.isna(row['returns']) else None,
            'drawdown': float(row['drawdown']) if not pd.isna(row['drawdown']) else None,
            'cumulative': float(row['cumulative']) if not pd.isna(row['cumulative']) else None
        })
    
    return {
        'metrics': {
            'var_95': float(var_95) * 100,  # Convert to percentage
            'var_99': float(var_99) * 100,
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown) * 100,
            'max_drawdown_date': max_drawdown_date,
            'volatility': float(volatility) * 100,
            'current_price': current_price,
            'price_change_pct': price_change_pct,
            'total_periods': len(df),
        },
        'data': risk_data
    }


@app.get("/api/v1/decisions/{symbol}")
async def get_investment_decision(symbol: str, interval: str = Query("1h")):
    """Get investment decision based on multiple factors"""
    df = load_parquet_data(symbol.upper(), interval)
    
    if df is None or df.empty:
        for alt_interval in ["1h", "4h", "1d"]:
            df = load_parquet_data(symbol.upper(), alt_interval)
            if df is not None and not df.empty:
                break
    
    if df is None or df.empty or len(df) < 30:
        raise HTTPException(status_code=404, detail="Insufficient data for decision")
    
    # Calculate indicators
    df['returns'] = df['close'].pct_change()
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Get latest values
    latest = df.iloc[-1]
    
    # Decision logic
    signals = []
    score = 0
    
    # Trend signal
    if latest['close'] > latest['sma_20'] > latest['sma_50']:
        signals.append({"factor": "Trend", "signal": "Bullish", "weight": 30})
        score += 30
    elif latest['close'] < latest['sma_20'] < latest['sma_50']:
        signals.append({"factor": "Trend", "signal": "Bearish", "weight": -30})
        score -= 30
    else:
        signals.append({"factor": "Trend", "signal": "Neutral", "weight": 0})
    
    # RSI signal
    if latest['rsi'] < 30:
        signals.append({"factor": "RSI", "signal": "Oversold (Buy)", "weight": 25})
        score += 25
    elif latest['rsi'] > 70:
        signals.append({"factor": "RSI", "signal": "Overbought (Sell)", "weight": -25})
        score -= 25
    else:
        signals.append({"factor": "RSI", "signal": "Neutral", "weight": 0})
    
    # Volatility signal
    vol = df['returns'].std()
    if vol > 0.03:
        signals.append({"factor": "Volatility", "signal": "High Risk", "weight": -15})
        score -= 15
    elif vol < 0.01:
        signals.append({"factor": "Volatility", "signal": "Low Risk", "weight": 15})
        score += 15
    else:
        signals.append({"factor": "Volatility", "signal": "Normal", "weight": 0})
    
    # Overall recommendation
    if score > 40:
        recommendation = "Strong Buy"
        confidence = "High"
    elif score > 15:
        recommendation = "Buy"
        confidence = "Medium"
    elif score > -15:
        recommendation = "Hold"
        confidence = "Low"
    elif score > -40:
        recommendation = "Sell"
        confidence = "Medium"
    else:
        recommendation = "Strong Sell"
        confidence = "High"
    
    return {
        "symbol": symbol.upper(),
        "timestamp": latest['timestamp'].isoformat(),
        "decision": recommendation,
        "confidence": confidence,
        "score": score,
        "signals": signals,
        "current_price": float(latest['close']),
        "rsi": float(latest['rsi']) if not pd.isna(latest['rsi']) else None
    }


@app.get("/api/v1/signals/regime")
async def get_regime_signal(
    symbol: str = Query(default="BTCUSDT", description="Trading pair symbol"),
    interval: str = Query(default="1h", description="Timeframe (1h/4h/1d)")
):
    """
    Get current market regime using HMM.
    
    Returns regime classification (Bull/Bear/Sideways) with confidence.
    """
    try:
        from src.models.regime_detector import RegimeDetector
        
        # Load data
        df = load_parquet_data(symbol.upper(), interval)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="No data available")
        
        # Initialize and train detector
        detector = RegimeDetector(n_states=3, lookback_days=90)
        
        # Train on historical data (use last 360 candles for training)
        train_size = min(360, int(len(df) * 0.7))
        detector.train(df.iloc[-train_size:])
        
        # Predict current regime
        result = detector.predict_current_regime(df.iloc[-30:])  # Use last 30 candles for context
        
        # Get latest price for context
        latest = df.iloc[-1]
        
        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "timestamp": latest['timestamp'].isoformat(),
            "current_price": float(latest['close']),
            "regime": result['regime'],
            "probability": float(result['probability']),
            "confidence": result['confidence'],
            "state_probabilities": {
                "Bear": float(result['all_probs'][1]) if len(result['all_probs']) > 1 else 0,
                "Sideways": float(result['all_probs'][0]) if len(result['all_probs']) > 0 else 0,
                "Bull": float(result['all_probs'][2]) if len(result['all_probs']) > 2 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting regime: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/signals/kama")
async def get_kama_signals(
    symbol: str = Query(default="BTCUSDT", description="Trading pair symbol"),
    interval: str = Query(default="1h", description="Timeframe (1h/4h/1d)"),
    period: int = Query(default=10, description="KAMA period")
):
    """
    Get KAMA (Kaufman Adaptive Moving Average) signals.
    
    Returns KAMA values, crossover signals, and trading recommendations.
    """
    try:
        from src.indicators.adaptive import calculate_kama, generate_kama_signals, calculate_atr
        
        # Load data
        df = load_parquet_data(symbol.upper(), interval)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="No data available")
        
        # Calculate KAMA
        df['kama'] = calculate_kama(df['close'], n=period)
        df['atr'] = calculate_atr(df, period=14)
        
        # Generate signals
        df_signals = generate_kama_signals(df, kama_period=period)
        
        # Get latest values
        latest = df_signals.iloc[-1]
        prev = df_signals.iloc[-2] if len(df_signals) > 1 else latest
        
        # Determine signal
        signal = "NEUTRAL"
        if latest['kama_cross'] == 1:
            signal = "BUY"
        elif latest['kama_cross'] == -1:
            signal = "SELL"
        elif latest['signal'] == 1:
            signal = "BULLISH"
        elif latest['signal'] == -1:
            signal = "BEARISH"
        
        # Distance from KAMA
        distance_pct = ((latest['close'] - latest['kama']) / latest['kama']) * 100
        
        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "timestamp": latest['timestamp'].isoformat(),
            "current_price": float(latest['close']),
            "kama_value": float(latest['kama']),
            "signal": signal,
            "distance_from_kama": float(distance_pct),
            "atr": float(latest['atr']),
            "atr_pct": float(latest['atr_pct']),
            "trend": "Bullish" if latest['signal'] == 1 else "Bearish" if latest['signal'] == -1 else "Neutral",
            "recent_cross": "Golden" if latest['kama_cross'] == 1 else "Death" if latest['kama_cross'] == -1 else "None"
        }
        
    except Exception as e:
        logger.error(f"Error getting KAMA signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/signals/onchain")
async def get_onchain_data():
    """
    Get on-chain metrics from free sources.
    
    Returns market cap, funding rate, active addresses, etc.
    """
    try:
        from src.data.free_onchain import get_comprehensive_onchain_data
        
        # Get all on-chain data
        data = get_comprehensive_onchain_data()
        
        return {
            "timestamp": data['timestamp'],
            "market_cap": {
                "value": data['mvrv']['value'],
                "signal": data['mvrv']['signal'],
                "description": data['mvrv']['description']
            },
            "funding_rate": {
                "rate": data['funding_rate']['funding_rate'],
                "rate_pct": data['funding_rate']['funding_rate_pct'],
                "annual_rate_pct": data['funding_rate']['annual_rate_pct'],
                "signal": data['funding_rate']['signal'],
                "warning": data['funding_rate']['warning'],
                "mark_price": data['funding_rate']['mark_price']
            },
            "network_health": {
                "active_addresses": data['active_addresses'],
                "mempool_size": data['mempool_size']
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting on-chain data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/signals/comprehensive")
async def get_comprehensive_signals(
    symbol: str = Query(default="BTCUSDT", description="Trading pair symbol"),
    interval: str = Query(default="1h", description="Timeframe (1h/4h/1d)")
):
    """
    Get comprehensive trading signals combining regime, KAMA, and on-chain data.
    
    Returns complete market analysis with trading recommendation.
    """
    try:
        # Get signals directly (don't call other endpoints to avoid Query issues)
        from src.models.regime_detector import RegimeDetector
        from src.indicators.adaptive import calculate_kama, generate_kama_signals, calculate_atr
        from src.data.free_onchain import get_comprehensive_onchain_data
        
        # Load data
        df = load_parquet_data(symbol.upper(), interval)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="No data available")
        
        # Get regime
        detector = RegimeDetector(n_states=3, lookback_days=90)
        train_size = min(360, int(len(df) * 0.7))
        detector.train(df.iloc[-train_size:])
        regime = detector.predict_current_regime(df.iloc[-30:])
        
        # Get KAMA
        df['kama'] = calculate_kama(df['close'], n=10)
        df['atr'] = calculate_atr(df, period=14)
        df_signals = generate_kama_signals(df, kama_period=10)
        latest = df_signals.iloc[-1]
        
        # Get on-chain data
        onchain_data = get_comprehensive_onchain_data()
        
        # Calculate composite score
        score = 0
        factors = []
        
        # Regime factor (30% weight)
        if regime['regime'] == 'Bull' and regime['probability'] > 0.7:
            score += 30
            factors.append({"name": "Regime", "signal": "Bull (High Confidence)", "weight": 30})
        elif regime['regime'] == 'Bull':
            score += 15
            factors.append({"name": "Regime", "signal": "Bull (Medium Confidence)", "weight": 15})
        elif regime['regime'] == 'Bear' and regime['probability'] > 0.7:
            score -= 30
            factors.append({"name": "Regime", "signal": "Bear (High Confidence)", "weight": -30})
        elif regime['regime'] == 'Bear':
            score -= 15
            factors.append({"name": "Regime", "signal": "Bear (Medium Confidence)", "weight": -15})
        else:
            factors.append({"name": "Regime", "signal": "Sideways", "weight": 0})
        
        # KAMA factor (30% weight)
        kama_signal = "NEUTRAL"
        if latest['kama_cross'] == 1:
            score += 30
            factors.append({"name": "KAMA", "signal": "Golden Cross", "weight": 30})
            kama_signal = "BUY"
        elif latest['kama_cross'] == -1:
            score -= 30
            factors.append({"name": "KAMA", "signal": "Death Cross", "weight": -30})
            kama_signal = "SELL"
        elif latest['signal'] == 1:
            score += 15
            factors.append({"name": "KAMA", "signal": "Bullish Trend", "weight": 15})
            kama_signal = "BULLISH"
        elif latest['signal'] == -1:
            score -= 15
            factors.append({"name": "KAMA", "signal": "Bearish Trend", "weight": -15})
            kama_signal = "BEARISH"
        else:
            factors.append({"name": "KAMA", "signal": "Neutral", "weight": 0})
        
        # Funding rate factor (20% weight)
        if onchain_data['funding_rate']['signal'] == 'EXTREME_SHORT':
            score += 20
            factors.append({"name": "Funding", "signal": "Extreme Short (Squeeze Risk)", "weight": 20})
        elif onchain_data['funding_rate']['signal'] == 'EXTREME_LONG':
            score -= 20
            factors.append({"name": "Funding", "signal": "Extreme Long (Squeeze Risk)", "weight": -20})
        elif onchain_data['funding_rate']['signal'] == 'NEUTRAL':
            score += 5
            factors.append({"name": "Funding", "signal": "Neutral (Healthy)", "weight": 5})
        
        # Market cap factor (20% weight)
        if onchain_data['mvrv']['signal'] == 'ACCUMULATION':
            score += 20
            factors.append({"name": "Market Cap", "signal": "Accumulation Zone", "weight": 20})
        elif onchain_data['mvrv']['signal'] == 'OVERVALUED':
            score -= 10
            factors.append({"name": "Market Cap", "signal": "Overvalued", "weight": -10})
        else:
            factors.append({"name": "Market Cap", "signal": "Fair Value", "weight": 0})
        
        # Generate recommendation
        if score >= 60:
            recommendation = "STRONG BUY"
            confidence = "High"
        elif score >= 30:
            recommendation = "BUY"
            confidence = "Medium"
        elif score >= -30:
            recommendation = "HOLD"
            confidence = "Low"
        elif score >= -60:
            recommendation = "SELL"
            confidence = "Medium"
        else:
            recommendation = "STRONG SELL"
            confidence = "High"
        
        # Get live price (fallback to parquet if API fails)
        live_price = get_live_price(symbol.upper())
        current_price = live_price if live_price is not None else float(latest['close'])
        
        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "timestamp": datetime.now().isoformat(),
            "current_price": current_price,
            "recommendation": recommendation,
            "confidence": confidence,
            "composite_score": score,
            "regime": {
                "regime": regime['regime'],
                "probability": regime['probability'],
                "confidence": regime['confidence']
            },
            "kama": {
                "value": float(latest['kama']),
                "signal": kama_signal,
                "distance_pct": float(((latest['close'] - latest['kama']) / latest['kama']) * 100)
            },
            "onchain": {
                "funding_rate": onchain_data['funding_rate']['signal'],
                "market_cap_signal": onchain_data['mvrv']['signal']
            },
            "factors": factors
        }
        
    except Exception as e:
        logger.error(f"Error getting comprehensive signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 Bitcoin API Server (Parquet Mode)")
    print("=" * 60)
    print("📍 Host: 0.0.0.0")
    print("🔌 Port: 8000")
    print("📖 Docs: http://localhost:8000/docs")
    print("📁 Data: Using Parquet files (no database needed)")
    print("=" * 60)
    
    uvicorn.run(
        "api_server_parquet:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
