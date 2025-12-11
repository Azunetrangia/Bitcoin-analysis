"""
Analysis API Routes.

Endpoints for technical analysis, regime classification, and risk metrics.
"""

from datetime import datetime
from typing import Optional
import pandas as pd
import numpy as np

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_analysis_service
from src.api.models import (
    TechnicalIndicatorsResponse,
    FeaturesResponse,
    MarketRegimeResponse,
    RegimeClassificationResponse,
    TrainRegimeRequest,
    DrawdownResponse,
    VolatilityResponse,
    SharpeResponse,
    VaRResponse,
    RiskMetricsResponse,
    InvestmentDecisionResponse,
    InvestmentFactorScore,
    IntervalEnum,
    RegimeTypeEnum
)
from src.application.services.analysis_service import AnalysisService
from src.shared.exceptions.custom_exceptions import (
    DataNotFoundError,
    AnalysisException
)
from src.infrastructure.storage.duckdb_query_engine import DuckDBQueryEngine
from src.domain.services.technical_analysis import TechnicalAnalysisService
from src.shared.config.settings import Settings
from pathlib import Path

router = APIRouter()

# Initialize TA service, Regime service, and DuckDB (lazy)
settings = Settings()
db_path = Path(settings.STORAGE_PATH) / "bitcoin_market.db"
ta_service = TechnicalAnalysisService()

# Import regime services
from src.domain.services.regime_classifier import RegimeClassifierService
from src.domain.services.risk_calculator import RiskCalculatorService

regime_service = RegimeClassifierService(n_regimes=4, n_hmm_states=4)  # 4 regimes: Bull/Bear/Neutral/HighVol
risk_service = RiskCalculatorService()

_db_engine = None

def get_db_engine():
    global _db_engine
    if _db_engine is None:
        import duckdb
        _db_engine = duckdb.connect(str(db_path), read_only=True)
    return _db_engine


def query_and_calculate_indicators(
    symbol: str,
    interval: str,
    start: Optional[datetime],
    end: Optional[datetime],
    limit: Optional[int] = None
) -> pd.DataFrame:
    """Query data from DuckDB and calculate technical indicators."""
    # Query data
    query = f"""
        SELECT timestamp, open, high, low, close, volume
        FROM market_data
        WHERE symbol = '{symbol}'
        AND interval = '{interval}'
    """
    
    if start:
        query += f" AND timestamp >= '{start.isoformat()}'"
    if end:
        query += f" AND timestamp <= '{end.isoformat()}'"
    
    query += " ORDER BY timestamp ASC"
    
    if limit:
        # Get more data for indicator calculation (need history)
        query += f" LIMIT {limit + 200}"
    
    conn = get_db_engine()
    df = conn.execute(query).fetchdf()
    
    if df.empty:
        return pd.DataFrame()
    
    # Ensure timestamp is datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Calculate indicators
    df_with_indicators = ta_service.calculate_all_indicators(df)
    
    # Apply final limit if specified
    if limit and len(df_with_indicators) > limit:
        df_with_indicators = df_with_indicators.iloc[-limit:]
    
    return df_with_indicators


def query_and_classify_regimes(
    symbol: str,
    interval: str,
    start: Optional[datetime],
    end: Optional[datetime],
    limit: Optional[int] = None
) -> dict:
    """Query data, calculate indicators, and classify regimes."""
    # Get data with indicators
    df = query_and_calculate_indicators(
        symbol=symbol,
        interval=interval,
        start=start,
        end=end,
        limit=None  # Need full history for regime classification
    )
    
    if df.empty:
        return {}
    
    # Ensure we have the required columns for feature extraction
    # The DataFrame should have: timestamp, open, high, low, close, volume, + indicators
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            raise HTTPException(status_code=500, detail=f"Missing required column: {col}")
    
    # Check if we have enough data
    if len(df) < 100:
        raise HTTPException(status_code=400, detail=f"Insufficient data for regime classification (need 100+, got {len(df)})")
    
    # Set timestamp as index for feature extraction to preserve it
    if 'timestamp' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index('timestamp')
    
    # Train regime classifier if not fitted (pass raw OHLCV data, it will extract features internally)
    if not hasattr(regime_service, 'is_fitted') or not regime_service.is_fitted:
        regime_service.fit(df)  # Pass df, not features_df
    
    # Get probability predictions (returns DataFrame with prob_bull, prob_bear, etc.)
    proba_df = regime_service.predict_proba(df)
    
    # Validate outputs
    if proba_df.empty:
        raise HTTPException(status_code=500, detail="No regimes classified")
    
    # Ensure all probability columns exist (fill with 0 if missing)
    prob_cols = ['prob_bull', 'prob_bear', 'prob_neutral', 'prob_high_volatility']
    for col in prob_cols:
        if col not in proba_df.columns:
            proba_df[col] = 0.0
    
    # Extract probabilities as numpy array for easier manipulation
    probabilities = proba_df[prob_cols].values
    
    if probabilities.ndim != 2:
        raise HTTPException(status_code=500, detail=f"Invalid probabilities shape: {probabilities.shape}")
    
    n_samples, n_states = probabilities.shape
    
    # Get regime labels from max probability
    regime_labels = np.argmax(probabilities, axis=1)
    
    if n_samples != len(regime_labels):
        raise HTTPException(status_code=500, detail=f"Length mismatch: {n_samples} probs vs {len(regime_labels)} labels")
    
    # Get regime names
    regime_names = []
    for label in regime_labels:
        if label == 0:
            regime_names.append("bull")
        elif label == 1:
            regime_names.append("bear")
        elif label == 2:
            regime_names.append("neutral")
        else:
            regime_names.append("high_volatility")
    
    # Use timestamps from proba_df (it has the correct aligned timestamps after feature extraction)
    # The index should be DatetimeIndex after feature extraction
    result_timestamps = pd.to_datetime(proba_df.index).astype(str).values
    
    # Combine results into DataFrame
    result_df = pd.DataFrame({
        'timestamp': result_timestamps,
        'regime': regime_names,
        'regime_state': regime_labels,
        'bull_prob': probabilities[:, 0] if n_states > 0 else np.zeros(n_samples),
        'bear_prob': probabilities[:, 1] if n_states > 1 else np.zeros(n_samples),
        'neutral_prob': probabilities[:, 2] if n_states > 2 else np.zeros(n_samples),
        'high_volatility_prob': probabilities[:, 3] if n_states > 3 else np.zeros(n_samples)
    })
    
    # Apply limit if specified
    if limit and len(result_df) > limit:
        result_df = result_df.iloc[-limit:]
    
    return {
        "regimes": result_df,
        "model_type": "HMM",
        "n_states": regime_service.n_components if hasattr(regime_service, 'n_components') else 4
    }


# ============================================================================
# TECHNICAL INDICATORS
# ============================================================================

@router.get(
    "/indicators",
    summary="Calculate technical indicators",
    description="Calculate technical indicators for market data"
)
async def get_technical_indicators(
    symbol: str = Query(default="BTCUSDT"),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    interval: IntervalEnum = Query(default=IntervalEnum.ONE_HOUR),
    limit: Optional[int] = Query(default=1000, description="Max rows to return (default 1000)"),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Calculate technical indicators.
    
    Computes RSI, MACD, Bollinger Bands, and moving averages.
    
    ## Parameters
    - **symbol**: Trading pair
    - **start**: Start datetime
    - **end**: End datetime
    - **interval**: Timeframe
    
    ## Returns
    Technical indicators for each timestamp.
    """
    try:
        # Query data and calculate indicators directly
        df = query_and_calculate_indicators(
            symbol=symbol,
            interval=interval.value,
            start=start,
            end=end,
            limit=limit
        )
        
        if df.empty:
            raise HTTPException(status_code=404, detail="No data found")
        
        # Convert to records for response
        # Get available columns (some indicators might be missing)
        available_cols = df.columns.tolist()
        cols_to_include = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        # Add indicator columns if they exist
        indicator_cols = ['rsi', 'macd', 'macd_signal', 'macd_hist',
                         'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
                         'sma_20', 'sma_50', 'ema_12', 'ema_26']
        
        for col in indicator_cols:
            if col in available_cols:
                cols_to_include.append(col)
        
        result_df = df[cols_to_include].copy()
        
        # Convert timestamps to strings for JSON serialization
        result_df['timestamp'] = result_df['timestamp'].astype(str)
        
        # Replace NaN/inf with None for JSON compliance
        result_df = result_df.replace([float('nan'), float('inf'), float('-inf')], None)
        
        indicators = result_df.to_dict(orient="records")
        
        return {
            "symbol": symbol,
            "interval": interval.value,
            "count": len(indicators),
            "data": indicators
        }
        
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AnalysisException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get(
    "/features",
    response_model=FeaturesResponse,
    summary="Extract regime features",
    description="Extract features used for regime classification"
)
async def get_regime_features(
    symbol: str = Query(default="BTCUSDT"),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    interval: IntervalEnum = Query(default=IntervalEnum.ONE_HOUR),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Extract regime classification features.
    
    Calculates returns, volatility, and momentum features.
    
    ## Parameters
    - **symbol**: Trading pair
    - **start**: Start datetime
    - **end**: End datetime
    - **interval**: Timeframe
    
    ## Returns
    Feature vectors for regime classification.
    """
    try:
        df = analysis_service.extract_regime_features(
            symbol=symbol,
            start=start,
            end=end,
            interval=interval.value
        )
        
        if df.empty:
            raise HTTPException(status_code=404, detail="No data found")
        
        features = df.to_dict(orient="records")
        
        return FeaturesResponse(
            symbol=symbol,
            interval=interval.value,
            count=len(features),
            features=features
        )
        
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AnalysisException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feature extraction failed: {str(e)}")


# ============================================================================
# REGIME CLASSIFICATION
# ============================================================================

@router.get(
    "/regimes",
    response_model=RegimeClassificationResponse,
    summary="Classify market regimes",
    description="Classify market conditions using trained HMM model"
)
async def classify_regimes(
    symbol: str = Query(default="BTCUSDT"),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    interval: IntervalEnum = Query(default=IntervalEnum.ONE_HOUR),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Classify market regimes.
    
    Uses Hidden Markov Model to classify market conditions.
    
    ## Parameters
    - **symbol**: Trading pair
    - **start**: Start datetime
    - **end**: End datetime
    - **interval**: Timeframe
    
    ## Returns
    Regime predictions (bull/bear/neutral/high_volatility) with probabilities.
    """
    try:
        # Query data and classify regimes
        result = query_and_classify_regimes(
            symbol=symbol,
            interval=interval.value,
            start=start,
            end=end,
            limit=100  # Limit for response size
        )
        
        if not result or "regimes" not in result:
            raise HTTPException(status_code=404, detail="No regimes found")
        
        df = result["regimes"]
        
        # Convert timestamps to strings
        df['timestamp'] = df['timestamp'].astype(str)
        
        # Clip probabilities to [0, 1] to handle floating point precision issues
        df['bull_prob'] = df['bull_prob'].clip(0.0, 1.0)
        df['bear_prob'] = df['bear_prob'].clip(0.0, 1.0)
        df['neutral_prob'] = df['neutral_prob'].clip(0.0, 1.0)
        df['high_volatility_prob'] = df['high_volatility_prob'].clip(0.0, 1.0)
        
        regimes = [
            MarketRegimeResponse(
                timestamp=row.timestamp,
                regime=RegimeTypeEnum(row.regime),
                regime_state=int(row.regime_state),
                bull_prob=float(row.bull_prob),
                bear_prob=float(row.bear_prob),
                neutral_prob=float(row.neutral_prob),
                high_volatility_prob=float(row.high_volatility_prob)
            )
            for row in df.itertuples(index=False)
        ]
        
        return RegimeClassificationResponse(
            symbol=symbol,
            interval=interval.value,
            count=len(regimes),
            model_score=None,  # Can add model score later
            regimes=regimes
        )
        
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AnalysisException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.post(
    "/train-regime",
    summary="Train regime classifier",
    description="Train HMM model for regime classification"
)
async def train_regime_classifier(
    request: TrainRegimeRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Train regime classifier model.
    
    Trains Hidden Markov Model on historical data.
    
    ## Request Body
    ```json
    {
        "symbol": "BTCUSDT",
        "start": "2023-01-01T00:00:00",
        "end": "2024-01-01T00:00:00",
        "interval": "1h",
        "n_states": 4
    }
    ```
    
    ## Returns
    Training confirmation with model score.
    """
    try:
        result = analysis_service.train_regime_classifier(
            symbol=request.symbol,
            start=request.start,
            end=request.end,
            interval=request.interval.value,
            n_states=request.n_states
        )
        
        return {
            "message": "Model trained successfully",
            "symbol": request.symbol,
            "interval": request.interval.value,
            "n_states": request.n_states,
            "score": result.get("score"),
            "samples": result.get("samples")
        }
        
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AnalysisException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


# ============================================================================
# RISK METRICS
# ============================================================================

@router.get(
    "/risk-metrics",
    summary="Calculate risk metrics",
    description="Calculate comprehensive risk metrics (drawdown, volatility, Sharpe, VaR)"
)
async def get_risk_metrics(
    symbol: str = Query(default="BTCUSDT"),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    interval: IntervalEnum = Query(default=IntervalEnum.ONE_HOUR),
    window: int = Query(default=30, ge=2, description="Rolling window for volatility"),
    risk_free_rate: float = Query(default=0.02, ge=0, le=1, description="Annual risk-free rate"),
    confidence_level: float = Query(default=0.95, ge=0, le=1, description="VaR confidence level"),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Calculate comprehensive risk metrics.
    
    ## Parameters
    - **symbol**: Trading pair
    - **start**: Start datetime
    - **end**: End datetime
    - **interval**: Timeframe
    - **window**: Rolling window for volatility calculation
    - **risk_free_rate**: Annual risk-free rate for Sharpe ratio (0-1)
    - **confidence_level**: VaR confidence level (0-1, e.g., 0.95 for 95%)
    
    ## Returns
    Risk metrics including:
    - **Drawdown**: Maximum drawdown and underwater periods
    - **Volatility**: Historical and annualized volatility
    - **Sharpe Ratio**: Risk-adjusted returns
    - **Value at Risk (VaR)**: Potential losses at confidence level
    """
    try:
        result = analysis_service.analyze_risk(
            symbol=symbol,
            interval=interval.value,
            start=start,
            end=end,
            confidence_level=confidence_level
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="No data found")
        
        # Convert result to dict and return
        return {
            "symbol": symbol,
            "interval": interval.value,
            "start": start,
            "end": end,
            "metrics": result.__dict__ if hasattr(result, '__dict__') else result
        }
        
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AnalysisException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk calculation failed: {str(e)}")


@router.get(
    "/drawdown",
    summary="Calculate drawdown",
    description="Calculate maximum drawdown metrics"
)
async def get_drawdown(
    symbol: str = Query(default="BTCUSDT"),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    interval: IntervalEnum = Query(default=IntervalEnum.ONE_HOUR),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """Calculate drawdown metrics only."""
    try:
        result = analysis_service.analyze_risk(
            symbol=symbol,
            interval=interval.value,
            start=start,
            end=end
        )
        
        # Extract max_drawdown from result
        return {"max_drawdown": result.max_drawdown if hasattr(result, 'max_drawdown') else result.get('max_drawdown')}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/volatility",
    summary="Calculate volatility",
    description="Calculate volatility metrics"
)
async def get_volatility(
    symbol: str = Query(default="BTCUSDT"),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    interval: IntervalEnum = Query(default=IntervalEnum.ONE_HOUR),
    window: int = Query(default=30, ge=2),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """Calculate volatility metrics only."""
    try:
        result = analysis_service.analyze_risk(
            symbol=symbol,
            interval=interval.value,
            start=start,
            end=end
        )
        
        # Extract volatility from result
        return {"volatility": result.volatility if hasattr(result, 'volatility') else result.get('volatility')}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sharpe",
    summary="Calculate Sharpe ratio",
    description="Calculate risk-adjusted returns (Sharpe ratio)"
)
async def get_sharpe_ratio(
    symbol: str = Query(default="BTCUSDT"),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    interval: IntervalEnum = Query(default=IntervalEnum.ONE_HOUR),
    risk_free_rate: float = Query(default=0.02, ge=0, le=1),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """Calculate Sharpe ratio only."""
    try:
        result = analysis_service.analyze_risk(
            symbol=symbol,
            interval=interval.value,
            start=start,
            end=end
        )
        
        # Extract sharpe_ratio from result
        return {"sharpe_ratio": result.sharpe_ratio if hasattr(result, 'sharpe_ratio') else result.get('sharpe_ratio')}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/var",
    summary="Calculate Value at Risk",
    description="Calculate potential losses at given confidence level"
)
async def get_value_at_risk(
    symbol: str = Query(default="BTCUSDT"),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    interval: IntervalEnum = Query(default=IntervalEnum.ONE_HOUR),
    confidence_level: float = Query(default=0.95, ge=0, le=1),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """Calculate Value at Risk only."""
    try:
        result = analysis_service.analyze_risk(
            symbol=symbol,
            interval=interval.value,
            start=start,
            end=end,
            confidence_level=confidence_level
        )
        
        # Extract VaR from result based on confidence level
        var_key = f'var_{int(confidence_level * 100)}'
        return {var_key: result.__dict__.get(var_key) if hasattr(result, '__dict__') else result.get(var_key)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Investment Decision ====================

@router.get("/decision", 
    response_model=InvestmentDecisionResponse,
    summary="Get investment recommendation",
    description="""
    Get multi-factor investment recommendation combining:
    - Trend analysis (price direction, momentum)
    - Technical indicators (RSI, MACD signals)
    - Risk metrics (VaR, Volatility, Sharpe)
    - Market regime classification
    - Drawdown analysis
    
    Returns investment signal: Mua mạnh/Mua/Giữ/Bán/Bán mạnh
    """,
    tags=["Investment"]
)
async def get_investment_decision(
    symbol: str = Query(default="BTCUSDT", description="Trading pair"),
    interval: IntervalEnum = Query(default=IntervalEnum.ONE_HOUR, description="Timeframe"),
    start: Optional[datetime] = Query(default=None, description="Start date (default: 30 days ago)"),
    end: Optional[datetime] = Query(default=None, description="End date (default: now)")
):
    """
    Generate investment recommendation based on multi-factor analysis.
    
    Requires at least 50 periods of data for accurate analysis.
    """
    from src.domain.services.investment_advisor import InvestmentAdvisorService
    from datetime import timedelta
    
    # Default date range (30 days)
    if end is None:
        end = datetime.now()
    if start is None:
        start = end - timedelta(days=30)
    
    # Initialize advisor
    advisor = InvestmentAdvisorService()
    
    try:
        # Query market data with SQL
        query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = '{symbol}'
            AND interval = '{interval.value}'
            AND timestamp >= '{start.isoformat()}'
            AND timestamp <= '{end.isoformat()}'
            ORDER BY timestamp ASC
        """
        
        import duckdb
        conn = duckdb.connect(str(db_path), read_only=True)
        df = conn.execute(query).fetchdf()
        conn.close()
        
        if df.empty or len(df) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for analysis (need 50+, got {len(df) if df is not None else 0})"
            )
        
        # Calculate technical indicators
        df = ta_service.calculate_all_indicators(df)
        
        # Get regime data
        regime_df = None
        try:
            # Fit regime classifier if needed
            if not regime_service.is_fitted:
                train_query = f"""
                    SELECT timestamp, open, high, low, close, volume
                    FROM market_data
                    WHERE symbol = '{symbol}'
                    AND interval = '{interval.value}'
                    AND timestamp >= '{(start - timedelta(days=60)).isoformat()}'
                    AND timestamp <= '{end.isoformat()}'
                    ORDER BY timestamp ASC
                """
                
                conn = duckdb.connect(str(db_path), read_only=True)
                train_df = conn.execute(train_query).fetchdf()
                conn.close()
                
                if train_df is not None and len(train_df) >= 100:
                    train_df = ta_service.calculate_all_indicators(train_df)
                    regime_service.fit(train_df)
            
            # Predict regimes
            if regime_service.is_fitted:
                df_for_regime = df.copy()
                df_for_regime = df_for_regime.set_index('timestamp')
                proba_df = regime_service.predict_proba(df_for_regime)
                
                prob_cols = ['prob_bull', 'prob_bear', 'prob_neutral', 'prob_high_volatility']
                for col in prob_cols:
                    if col not in proba_df.columns:
                        proba_df[col] = 0.0
                
                regime_df = pd.DataFrame({
                    'timestamp': pd.to_datetime(proba_df.index).astype(str).values,
                    'bull_prob': proba_df['prob_bull'].clip(0.0, 1.0).values,
                    'bear_prob': proba_df['prob_bear'].clip(0.0, 1.0).values,
                    'neutral_prob': proba_df['prob_neutral'].clip(0.0, 1.0).values,
                    'high_volatility_prob': proba_df['prob_high_volatility'].clip(0.0, 1.0).values
                })
        except Exception as e:
            print(f"Warning: Could not classify regimes: {e}")
            # Continue without regime data
        
        # Generate investment recommendation
        result = advisor.analyze(df, regime_data=regime_df)
        
        # Format factors for response
        formatted_factors = {
            factor_name: InvestmentFactorScore(**factor_data)
            for factor_name, factor_data in result['factors'].items()
        }
        
        return InvestmentDecisionResponse(
            symbol=symbol,
            interval=interval.value,
            timestamp=str(result['timestamp']),
            signal=result['signal'],
            score=result['score'],
            confidence=result['confidence'],
            factors=formatted_factors,
            market_context=result.get('market_context'),
            insights=result.get('insights')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

