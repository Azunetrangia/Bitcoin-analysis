"""
Market Data API Routes.

Endpoints for querying and downloading market data.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from src.api.dependencies import get_market_service
from src.api.models import (
    MarketDataResponse,
    OHLCVResponse,
    DownloadRequest,
    DownloadResponse,
    IntervalEnum
)
from src.application.services.market_data_service import MarketDataService
from src.shared.exceptions.custom_exceptions import DataNotFoundError, DataDownloadError
from src.infrastructure.storage.duckdb_query_engine import DuckDBQueryEngine
from src.shared.config.settings import Settings
from pathlib import Path
import pandas as pd

router = APIRouter()

# DuckDB connection for fast queries (shared, read-only)
settings = Settings()
db_path = Path(settings.STORAGE_PATH) / "bitcoin_market.db"

# Lazy initialization to avoid conflicts
_db_engine = None

def get_db_engine():
    global _db_engine
    if _db_engine is None:
        import duckdb
        # Use read-only connection to avoid lock conflicts
        _db_engine = duckdb.connect(str(db_path), read_only=True)
    return _db_engine


def query_duckdb(
    symbol: str,
    interval: str,
    start: Optional[datetime],
    end: Optional[datetime],
    limit: Optional[int] = None
) -> pd.DataFrame:
    """Query data directly from DuckDB."""
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
        query += f" LIMIT {limit}"
    
    conn = get_db_engine()
    df = conn.execute(query).fetchdf()
    
    if not df.empty and 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df


@router.get(
    "/",
    response_model=MarketDataResponse,
    summary="Query market data",
    description="Query historical OHLCV data with flexible filters"
)
async def get_market_data(
    symbol: str = Query(default="BTCUSDT", description="Trading pair"),
    start: Optional[datetime] = Query(default=None, description="Start datetime"),
    end: Optional[datetime] = Query(default=None, description="End datetime"),
    interval: IntervalEnum = Query(default=IntervalEnum.ONE_HOUR, description="Timeframe"),
    limit: Optional[int] = Query(default=None, ge=1, le=5000, description="Max rows"),
    market_service: MarketDataService = Depends(get_market_service)
):
    """
    Query historical market data.
    
    ## Parameters
    - **symbol**: Trading pair (e.g., BTCUSDT)
    - **start**: Start datetime (ISO 8601)
    - **end**: End datetime (ISO 8601)
    - **interval**: Candle timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
    - **limit**: Maximum number of rows to return
    
    ## Returns
    OHLCV data matching the query filters.
    
    ## Example
    ```
    GET /api/v1/market-data/?symbol=BTCUSDT&start=2024-01-01&end=2024-01-02&interval=1h
    ```
    """
    try:
        # Query directly from DuckDB for fast access
        df = query_duckdb(
            symbol=symbol,
            interval=interval.value,
            start=start,
            end=end,
            limit=limit
        )
        
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for {symbol} with given filters"
            )
        
        # Convert DataFrame to response - use timestamp column, not index
        ohlcv_data = [
            OHLCVResponse(
                timestamp=row.timestamp,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume
            )
            for row in df.itertuples()
        ]
        
        return MarketDataResponse(
            symbol=symbol,
            interval=interval.value,
            data=ohlcv_data,
            count=len(ohlcv_data),
            start=df['timestamp'].min() if not df.empty else None,
            end=df['timestamp'].max() if not df.empty else None
        )
        
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get(
    "/latest",
    response_model=OHLCVResponse,
    summary="Get latest candle",
    description="Get the most recent OHLCV candle"
)
async def get_latest_candle(
    symbol: str = Query(default="BTCUSDT", description="Trading pair"),
    interval: IntervalEnum = Query(default=IntervalEnum.ONE_HOUR, description="Timeframe"),
    market_service: MarketDataService = Depends(get_market_service)
):
    """
    Get the latest candle for a symbol.
    
    ## Parameters
    - **symbol**: Trading pair (e.g., BTCUSDT)
    - **interval**: Candle timeframe
    
    ## Returns
    The most recent OHLCV candle.
    """
    try:
        # Query all data and get the last row
        df = market_service.get_data_as_dataframe(
            symbol=symbol,
            interval=interval.value,
            start=datetime(2020, 1, 1),  # Far past
            end=datetime.now()
        )
        
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for {symbol}"
            )
        
        row = df.iloc[0]
        
        return OHLCVResponse(
            timestamp=df.index[0],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"]
        )
        
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post(
    "/download",
    response_model=DownloadResponse,
    summary="Download historical data",
    description="Download and store historical data from Binance"
)
async def download_historical_data(
    request: DownloadRequest,
    market_service: MarketDataService = Depends(get_market_service)
):
    """
    Download historical data from Binance.
    
    This fetches data from Binance API and stores it in the local repository.
    
    ## Request Body
    ```json
    {
        "symbol": "BTCUSDT",
        "start": "2024-01-01T00:00:00",
        "end": "2024-02-01T00:00:00",
        "interval": "1h"
    }
    ```
    
    ## Returns
    Download confirmation with row count.
    """
    try:
        rows_added = market_service.download_historical_data(
            symbol=request.symbol,
            start=request.start,
            end=request.end,
            interval=request.interval.value
        )
        
        return DownloadResponse(
            symbol=request.symbol,
            interval=request.interval.value,
            rows_added=rows_added,
            start=request.start,
            end=request.end,
            message=f"Successfully downloaded {rows_added} candles"
        )
        
    except DataDownloadError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post(
    "/update",
    response_model=DownloadResponse,
    summary="Update latest data",
    description="Download latest candles to keep data up-to-date"
)
async def update_latest_data(
    symbol: str = Query(default="BTCUSDT"),
    interval: IntervalEnum = Query(default=IntervalEnum.ONE_HOUR),
    limit: int = Query(default=2, ge=1, le=100),
    market_service: MarketDataService = Depends(get_market_service)
):
    """
    Update with latest candles.
    
    This downloads the most recent N candles to keep data fresh.
    
    ## Parameters
    - **symbol**: Trading pair
    - **interval**: Timeframe
    - **limit**: Number of recent candles to fetch (default: 2)
    
    ## Returns
    Update confirmation with row count.
    """
    try:
        result = market_service.update_latest_data(
            symbol=symbol,
            interval=interval.value,
            limit=limit
        )
        
        rows = result.get("rows_added", 0) if isinstance(result, dict) else result
        
        return DownloadResponse(
            symbol=symbol,
            interval=interval.value,
            rows_added=rows,
            start=datetime.now(),
            end=datetime.now(),
            message=f"Successfully updated with {rows} new candles"
        )
        
    except DataDownloadError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
