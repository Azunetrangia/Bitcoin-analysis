"""
Pydantic Models - Request/Response schemas for API.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ==================== Enums ====================

class IntervalEnum(str, Enum):
    """Timeframe intervals."""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"


class RegimeTypeEnum(str, Enum):
    """Market regime types."""
    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"
    HIGH_VOLATILITY = "high_volatility"


# ==================== Market Data ====================

class OHLCVResponse(BaseModel):
    """OHLCV candle response."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-01-01T00:00:00",
                "open": 45000.0,
                "high": 45500.0,
                "low": 44800.0,
                "close": 45200.0,
                "volume": 123.45
            }
        }


class MarketDataResponse(BaseModel):
    """Market data query response."""
    symbol: str
    interval: str
    data: List[OHLCVResponse]
    count: int
    start: Optional[datetime] = None
    end: Optional[datetime] = None


class DownloadRequest(BaseModel):
    """Request to download historical data."""
    symbol: str = Field(default="BTCUSDT", description="Trading pair")
    start: datetime = Field(description="Start datetime")
    end: datetime = Field(description="End datetime")
    interval: IntervalEnum = Field(default=IntervalEnum.ONE_HOUR, description="Timeframe")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTCUSDT",
                "start": "2024-01-01T00:00:00",
                "end": "2024-02-01T00:00:00",
                "interval": "1h"
            }
        }


class DownloadResponse(BaseModel):
    """Response after downloading data."""
    symbol: str
    interval: str
    rows_added: int
    start: datetime
    end: datetime
    message: str


# ==================== Technical Analysis ====================

class TechnicalIndicatorsResponse(BaseModel):
    """Technical indicators response."""
    timestamp: List[datetime]
    rsi: Optional[List[Optional[float]]] = None
    macd: Optional[Dict[str, List[Optional[float]]]] = None
    bollinger_bands: Optional[Dict[str, List[Optional[float]]]] = None
    atr: Optional[List[Optional[float]]] = None
    count: int


class FeaturesResponse(BaseModel):
    """Feature extraction response."""
    timestamp: List[datetime]
    returns: List[Optional[float]]
    volatility: List[Optional[float]]
    rsi: List[Optional[float]]
    macd_histogram: List[Optional[float]]
    atr_normalized: List[Optional[float]]
    volume_change: List[Optional[float]]
    count: int


# ==================== Regime Classification ====================

class MarketRegimeResponse(BaseModel):
    """Market regime response."""
    timestamp: str
    regime: RegimeTypeEnum
    regime_state: int
    bull_prob: float = Field(ge=0.0, le=1.0)
    bear_prob: float = Field(ge=0.0, le=1.0)
    neutral_prob: float = Field(ge=0.0, le=1.0)
    high_volatility_prob: float = Field(ge=0.0, le=1.0)


class RegimeClassificationResponse(BaseModel):
    """Regime classification response."""
    symbol: str
    interval: str
    count: int
    model_score: Optional[float] = None
    regimes: List[MarketRegimeResponse]


class TrainRegimeRequest(BaseModel):
    """Request to train regime classifier."""
    symbol: str = Field(default="BTCUSDT")
    start: datetime
    end: datetime
    interval: IntervalEnum = Field(default=IntervalEnum.ONE_HOUR)
    n_regimes: int = Field(default=4, ge=2, le=10)


# ==================== Risk Metrics ====================

class DrawdownResponse(BaseModel):
    """Drawdown metrics response."""
    max_drawdown: float = Field(description="Maximum drawdown (%)")
    max_drawdown_duration: float = Field(description="Duration in hours")
    current_drawdown: float = Field(description="Current drawdown (%)")
    peak_value: float
    valley_value: float
    peak_date: datetime
    valley_date: datetime


class VolatilityResponse(BaseModel):
    """Volatility metrics response."""
    historical_volatility: float = Field(description="Annualized volatility (%)")
    rolling_volatility: List[Optional[float]] = Field(description="20-period rolling vol")
    timestamps: List[datetime]


class SharpeResponse(BaseModel):
    """Sharpe ratio response."""
    sharpe_ratio: float
    annualized_return: float
    annualized_volatility: float
    risk_free_rate: float


class VaRResponse(BaseModel):
    """Value at Risk response."""
    var_95: float = Field(description="95% VaR (%)")
    var_99: float = Field(description="99% VaR (%)")
    cvar_95: float = Field(description="95% CVaR (Expected Shortfall) (%)")
    cvar_99: float = Field(description="99% CVaR (%)")


class RiskMetricsResponse(BaseModel):
    """Comprehensive risk metrics response."""
    symbol: str
    period_start: datetime
    period_end: datetime
    drawdown: DrawdownResponse
    volatility: VolatilityResponse
    sharpe_ratio: SharpeResponse
    var: VaRResponse


# ==================== Scheduler ====================

class JobStatus(BaseModel):
    """Scheduler job status."""
    job_id: str
    name: str
    trigger: str
    description: str
    status: str
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    error_count: int
    metadata: Dict[str, Any]


class SchedulerStatusResponse(BaseModel):
    """Scheduler status response."""
    running: bool
    jobs_count: int
    timezone: str
    jobs: List[JobStatus]


class PipelineResultResponse(BaseModel):
    """Pipeline execution result."""
    pipeline_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    stage: str
    status: str
    rows_downloaded: int = 0
    rows_stored: int = 0
    regimes_classified: int = 0
    duration_seconds: Optional[float] = None
    errors: List[str] = Field(default_factory=list)


# ==================== Investment Decision ====================

class InvestmentFactorScore(BaseModel):
    """Individual factor score in investment analysis."""
    score: float = Field(description="Factor score (0-100)")
    weight: float = Field(description="Factor weight in final decision")
    contribution: float = Field(description="Weighted contribution to final score")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed analysis of this factor")


class InvestmentDecisionResponse(BaseModel):
    """Investment recommendation response."""
    symbol: str
    interval: str
    timestamp: str
    signal: str = Field(description="Investment signal: Mua mạnh/Mua/Giữ/Bán/Bán mạnh")
    score: float = Field(description="Composite score (0-100)", ge=0, le=100)
    confidence: float = Field(description="Confidence level (%)", ge=0, le=100)
    factors: Dict[str, InvestmentFactorScore] = Field(description="Individual factor scores and contributions")
    market_context: Optional[Dict[str, Any]] = Field(default=None, description="Market context analysis")
    insights: Optional[Dict[str, Any]] = Field(default=None, description="Actionable investment insights")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTCUSDT",
                "interval": "1h",
                "timestamp": "2024-11-15T12:00:00",
                "signal": "Mua",
                "score": 67.5,
                "confidence": 75.0,
                "factors": {
                    "trend": {"score": 72.0, "weight": 0.25, "contribution": 18.0},
                    "technical": {"score": 65.0, "weight": 0.25, "contribution": 16.25},
                    "risk": {"score": 58.0, "weight": 0.20, "contribution": 11.6},
                    "regime": {"score": 80.0, "weight": 0.20, "contribution": 16.0},
                    "drawdown": {"score": 55.0, "weight": 0.10, "contribution": 5.5}
                }
            }
        }


# ==================== Error Responses ====================

class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    status_code: int
