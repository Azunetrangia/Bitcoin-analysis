"""
DateTime Utilities
~~~~~~~~~~~~~~~~~~

Date and time manipulation helpers for financial data.

Features:
- Timezone-aware datetime handling (UTC for market data)
- Business day calculations
- Date range generation
- Timestamp conversions

Usage:
    from src.shared.utils.datetime_utils import get_date_range, to_utc
    
    dates = get_date_range("2021-01-01", "2024-01-01", freq="1D")
    utc_time = to_utc("2024-01-01 12:00:00")
"""

from datetime import datetime, timedelta, timezone
from typing import Literal
import pandas as pd


def to_utc(dt: datetime | str) -> datetime:
    """
    Convert datetime to UTC timezone.
    
    Args:
        dt: Datetime object or ISO string
        
    Returns:
        Timezone-aware datetime in UTC
        
    Example:
        >>> to_utc("2024-01-01 12:00:00")
        datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(timezone.utc)


def now_utc() -> datetime:
    """
    Get current UTC datetime.
    
    Returns:
        Current datetime in UTC
    """
    return datetime.now(timezone.utc)


def get_date_range(
    start: datetime | str,
    end: datetime | str,
    freq: Literal["1h", "1d", "1w", "1M"] = "1d"
) -> pd.DatetimeIndex:
    """
    Generate date range between start and end dates.
    
    Args:
        start: Start date (inclusive)
        end: End date (inclusive)
        freq: Frequency (1h=hourly, 1d=daily, 1w=weekly, 1M=monthly)
        
    Returns:
        Pandas DatetimeIndex
        
    Example:
        >>> get_date_range("2024-01-01", "2024-01-07", freq="1d")
        DatetimeIndex(['2024-01-01', '2024-01-02', ..., '2024-01-07'])
    """
    if isinstance(start, str):
        start = pd.Timestamp(start)
    if isinstance(end, str):
        end = pd.Timestamp(end)
    
    return pd.date_range(start=start, end=end, freq=freq, tz="UTC")


def days_ago(days: int) -> datetime:
    """
    Get datetime N days ago from now (UTC).
    
    Args:
        days: Number of days in the past
        
    Returns:
        Datetime N days ago
        
    Example:
        >>> days_ago(30)  # 30 days ago
        datetime.datetime(2023, 12, 02, 12, 0, tzinfo=datetime.timezone.utc)
    """
    return now_utc() - timedelta(days=days)


def to_timestamp(dt: datetime) -> int:
    """
    Convert datetime to Unix timestamp (milliseconds).
    
    Args:
        dt: Datetime object
        
    Returns:
        Unix timestamp in milliseconds
        
    Example:
        >>> to_timestamp(datetime(2024, 1, 1, tzinfo=timezone.utc))
        1704067200000
    """
    return int(dt.timestamp() * 1000)


def from_timestamp(ts: int) -> datetime:
    """
    Convert Unix timestamp to datetime (UTC).
    
    Args:
        ts: Unix timestamp (milliseconds or seconds auto-detected)
        
    Returns:
        Timezone-aware datetime in UTC
        
    Example:
        >>> from_timestamp(1704067200000)
        datetime.datetime(2024, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
    """
    # Auto-detect milliseconds vs seconds
    if ts > 1e12:  # Likely milliseconds
        ts = ts / 1000
    
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Human-readable string (e.g., "2h 30m 15s")
        
    Example:
        >>> format_duration(9015)
        "2h 30m 15s"
    """
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)
