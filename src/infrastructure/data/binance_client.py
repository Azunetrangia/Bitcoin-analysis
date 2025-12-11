"""
Binance Data Client
~~~~~~~~~~~~~~~~~~~

Infrastructure component for downloading historical data from Binance Public Data.

Data Source: https://data.binance.vision
- Free, unlimited downloads
- Historical klines (OHLCV) data
- Available in CSV and ZIP formats

File Structure:
  /data/spot/monthly/klines/BTCUSDT/1h/
    BTCUSDT-1h-2024-01.zip
    BTCUSDT-1h-2024-02.zip
    ...
"""

import requests
import zipfile
import io
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
from tqdm import tqdm

from src.shared.config.settings import settings
from src.shared.exceptions.custom_exceptions import DataDownloadError, DataParsingError
from src.shared.utils.logging_utils import get_logger
from src.shared.utils.datetime_utils import to_utc

logger = get_logger(__name__)


class BinanceDataClient:
    """
    Client for downloading historical data from Binance Public Data.
    
    This client handles:
    - Constructing correct URLs
    - Downloading ZIP files
    - Extracting and parsing CSV data
    - Retry logic for failed downloads
    """
    
    def __init__(self, base_url: str | None = None):
        """
        Initialize Binance Data Client.
        
        Args:
            base_url: Base URL for Binance data (defaults to settings)
        """
        self.base_url = base_url or settings.BINANCE_DATA_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Bitcoin-Market-Intelligence/0.1.0)"
        })
    
    def construct_url(
        self,
        symbol: str,
        interval: str,
        year: int,
        month: int,
        data_type: str = "klines"
    ) -> str:
        """
        Construct URL for monthly data file.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Time interval ('1m', '5m', '15m', '1h', '4h', '1d')
            year: Year (e.g., 2024)
            month: Month (1-12)
            data_type: Data type (default 'klines' for OHLCV)
            
        Returns:
            Full URL to ZIP file
            
        Example:
            https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01.zip
        """
        month_str = f"{month:02d}"  # Zero-pad month
        filename = f"{symbol}-{interval}-{year}-{month_str}.zip"
        
        url = (
            f"{self.base_url}/data/spot/monthly/{data_type}/"
            f"{symbol}/{interval}/{filename}"
        )
        
        return url
    
    def download_month(
        self,
        symbol: str,
        interval: str,
        year: int,
        month: int,
        timeout: int = 60
    ) -> pd.DataFrame:
        """
        Download and parse data for one month.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            year: Year
            month: Month (1-12)
            timeout: Request timeout in seconds
            
        Returns:
            DataFrame with OHLCV data
            
        Raises:
            DataDownloadError: If download fails
            DataParsingError: If CSV parsing fails
            
        CSV Columns (from Binance):
            0: Open time (timestamp)
            1: Open
            2: High
            3: Low
            4: Close
            5: Volume
            6: Close time
            7: Quote asset volume
            8: Number of trades
            9: Taker buy base asset volume
            10: Taker buy quote asset volume
            11: Ignore
        """
        url = self.construct_url(symbol, interval, year, month)
        
        try:
            logger.info(f"📥 Downloading {symbol} {interval} {year}-{month:02d}", url=url)
            
            # Download ZIP file
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Extract CSV from ZIP
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                # Get first CSV file in ZIP
                csv_filename = zip_file.namelist()[0]
                
                with zip_file.open(csv_filename) as csv_file:
                    # Parse CSV
                    df = pd.read_csv(
                        csv_file,
                        header=None,
                        names=[
                            "open_time", "open", "high", "low", "close", "volume",
                            "close_time", "quote_volume", "trades",
                            "taker_buy_base", "taker_buy_quote", "ignore"
                        ]
                    )
            
            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
            
            # Select relevant columns
            df = df[[
                "timestamp", "open", "high", "low", "close", "volume"
            ]].copy()
            
            # Convert to numeric (in case of string types)
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # Drop any NaN rows
            df = df.dropna()
            
            logger.info(
                f"✅ Downloaded {len(df)} rows",
                symbol=symbol,
                interval=interval,
                month=f"{year}-{month:02d}"
            )
            
            return df
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise DataDownloadError(
                    f"Data not found for {symbol} {interval} {year}-{month:02d}",
                    details={"url": url, "status_code": 404}
                )
            else:
                raise DataDownloadError(
                    f"HTTP error downloading data: {e}",
                    details={"url": url, "status_code": e.response.status_code}
                )
                
        except zipfile.BadZipFile as e:
            raise DataParsingError(
                f"Invalid ZIP file: {e}",
                details={"url": url}
            )
            
        except Exception as e:
            raise DataDownloadError(
                f"Failed to download data: {str(e)}",
                details={"url": url, "error_type": type(e).__name__}
            )
    
    def download_date_range(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        show_progress: bool = True
    ) -> pd.DataFrame:
        """
        Download data for a date range (multiple months).
        
        Args:
            symbol: Trading pair
            interval: Time interval
            start: Start date
            end: End date
            show_progress: Show progress bar
            
        Returns:
            Concatenated DataFrame with all data
            
        Example:
            >>> client = BinanceDataClient()
            >>> df = client.download_date_range(
            ...     "BTCUSDT", "1h",
            ...     datetime(2023, 1, 1),
            ...     datetime(2023, 12, 31)
            ... )
            >>> print(f"Downloaded {len(df)} hours of data")
        """
        start = to_utc(start)
        end = to_utc(end)
        
        # Generate list of (year, month) tuples
        months = []
        current = start.replace(day=1)
        
        while current <= end:
            months.append((current.year, current.month))
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        logger.info(
            f"📥 Downloading {len(months)} months of data",
            symbol=symbol,
            interval=interval,
            months=len(months)
        )
        
        # Download each month
        dfs = []
        
        iterator = tqdm(months, desc="Downloading") if show_progress else months
        
        for year, month in iterator:
            try:
                df_month = self.download_month(symbol, interval, year, month)
                dfs.append(df_month)
                
            except DataDownloadError as e:
                logger.warning(f"⚠️ Skipping {year}-{month:02d}: {e.message}")
                continue
        
        if not dfs:
            raise DataDownloadError(
                f"No data downloaded for {symbol} {interval}",
                details={"start": start.isoformat(), "end": end.isoformat()}
            )
        
        # Concatenate all months
        df_all = pd.concat(dfs, ignore_index=True)
        
        # Filter to exact date range
        df_all = df_all[
            (df_all["timestamp"] >= start) & (df_all["timestamp"] <= end)
        ].copy()
        
        # Sort by timestamp
        df_all = df_all.sort_values("timestamp").reset_index(drop=True)
        
        logger.info(
            f"✅ Downloaded total {len(df_all)} rows",
            symbol=symbol,
            interval=interval,
            start=start.date(),
            end=end.date()
        )
        
        return df_all
    
    def get_latest_available_month(self, symbol: str, interval: str) -> tuple[int, int]:
        """
        Find the latest available month with data.
        
        This tries the current month and goes backwards until data is found.
        
        Args:
            symbol: Trading pair
            interval: Time interval
            
        Returns:
            Tuple of (year, month) with latest data
            
        Raises:
            DataDownloadError: If no data found in last 12 months
        """
        now = datetime.utcnow()
        
        for i in range(12):  # Try last 12 months
            check_date = now - timedelta(days=30 * i)
            year = check_date.year
            month = check_date.month
            
            try:
                # Try to download (just check if exists)
                url = self.construct_url(symbol, interval, year, month)
                response = self.session.head(url, timeout=5)
                
                if response.status_code == 200:
                    logger.info(
                        f"✅ Latest data available: {year}-{month:02d}",
                        symbol=symbol,
                        interval=interval
                    )
                    return (year, month)
                    
            except Exception:
                continue
        
        raise DataDownloadError(
            f"No data found for {symbol} {interval} in last 12 months"
        )
    
    def save_to_csv(
        self,
        df: pd.DataFrame,
        output_path: Path | str,
        compress: bool = False
    ) -> None:
        """
        Save DataFrame to CSV file.
        
        Args:
            df: DataFrame to save
            output_path: Output file path
            compress: If True, save as .csv.gz (compressed)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if compress:
            if not str(output_path).endswith(".gz"):
                output_path = Path(str(output_path) + ".gz")
            df.to_csv(output_path, index=False, compression="gzip")
        else:
            df.to_csv(output_path, index=False)
        
        logger.info(f"💾 Saved to {output_path}", rows=len(df))
