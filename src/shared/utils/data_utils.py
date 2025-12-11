"""
Data Processing Utilities
~~~~~~~~~~~~~~~~~~~~~~~~~~

Helper functions for data validation and manipulation.

Features:
- DataFrame validation
- Missing data handling
- Data type conversions
- OHLCV data validation

Usage:
    from src.shared.utils.data_utils import validate_ohlcv, check_missing_data
    
    validate_ohlcv(df)
    missing = check_missing_data(df)
"""

import pandas as pd
import numpy as np
from typing import List
from src.shared.exceptions.custom_exceptions import DataValidationError
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


def validate_ohlcv(df: pd.DataFrame) -> None:
    """
    Validate OHLCV DataFrame structure and data integrity.
    
    Args:
        df: DataFrame with columns [open, high, low, close, volume]
        
    Raises:
        DataValidationError: If validation fails
        
    Checks:
        - Required columns exist
        - No negative prices/volumes
        - High >= Low
        - High >= Open, Close
        - Low <= Open, Close
    """
    required_cols = ["open", "high", "low", "close", "volume"]
    missing_cols = set(required_cols) - set(df.columns)
    
    if missing_cols:
        raise DataValidationError(
            f"Missing required columns: {missing_cols}",
            details={"missing_columns": list(missing_cols)}
        )
    
    # Check for negative values
    for col in ["open", "high", "low", "close"]:
        if (df[col] < 0).any():
            raise DataValidationError(
                f"Negative values found in column: {col}",
                details={"column": col, "min_value": df[col].min()}
            )
    
    # Check OHLC relationships
    if (df["high"] < df["low"]).any():
        invalid_rows = df[df["high"] < df["low"]]
        raise DataValidationError(
            "High price is lower than Low price",
            details={"invalid_rows": len(invalid_rows)}
        )
    
    if (df["high"] < df["open"]).any() or (df["high"] < df["close"]).any():
        raise DataValidationError("High price is lower than Open or Close")
    
    if (df["low"] > df["open"]).any() or (df["low"] > df["close"]).any():
        raise DataValidationError("Low price is higher than Open or Close")
    
    logger.info(f"✅ OHLCV validation passed", rows=len(df))


def check_missing_data(df: pd.DataFrame) -> dict[str, int]:
    """
    Check for missing data in DataFrame.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Dictionary with column names and count of missing values
        
    Example:
        >>> check_missing_data(df)
        {'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 5}
    """
    missing = df.isnull().sum()
    missing_dict = missing[missing > 0].to_dict()
    
    if missing_dict:
        logger.warning(f"⚠️ Missing data detected", missing=missing_dict)
    
    return missing_dict


def fill_missing_ohlcv(df: pd.DataFrame, method: str = "ffill") -> pd.DataFrame:
    """
    Fill missing values in OHLCV data.
    
    Args:
        df: OHLCV DataFrame
        method: Filling method ('ffill', 'bfill', or 'interpolate')
        
    Returns:
        DataFrame with filled values
        
    Note:
        - 'ffill': Forward fill (use last valid observation)
        - 'bfill': Backward fill (use next valid observation)
        - 'interpolate': Linear interpolation
    """
    df = df.copy()
    
    if method == "interpolate":
        df = df.interpolate(method="linear")
    else:
        df = df.fillna(method=method)
    
    # Volume: use 0 for missing values (no trading volume)
    df["volume"] = df["volume"].fillna(0)
    
    return df


def detect_outliers(
    series: pd.Series,
    method: str = "iqr",
    threshold: float = 3.0
) -> pd.Series:
    """
    Detect outliers in time series data.
    
    Args:
        series: Input series
        method: Detection method ('iqr' or 'zscore')
        threshold: Threshold for outlier detection
            - For IQR: multiplier (default 3.0 = extreme outliers)
            - For Z-score: number of standard deviations (default 3.0)
            
    Returns:
        Boolean series (True = outlier)
        
    Example:
        >>> outliers = detect_outliers(df["volume"], method="iqr")
        >>> df[outliers]  # Show outlier rows
    """
    if method == "iqr":
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        
        return (series < lower_bound) | (series > upper_bound)
    
    elif method == "zscore":
        z_scores = np.abs((series - series.mean()) / series.std())
        return z_scores > threshold
    
    else:
        raise ValueError(f"Unknown method: {method}. Use 'iqr' or 'zscore'")


def resample_ohlcv(
    df: pd.DataFrame,
    freq: str,
    timestamp_col: str = "timestamp"
) -> pd.DataFrame:
    """
    Resample OHLCV data to different frequency.
    
    Args:
        df: OHLCV DataFrame with timestamp index or column
        freq: Target frequency ('1h', '4h', '1d', etc.)
        timestamp_col: Name of timestamp column (if not index)
        
    Returns:
        Resampled DataFrame
        
    Example:
        >>> # Resample 1h data to 4h
        >>> df_4h = resample_ohlcv(df, freq="4h")
    """
    df = df.copy()
    
    # Set timestamp as index if needed
    if timestamp_col in df.columns:
        df = df.set_index(timestamp_col)
    
    # Ensure index is datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    # Resample
    resampled = df.resample(freq).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    })
    
    return resampled.dropna()


def calculate_returns(
    prices: pd.Series,
    method: str = "simple"
) -> pd.Series:
    """
    Calculate returns from price series.
    
    Args:
        prices: Price series
        method: 'simple' or 'log' returns
        
    Returns:
        Returns series
        
    Example:
        >>> returns = calculate_returns(df["close"], method="log")
    """
    if method == "simple":
        return prices.pct_change()
    elif method == "log":
        return np.log(prices / prices.shift(1))
    else:
        raise ValueError(f"Unknown method: {method}. Use 'simple' or 'log'")
