"""
Adaptive Technical Indicators
Kaufman Adaptive Moving Average (KAMA) and ATR-based normalization
"""

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def calculate_kama(prices, n=10, fast=2, slow=30):
    """
    Calculate Kaufman Adaptive Moving Average (KAMA).
    
    KAMA adjusts its sensitivity based on market efficiency:
    - Fast in trending markets (high efficiency)
    - Slow in choppy markets (low efficiency)
    
    Args:
        prices: pandas Series of prices
        n: Period for efficiency ratio calculation (default 10)
        fast: Fast EMA period (default 2)
        slow: Slow EMA period (default 30)
        
    Returns:
        pandas Series with KAMA values
    """
    prices = pd.Series(prices).astype(float)
    
    # Calculate Efficiency Ratio (ER)
    # ER = |Total Price Change| / Sum of |Individual Changes|
    change = abs(prices - prices.shift(n))
    volatility = abs(prices - prices.shift(1)).rolling(n).sum()
    
    # Avoid division by zero
    volatility = volatility.replace(0, np.nan)
    er = change / volatility
    er = er.fillna(0)
    
    # Calculate Smoothing Constant (SC)
    # SC = [ER * (fast_sc - slow_sc) + slow_sc]^2
    fast_sc = 2 / (fast + 1)
    slow_sc = 2 / (slow + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
    
    # Calculate KAMA recursively
    kama = pd.Series(index=prices.index, dtype=float)
    
    # Initialize first value
    kama.iloc[n] = prices.iloc[n]
    
    # Recursive calculation: KAMA[i] = KAMA[i-1] + SC[i] * (Price[i] - KAMA[i-1])
    for i in range(n + 1, len(prices)):
        kama.iloc[i] = kama.iloc[i-1] + sc.iloc[i] * (prices.iloc[i] - kama.iloc[i-1])
    
    return kama


def calculate_atr(df, period=14):
    """
    Calculate Average True Range (ATR) for volatility measurement.
    
    Args:
        df: DataFrame with high, low, close columns
        period: ATR period (default 14)
        
    Returns:
        pandas Series with ATR values
    """
    df = df.copy()
    
    # True Range components
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = abs(df['high'] - df['close'].shift(1))
    df['l-pc'] = abs(df['low'] - df['close'].shift(1))
    
    # True Range = max of three components
    df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    
    # ATR = Moving Average of True Range
    atr = df['tr'].rolling(period).mean()
    
    return atr


def calculate_atr_percent(df, period=14):
    """
    Calculate ATR as percentage of price for normalization.
    
    Args:
        df: DataFrame with OHLC data
        period: ATR period
        
    Returns:
        pandas Series with ATR %
    """
    atr = calculate_atr(df, period)
    atr_percent = (atr / df['close']) * 100
    
    return atr_percent


def generate_kama_signals(df, kama_period=10, fast=2, slow=30):
    """
    Generate trading signals based on KAMA.
    
    Signals:
    - Buy: Price crosses above KAMA
    - Sell: Price crosses below KAMA
    
    Args:
        df: DataFrame with OHLCV data
        kama_period: KAMA calculation period
        fast: Fast smoothing constant
        slow: Slow smoothing constant
        
    Returns:
        DataFrame with signals
    """
    df = df.copy()
    
    # Calculate KAMA
    df['kama'] = calculate_kama(df['close'], n=kama_period, fast=fast, slow=slow)
    
    # Calculate ATR for context
    df['atr'] = calculate_atr(df, period=14)
    df['atr_pct'] = calculate_atr_percent(df, period=14)
    
    # Generate signals
    df['price_vs_kama'] = df['close'] - df['kama']
    df['signal'] = 0  # 0 = neutral
    
    # Price above KAMA = bullish
    df.loc[df['close'] > df['kama'], 'signal'] = 1
    
    # Price below KAMA = bearish
    df.loc[df['close'] < df['kama'], 'signal'] = -1
    
    # Detect crossovers
    df['kama_cross'] = 0
    
    # Bullish cross (price crosses above KAMA)
    df.loc[(df['signal'] == 1) & (df['signal'].shift(1) == -1), 'kama_cross'] = 1
    
    # Bearish cross (price crosses below KAMA)
    df.loc[(df['signal'] == -1) & (df['signal'].shift(1) == 1), 'kama_cross'] = -1
    
    # Calculate distance from KAMA in ATR units (for risk management)
    df['distance_atr'] = abs(df['price_vs_kama']) / df['atr']
    
    return df


def adaptive_stop_loss(current_price, entry_price, atr, multiplier=2.0):
    """
    Calculate adaptive stop loss based on ATR.
    
    Args:
        current_price: Current market price
        entry_price: Entry price
        atr: Current ATR value
        multiplier: ATR multiplier for stop distance (default 2.0)
        
    Returns:
        Stop loss price
    """
    if current_price > entry_price:
        # Long position
        stop_loss = entry_price - (atr * multiplier)
    else:
        # Short position
        stop_loss = entry_price + (atr * multiplier)
    
    return stop_loss


def adaptive_take_profit(entry_price, atr, risk_reward_ratio=2.0, multiplier=2.0):
    """
    Calculate adaptive take profit based on ATR and risk-reward ratio.
    
    Args:
        entry_price: Entry price
        atr: Current ATR value
        risk_reward_ratio: Desired risk:reward ratio (default 2.0)
        multiplier: ATR multiplier for stop distance
        
    Returns:
        Take profit price
    """
    stop_distance = atr * multiplier
    profit_distance = stop_distance * risk_reward_ratio
    
    # Assuming long position (adjust for short)
    take_profit = entry_price + profit_distance
    
    return take_profit


class KAMAStrategy:
    """
    Complete KAMA-based trading strategy with adaptive parameters.
    """
    
    def __init__(self, kama_period=10, fast=2, slow=30, atr_multiplier=2.0):
        """
        Initialize KAMA strategy.
        
        Args:
            kama_period: KAMA calculation period
            fast: Fast EMA period
            slow: Slow EMA period
            atr_multiplier: ATR multiplier for stops
        """
        self.kama_period = kama_period
        self.fast = fast
        self.slow = slow
        self.atr_multiplier = atr_multiplier
        
    def analyze(self, df):
        """
        Analyze market with KAMA strategy.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            dict with analysis results
        """
        # Generate signals
        df_signals = generate_kama_signals(
            df,
            kama_period=self.kama_period,
            fast=self.fast,
            slow=self.slow
        )
        
        # Get current values
        current = df_signals.iloc[-1]
        
        # Determine action
        if current['kama_cross'] == 1:
            action = "STRONG_BUY"
        elif current['kama_cross'] == -1:
            action = "STRONG_SELL"
        elif current['signal'] == 1:
            action = "BUY"
        elif current['signal'] == -1:
            action = "SELL"
        else:
            action = "HOLD"
        
        # Calculate risk management levels
        entry_price = current['close']
        atr = current['atr']
        
        stop_loss = adaptive_stop_loss(
            current['close'],
            entry_price,
            atr,
            self.atr_multiplier
        )
        
        take_profit = adaptive_take_profit(
            entry_price,
            atr,
            risk_reward_ratio=2.0,
            multiplier=self.atr_multiplier
        )
        
        return {
            'action': action,
            'price': float(current['close']),
            'kama': float(current['kama']),
            'atr': float(atr),
            'atr_pct': float(current['atr_pct']),
            'distance_atr': float(current['distance_atr']),
            'stop_loss': float(stop_loss),
            'take_profit': float(take_profit),
            'risk_reward_ratio': float((take_profit - entry_price) / (entry_price - stop_loss))
        }


if __name__ == "__main__":
    print("Adaptive Indicators Module")
    print("=" * 50)
    print("Available functions:")
    print("- calculate_kama(prices, n, fast, slow)")
    print("- calculate_atr(df, period)")
    print("- generate_kama_signals(df)")
    print("- KAMAStrategy class for complete analysis")
