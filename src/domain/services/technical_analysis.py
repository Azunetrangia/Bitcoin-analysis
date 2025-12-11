"""
Technical Analysis Service
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Domain service for calculating technical indicators.

This is a pure domain service with no external dependencies.
All calculations are based on standard technical analysis formulas.

Indicators:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- ATR (Average True Range)
- SMA/EMA (Simple/Exponential Moving Averages)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple
from src.shared.exceptions.custom_exceptions import TechnicalIndicatorError
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class TechnicalAnalysisService:
    """
    Domain service for technical indicator calculations.
    
    This service is stateless and contains pure calculation logic.
    No external dependencies (database, API, etc.)
    """
    
    def calculate_rsi(
        self, 
        prices: pd.Series, 
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        RSI measures momentum on a scale of 0-100.
        - RSI > 70: Overbought (potential sell signal)
        - RSI < 30: Oversold (potential buy signal)
        
        Args:
            prices: Close price series
            period: RSI period (default 14)
            
        Returns:
            RSI values (0-100)
            
        Raises:
            TechnicalIndicatorError: If calculation fails
            
        Formula:
            RSI = 100 - (100 / (1 + RS))
            RS = Average Gain / Average Loss
        """
        try:
            if len(prices) < period:
                raise TechnicalIndicatorError(
                    f"Insufficient data for RSI calculation (need {period}, got {len(prices)})"
                )
            
            # Calculate price changes
            delta = prices.diff()
            
            # Separate gains and losses
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            # Calculate average gains and losses (Wilder's smoothing)
            avg_gains = gains.rolling(window=period, min_periods=period).mean()
            avg_losses = losses.rolling(window=period, min_periods=period).mean()
            
            # Calculate RS and RSI
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            logger.debug(f"RSI calculated", period=period, values=len(rsi.dropna()))
            
            return rsi
            
        except Exception as e:
            raise TechnicalIndicatorError(
                f"RSI calculation failed: {str(e)}",
                details={"period": period, "data_length": len(prices)}
            )
    
    def calculate_macd(
        self,
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        MACD is a trend-following momentum indicator.
        - MACD line crossing above signal: Bullish
        - MACD line crossing below signal: Bearish
        
        Args:
            prices: Close price series
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line EMA period (default 9)
            
        Returns:
            Dictionary with keys: 'macd', 'signal', 'histogram'
            
        Raises:
            TechnicalIndicatorError: If calculation fails
        """
        try:
            if len(prices) < slow_period:
                raise TechnicalIndicatorError(
                    f"Insufficient data for MACD (need {slow_period}, got {len(prices)})"
                )
            
            # Calculate EMAs
            ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
            ema_slow = prices.ewm(span=slow_period, adjust=False).mean()
            
            # MACD line
            macd_line = ema_fast - ema_slow
            
            # Signal line (EMA of MACD)
            signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
            
            # MACD histogram
            histogram = macd_line - signal_line
            
            logger.debug(
                f"MACD calculated",
                fast=fast_period,
                slow=slow_period,
                signal=signal_period
            )
            
            return {
                "macd": macd_line,
                "signal": signal_line,
                "histogram": histogram,
            }
            
        except Exception as e:
            raise TechnicalIndicatorError(
                f"MACD calculation failed: {str(e)}",
                details={
                    "fast_period": fast_period,
                    "slow_period": slow_period,
                    "signal_period": signal_period,
                }
            )
    
    def calculate_bollinger_bands(
        self,
        prices: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands.
        
        Bollinger Bands measure volatility and identify overbought/oversold levels.
        - Price touching upper band: Overbought
        - Price touching lower band: Oversold
        
        Args:
            prices: Close price series
            period: Moving average period (default 20)
            std_dev: Standard deviation multiplier (default 2.0)
            
        Returns:
            Dictionary with keys: 'upper', 'middle', 'lower', 'bandwidth'
            
        Raises:
            TechnicalIndicatorError: If calculation fails
        """
        try:
            if len(prices) < period:
                raise TechnicalIndicatorError(
                    f"Insufficient data for Bollinger Bands (need {period}, got {len(prices)})"
                )
            
            # Middle band (SMA)
            middle_band = prices.rolling(window=period).mean()
            
            # Standard deviation
            rolling_std = prices.rolling(window=period).std()
            
            # Upper and lower bands
            upper_band = middle_band + (rolling_std * std_dev)
            lower_band = middle_band - (rolling_std * std_dev)
            
            # Bandwidth (normalized width)
            bandwidth = (upper_band - lower_band) / middle_band
            
            logger.debug(
                f"Bollinger Bands calculated",
                period=period,
                std_dev=std_dev
            )
            
            return {
                "upper": upper_band,
                "middle": middle_band,
                "lower": lower_band,
                "bandwidth": bandwidth,
            }
            
        except Exception as e:
            raise TechnicalIndicatorError(
                f"Bollinger Bands calculation failed: {str(e)}",
                details={"period": period, "std_dev": std_dev}
            )
    
    def calculate_atr(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Average True Range (ATR).
        
        ATR measures market volatility (not direction).
        Higher ATR = Higher volatility
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            period: ATR period (default 14)
            
        Returns:
            ATR values
            
        Raises:
            TechnicalIndicatorError: If calculation fails
            
        Formula:
            TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
            ATR = Moving average of TR
        """
        try:
            if len(high) < period:
                raise TechnicalIndicatorError(
                    f"Insufficient data for ATR (need {period}, got {len(high)})"
                )
            
            # Calculate True Range components
            high_low = high - low
            high_close = (high - close.shift(1)).abs()
            low_close = (low - close.shift(1)).abs()
            
            # True Range (max of the three)
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            
            # ATR (Wilder's smoothing)
            atr = tr.rolling(window=period, min_periods=period).mean()
            
            logger.debug(f"ATR calculated", period=period)
            
            return atr
            
        except Exception as e:
            raise TechnicalIndicatorError(
                f"ATR calculation failed: {str(e)}",
                details={"period": period}
            )
    
    def calculate_sma(
        self,
        prices: pd.Series,
        period: int
    ) -> pd.Series:
        """
        Calculate Simple Moving Average (SMA).
        
        Args:
            prices: Price series
            period: Moving average period
            
        Returns:
            SMA values
        """
        return prices.rolling(window=period).mean()
    
    def calculate_ema(
        self,
        prices: pd.Series,
        period: int
    ) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA).
        
        Args:
            prices: Price series
            period: Moving average period
            
        Returns:
            EMA values
        """
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate_all_indicators(
        self,
        df: pd.DataFrame,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
        bb_std: float = 2.0,
        atr_period: int = 14
    ) -> pd.DataFrame:
        """
        Calculate all technical indicators at once.
        
        This is a convenience method for batch calculation.
        
        Args:
            df: DataFrame with OHLCV columns
            rsi_period: RSI period
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
            bb_period: Bollinger Bands period
            bb_std: Bollinger Bands std dev multiplier
            atr_period: ATR period
            
        Returns:
            DataFrame with all original columns + indicator columns
            
        Example:
            >>> ta = TechnicalAnalysisService()
            >>> df_with_indicators = ta.calculate_all_indicators(df)
            >>> df_with_indicators[['close', 'rsi', 'macd', 'bb_upper']].tail()
        """
        result = df.copy()
        
        try:
            # RSI
            result["rsi"] = self.calculate_rsi(df["close"], period=rsi_period)
            
            # MACD
            macd = self.calculate_macd(
                df["close"],
                fast_period=macd_fast,
                slow_period=macd_slow,
                signal_period=macd_signal
            )
            result["macd"] = macd["macd"]
            result["macd_signal"] = macd["signal"]
            result["macd_histogram"] = macd["histogram"]
            
            # Bollinger Bands
            bb = self.calculate_bollinger_bands(
                df["close"],
                period=bb_period,
                std_dev=bb_std
            )
            result["bb_upper"] = bb["upper"]
            result["bb_middle"] = bb["middle"]
            result["bb_lower"] = bb["lower"]
            result["bb_bandwidth"] = bb["bandwidth"]
            
            # ATR
            result["atr"] = self.calculate_atr(
                df["high"],
                df["low"],
                df["close"],
                period=atr_period
            )
            
            # Moving averages
            result["sma_20"] = self.calculate_sma(df["close"], period=20)
            result["sma_50"] = self.calculate_sma(df["close"], period=50)
            result["ema_20"] = self.calculate_ema(df["close"], period=20)
            
            logger.info(
                f"✅ All technical indicators calculated",
                indicators=11,
                rows=len(result)
            )
            
            return result
            
        except Exception as e:
            raise TechnicalIndicatorError(
                f"Batch indicator calculation failed: {str(e)}",
                details={"rows": len(df)}
            )
    
    def extract_features_for_regime_classification(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Extract features specifically for regime classification.
        
        This creates a feature set optimized for GMM clustering.
        
        Args:
            df: DataFrame with OHLCV columns
            
        Returns:
            DataFrame with feature columns:
            - returns: Log returns
            - volatility: Rolling volatility (20-period)
            - rsi: RSI (14-period)
            - macd_signal: MACD signal line
            - atr_normalized: ATR / Close (normalized)
            
        Example:
            >>> ta = TechnicalAnalysisService()
            >>> features = ta.extract_features_for_regime_classification(df)
            >>> # Use features for GMM fitting
        """
        result = pd.DataFrame(index=df.index)
        
        try:
            # Log returns (price momentum)
            result["returns"] = np.log(df["close"] / df["close"].shift(1))
            
            # Rolling volatility (20-period standard deviation of returns)
            result["volatility"] = result["returns"].rolling(window=20).std()
            
            # RSI (momentum indicator)
            result["rsi"] = self.calculate_rsi(df["close"], period=14)
            
            # MACD histogram (trend strength)
            macd = self.calculate_macd(df["close"])
            result["macd_histogram"] = macd["histogram"]
            
            # ATR normalized by price (volatility indicator)
            atr = self.calculate_atr(df["high"], df["low"], df["close"], period=14)
            result["atr_normalized"] = atr / df["close"]
            
            # Volume change (liquidity indicator)
            result["volume_change"] = df["volume"].pct_change()
            
            # Drop NaN values (from rolling calculations)
            result = result.dropna()
            
            logger.info(
                f"✅ Regime features extracted",
                features=len(result.columns),
                rows=len(result)
            )
            
            return result
            
        except Exception as e:
            raise TechnicalIndicatorError(
                f"Feature extraction failed: {str(e)}",
                details={"rows": len(df)}
            )
