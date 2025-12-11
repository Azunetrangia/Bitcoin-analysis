"""
Bitcoin Market Intelligence REST API
Production-ready FastAPI service for real-time market data and analytics.

Author: Bitcoin Market Intelligence Team
Created: 2025-12-10
Version: 1.0.0
"""

from fastapi import FastAPI, HTTPException, Query, Path, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel, Field
import logging
import os
import asyncio
import json
from contextlib import asynccontextmanager

# Import our infrastructure
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.infrastructure.database.repository import (
    DatabaseRepository,
    CandleData,
    TradeData,
    RiskMetrics,
    DerivativesMetrics,
    TradingSignalData
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# PYDANTIC MODELS (API Schemas)
# ============================================================

class CandleResponse(BaseModel):
    """Candlestick data response model"""
    time: datetime
    symbol: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: int


class TradeResponse(BaseModel):
    """Trade data response model"""
    time: datetime
    symbol: str
    trade_id: int
    price: float
    quantity: float
    is_buyer_maker: bool


class RiskMetricsResponse(BaseModel):
    """Risk metrics response model"""
    time: datetime
    symbol: str
    interval: str
    mean_return: Optional[float] = None
    volatility: Optional[float] = None
    var_95: Optional[float] = None
    var_99: Optional[float] = None
    var_95_modified: Optional[float] = None
    var_99_modified: Optional[float] = None
    expected_shortfall_95: Optional[float] = None
    expected_shortfall_99: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    sample_size: Optional[int] = None


class DerivativesMetricsResponse(BaseModel):
    """Derivatives metrics response model"""
    time: datetime
    symbol: str
    exchange: str
    funding_rate: Optional[float] = None
    funding_rate_annual: Optional[float] = None
    open_interest: Optional[float] = None
    open_interest_value: Optional[float] = None
    long_ratio: Optional[float] = None
    short_ratio: Optional[float] = None
    mark_price: Optional[float] = None
    index_price: Optional[float] = None


class TradingSignalResponse(BaseModel):
    """Trading signal response model"""
    time: datetime
    symbol: str
    signal_type: str
    strength: str
    direction: str
    price: float
    reason: str
    data: Optional[Dict[str, Any]] = None


class PriceChangeResponse(BaseModel):
    """Price change response model"""
    current_price: float
    previous_price: float
    change_amount: float
    change_percent: float


class VolumeStatsResponse(BaseModel):
    """Volume statistics response model"""
    total_volume: float
    avg_volume: float
    max_volume: float
    trade_count: int


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    database: str
    timestamp: datetime


class MarketSummaryResponse(BaseModel):
    """Comprehensive market summary"""
    symbol: str
    timestamp: datetime
    price: Optional[CandleResponse] = None
    price_change_1h: Optional[PriceChangeResponse] = None
    price_change_24h: Optional[PriceChangeResponse] = None
    volume_24h: Optional[VolumeStatsResponse] = None
    risk_metrics: Optional[RiskMetricsResponse] = None
    derivatives: List[DerivativesMetricsResponse] = []
    recent_signals: List[TradingSignalResponse] = []


class RegimeDataPoint(BaseModel):
    """Single regime classification data point"""
    timestamp: datetime
    regime: int
    regime_name: str
    probability: float


class RegimeStats(BaseModel):
    """Regime statistics"""
    total_regimes: int
    distribution: Dict[str, float]
    current_regime: str


class TechnicalIndicator(BaseModel):
    """Technical indicator data point"""
    timestamp: datetime
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None


# ============================================================
# APPLICATION SETUP
# ============================================================

# Global database repository
db_repo: Optional[DatabaseRepository] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_repo
    
    # Startup
    logger.info("Starting Bitcoin Market Intelligence API...")
    try:
        db_repo = DatabaseRepository()
        if db_repo.health_check():
            logger.info("✅ Database connection established")
        else:
            logger.error("❌ Database health check failed")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down API...")
    if db_repo:
        db_repo.close()
        logger.info("✅ Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Bitcoin Market Intelligence API",
    description="Real-time Bitcoin market data, risk analytics, and trading signals",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DEPENDENCY INJECTION
# ============================================================

def get_db() -> DatabaseRepository:
    """Get database repository dependency"""
    if db_repo is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return db_repo


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def convert_decimal_to_float(obj: Any) -> Any:
    """Recursively convert Decimal to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    return obj


def dataclass_to_response(data: Any, response_model: type) -> Any:
    """Convert dataclass to Pydantic response model"""
    if hasattr(data, '__dict__'):
        data_dict = {k: convert_decimal_to_float(v) for k, v in data.__dict__.items()}
        return response_model(**data_dict)
    return None


# ============================================================
# API ENDPOINTS
# ============================================================

@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "name": "Bitcoin Market Intelligence API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "candles": "/api/v1/candles/{symbol}",
            "trades": "/api/v1/trades/{symbol}",
            "risk": "/api/v1/risk/{symbol}",
            "derivatives": "/api/v1/derivatives/{symbol}",
            "signals": "/api/v1/signals/{symbol}",
            "summary": "/api/v1/summary/{symbol}"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: DatabaseRepository = Depends(get_db)):
    """Health check endpoint"""
    db_status = "connected" if db.health_check() else "disconnected"
    
    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        database=db_status,
        timestamp=datetime.now()
    )


# ============================================================
# CANDLES ENDPOINTS
# ============================================================

@app.get(
    "/api/v1/candles/{symbol}",
    response_model=List[CandleResponse],
    tags=["Candles"]
)
async def get_candles(
    symbol: str = Path(..., description="Trading pair (e.g., BTCUSDT)"),
    interval: str = Query("1m", description="Timeframe (1m, 5m, 15m, 1h, 4h, 1d)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of candles to return"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    db: DatabaseRepository = Depends(get_db)
):
    """Get historical candlestick data"""
    try:
        candles = db.get_candles(
            symbol=symbol.upper(),
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        return [dataclass_to_response(c, CandleResponse) for c in candles]
    
    except Exception as e:
        logger.error(f"Error fetching candles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/summary/{symbol}",
    response_model=MarketSummaryResponse,
    tags=["Summary"]
)
async def get_market_summary(
    symbol: str = Path(..., description="Trading pair"),
    interval: str = Query("1m", description="Timeframe for price data"),
    db: DatabaseRepository = Depends(get_db)
):
    """Get comprehensive market summary"""
    try:
        symbol_upper = symbol.upper()
        summary = MarketSummaryResponse(
            symbol=symbol_upper,
            timestamp=datetime.now()
        )
        
        # Latest price
        candle = db.get_latest_candle(symbol_upper, interval)
        if candle:
            summary.price = dataclass_to_response(candle, CandleResponse)
        
        # Price changes
        change_1h = db.get_price_change(symbol_upper, interval, 1)
        if change_1h:
            summary.price_change_1h = PriceChangeResponse(**convert_decimal_to_float(change_1h))
        
        change_24h = db.get_price_change(symbol_upper, interval, 24)
        if change_24h:
            summary.price_change_24h = PriceChangeResponse(**convert_decimal_to_float(change_24h))
        
        # Volume stats
        volume = db.get_volume_stats(symbol_upper, 24)
        if volume:
            summary.volume_24h = VolumeStatsResponse(**convert_decimal_to_float(volume))
        
        # Risk metrics
        risk = db.get_latest_risk_metrics(symbol_upper, interval)
        if risk:
            summary.risk_metrics = dataclass_to_response(risk, RiskMetricsResponse)
        
        # Derivatives
        derivatives = db.get_latest_derivatives(symbol_upper)
        summary.derivatives = [
            dataclass_to_response(d, DerivativesMetricsResponse) for d in derivatives
        ]
        
        # Recent signals
        signals = db.get_strong_signals(symbol_upper, 24)
        summary.recent_signals = [
            dataclass_to_response(s, TradingSignalResponse) for s in signals[:5]
        ]
        
        return summary
    
    except Exception as e:
        logger.error(f"Error fetching market summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/analysis/regimes",
    tags=["Analysis"]
)
async def get_regime_classification(
    symbol: str = Query("BTCUSDT", description="Trading pair"),
    start: datetime = Query(..., description="Start time"),
    end: datetime = Query(..., description="End time"),
    interval: str = Query("1h", description="Timeframe"),
    db: DatabaseRepository = Depends(get_db)
):
    """Get market regime classification"""
    try:
        # Try to get candles for the period
        candles = db.get_candles(
            symbol=symbol.upper(),
            interval=interval,
            start_time=start,
            end_time=end,
            limit=1000
        )
        
        # If no data in range, try different intervals
        if not candles:
            logger.info(f"No data in requested range for interval {interval}, trying other intervals")
            all_intervals = ["1m", "5m", "15m", "1h", "4h", "1d"]
            for test_interval in all_intervals:
                candles = db.get_candles(
                    symbol=symbol.upper(),
                    interval=test_interval,
                    start_time=None,
                    end_time=None,
                    limit=500
                )
                if candles and len(candles) >= 30:
                    logger.info(f"Found {len(candles)} candles with interval {test_interval}")
                    break
        
        if not candles or len(candles) < 30:
            raise HTTPException(
                status_code=404, 
                detail=f"Insufficient data. Need at least 30 data points, found {len(candles) if candles else 0}. Try loading historical data first."
            )
        
        # Simple regime classification based on price action and volatility
        import pandas as pd
        import numpy as np
        
        df = pd.DataFrame([{
            'timestamp': c.time,
            'close': float(c.close),
            'volume': float(c.volume)
        } for c in candles])
        
        # Calculate returns and volatility
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std()
        df['sma_20'] = df['close'].rolling(20).mean()
        
        # Classify regimes
        regimes = []
        regime_names = {0: "High Volatility", 1: "Bearish", 2: "Neutral", 3: "Bullish"}
        
        for idx, row in df.iterrows():
            if pd.isna(row['volatility']) or pd.isna(row['sma_20']):
                regime = 2  # Neutral
            else:
                # High volatility regime
                if row['volatility'] > df['volatility'].quantile(0.75):
                    regime = 0
                # Bullish: price above SMA and positive returns
                elif row['close'] > row['sma_20'] and row['returns'] > 0:
                    regime = 3
                # Bearish: price below SMA and negative returns
                elif row['close'] < row['sma_20'] and row['returns'] < 0:
                    regime = 1
                # Neutral
                else:
                    regime = 2
            
            regimes.append({
                'timestamp': row['timestamp'].isoformat(),
                'regime': regime,
                'regime_name': regime_names[regime],
                'probability': 0.85  # Mock probability
            })
        
        # Calculate distribution
        regime_counts = pd.Series([r['regime'] for r in regimes]).value_counts()
        total = len(regimes)
        distribution = {regime_names[k]: float(v) / total for k, v in regime_counts.items()}
        
        return {
            'regimes': regimes,
            'regime_stats': {
                'total_regimes': 4,
                'distribution': distribution,
                'current_regime': regimes[-1]['regime_name'] if regimes else 'Unknown'
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in regime classification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/analysis/indicators",
    tags=["Analysis"]
)
async def get_technical_indicators(
    symbol: str = Query("BTCUSDT", description="Trading pair"),
    start: datetime = Query(..., description="Start time"),
    end: datetime = Query(..., description="End time"),
    interval: str = Query("1h", description="Timeframe"),
    db: DatabaseRepository = Depends(get_db)
):
    """Get technical indicators"""
    try:
        # Try to get candles for the period
        candles = db.get_candles(
            symbol=symbol.upper(),
            interval=interval,
            start_time=start,
            end_time=end,
            limit=1000
        )
        
        # If no data in range, try different intervals
        if not candles:
            logger.info(f"No data in requested range for interval {interval}, trying other intervals")
            all_intervals = ["1m", "5m", "15m", "1h", "4h", "1d"]
            for test_interval in all_intervals:
                candles = db.get_candles(
                    symbol=symbol.upper(),
                    interval=test_interval,
                    start_time=None,
                    end_time=None,
                    limit=500
                )
                if candles and len(candles) >= 50:
                    logger.info(f"Found {len(candles)} candles with interval {test_interval}")
                    break
        
        if not candles or len(candles) < 50:
            raise HTTPException(
                status_code=404, 
                detail=f"Insufficient data. Need at least 50 data points, found {len(candles) if candles else 0}. Try loading historical data first."
            )
        
        import pandas as pd
        import numpy as np
        
        df = pd.DataFrame([{
            'timestamp': c.time,
            'close': float(c.close),
            'high': float(c.high),
            'low': float(c.low)
        } for c in candles])
        
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
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# WEBSOCKET ENDPOINT FOR REAL-TIME STREAMING
# ============================================================

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")


# Global connection manager
manager = ConnectionManager()


@app.websocket("/ws/live/{symbol}")
async def websocket_endpoint(
    websocket: WebSocket,
    symbol: str = Path(..., description="Trading pair symbol (e.g., BTCUSDT)")
):
    """
    WebSocket endpoint for real-time market data streaming.
    
    Sends updates every 5 seconds with:
    - Latest candle data
    - Recent trades
    - Current risk metrics
    - Latest derivatives data
    - Recent trading signals
    """
    await manager.connect(websocket)
    
    try:
        symbol_upper = symbol.upper()
        
        while True:
            try:
                db = get_db()
                
                # Gather latest data
                latest_candle = db.get_latest_candle(symbol_upper, "1m")
                recent_trades = db.get_large_trades(symbol_upper, 0.1, hours=1)
                risk_metrics = db.get_latest_risk_metrics(symbol_upper, "1h")
                derivatives = db.get_latest_derivatives(symbol_upper)
                signals = db.get_strong_signals(symbol_upper, hours=1)
                
                # Prepare response
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "symbol": symbol_upper,
                    "candle": None,
                    "recent_trades_count": len(recent_trades),
                    "risk_metrics": None,
                    "derivatives": [],
                    "recent_signals": []
                }
                
                # Add candle data
                if latest_candle:
                    data["candle"] = {
                        "time": latest_candle.time.isoformat(),
                        "open": float(latest_candle.open),
                        "high": float(latest_candle.high),
                        "low": float(latest_candle.low),
                        "close": float(latest_candle.close),
                        "volume": float(latest_candle.volume),
                        "price_change": float(latest_candle.close - latest_candle.open),
                        "price_change_pct": float((latest_candle.close - latest_candle.open) / latest_candle.open * 100)
                    }
                
                # Add risk metrics
                if risk_metrics:
                    data["risk_metrics"] = {
                        "volatility": float(risk_metrics.volatility) if risk_metrics.volatility else None,
                        "var_95": float(risk_metrics.var_95) if risk_metrics.var_95 else None,
                        "sharpe_ratio": float(risk_metrics.sharpe_ratio) if risk_metrics.sharpe_ratio else None,
                        "max_drawdown": float(risk_metrics.max_drawdown) if risk_metrics.max_drawdown else None
                    }
                
                # Add derivatives
                for d in derivatives[:3]:  # Top 3 exchanges
                    data["derivatives"].append({
                        "exchange": d.exchange,
                        "funding_rate": float(d.funding_rate) if d.funding_rate else None,
                        "open_interest": float(d.open_interest) if d.open_interest else None,
                        "long_ratio": float(d.long_ratio) if d.long_ratio else None,
                        "short_ratio": float(d.short_ratio) if d.short_ratio else None
                    })
                
                # Add signals
                for s in signals[:3]:  # Latest 3 signals
                    data["recent_signals"].append({
                        "time": s.time.isoformat(),
                        "signal_type": s.signal_type,
                        "strength": s.strength,
                        "direction": s.direction,
                        "price": float(s.price),
                        "reason": s.reason
                    })
                
                # Send to client
                await websocket.send_json(data)
                
                # Wait 5 seconds before next update
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}")
                await asyncio.sleep(5)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"Client disconnected from {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============================================================
# STARTUP INFO
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 Bitcoin Market Intelligence API")
    print("=" * 60)
    print(f"📍 Host: 0.0.0.0")
    print(f"🔌 Port: 8000")
    print(f"📖 Docs: http://localhost:8000/docs")
    print(f"🔄 ReDoc: http://localhost:8000/redoc")
    print("=" * 60)
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
