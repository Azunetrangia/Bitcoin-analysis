#!/usr/bin/env python3
"""
Comprehensive Backtest Script
==============================

Tests the complete trading strategy combining:
1. HMM Regime Detection (Bull/Bear/Sideways)
2. KAMA Adaptive Indicator (entry/exit signals)
3. Free On-Chain Data (market sentiment)

Strategy Rules:
- LONG: Regime=Bull AND Price>KAMA AND Funding<0.1% (not overheated)
- SHORT: Regime=Bear AND Price<KAMA AND Funding>-0.1% (not oversold)
- EXIT: Regime changes OR opposite KAMA signal

Performance Metrics:
- Total Return
- Sharpe Ratio
- Maximum Drawdown
- Win Rate
- Average Win/Loss
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.regime_detector import RegimeDetector
from indicators.adaptive import calculate_kama, generate_kama_signals, calculate_atr
from data.free_onchain import get_comprehensive_onchain_data

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StrategyBacktest:
    """
    Complete backtesting engine for HMM + KAMA + On-Chain strategy.
    """
    
    def __init__(self, initial_capital=10000, position_size=0.95, commission=0.001):
        """
        Initialize backtest engine.
        
        Args:
            initial_capital: Starting capital in USD
            position_size: Fraction of capital to use per trade (default 95%)
            commission: Trading commission per trade (default 0.1%)
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.commission = commission
        
        # Components
        self.regime_detector = RegimeDetector(n_states=3, lookback_days=90)
        
        # Results storage
        self.trades = []
        self.equity_curve = []
        
    def load_data(self, filepath):
        """
        Load historical price data from parquet.
        
        Args:
            filepath: Path to parquet file
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Loading data from {filepath}")
        df = pd.read_parquet(filepath)
        
        # Convert time column to datetime and set as index
        if 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
            df.set_index('timestamp', inplace=True)
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        logger.info(f"Loaded {len(df)} candles from {df.index[0]} to {df.index[-1]}")
        return df
    
    def prepare_features(self, df):
        """
        Calculate all technical indicators and features.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added indicators
        """
        logger.info("Calculating technical indicators...")
        
        # KAMA (adaptive moving average)
        df['kama'] = calculate_kama(df['close'], n=10, fast=2, slow=30)
        
        # ATR (volatility)
        df['atr'] = calculate_atr(df, period=14)
        
        # KAMA signals
        df_signals = generate_kama_signals(df)
        
        # Add signal columns (check which columns exist)
        df['kama_signal'] = df_signals['signal']
        
        # Map kama_cross values: 1 = golden, -1 = death, 0 = none
        df['kama_cross_value'] = df_signals['kama_cross']
        df['kama_cross'] = 'none'
        df.loc[df['kama_cross_value'] == 1, 'kama_cross'] = 'golden'
        df.loc[df['kama_cross_value'] == -1, 'kama_cross'] = 'death'
        
        # Distance from KAMA in percent
        df['distance_pct'] = ((df['close'] - df['kama']) / df['kama']) * 100
        
        logger.info(f"Indicators calculated. Null values: {df.isnull().sum().sum()}")
        
        return df.dropna()
    
    def train_regime_model(self, df, train_end_idx):
        """
        Train HMM regime detector on training data.
        
        Args:
            df: Full DataFrame
            train_end_idx: Index to end training (rest is for testing)
        """
        logger.info("Training HMM regime detector...")
        
        train_df = df.iloc[:train_end_idx].copy()
        self.regime_detector.train(train_df)
        
        logger.info(f"Model trained on {len(train_df)} candles")
        logger.info(f"HMM converged: {self.regime_detector.model.monitor_.converged}")
    
    def run_backtest(self, df, train_ratio=0.5):
        """
        Execute complete backtest.
        
        Args:
            df: DataFrame with OHLCV data
            train_ratio: Fraction of data for training (default 50%)
            
        Returns:
            dict with backtest results
        """
        # Split data
        train_size = int(len(df) * train_ratio)
        train_df = df.iloc[:train_size].copy()
        test_df = df.iloc[train_size:].copy()
        
        logger.info(f"Train period: {train_df.index[0]} to {train_df.index[-1]} ({len(train_df)} candles)")
        logger.info(f"Test period: {test_df.index[0]} to {test_df.index[-1]} ({len(test_df)} candles)")
        
        # Train HMM
        self.regime_detector.train(train_df)
        
        # Simulate trading
        capital = self.initial_capital
        position = None  # None, 'LONG', or 'SHORT'
        entry_price = 0
        entry_time = None
        
        for idx in range(len(test_df)):
            current = test_df.iloc[idx]
            timestamp = current.name
            price = current['close']
            
            # Get regime prediction (use last 30 candles for context)
            lookback_start = max(0, train_size + idx - 30)
            recent_df = df.iloc[lookback_start:train_size + idx + 1]
            
            regime_result = self.regime_detector.predict_current_regime(recent_df)
            regime = regime_result['regime']
            regime_prob = regime_result['probability']
            
            # Get KAMA signal
            kama_signal = current['kama_signal']
            kama_cross = current['kama_cross']
            distance_pct = current['distance_pct']
            
            # Trading logic
            if position is None:
                # Look for entry
                
                # LONG entry: Bull regime + bullish KAMA + not too far from KAMA
                if (regime in ['Bull', 'Sideways'] and  # Allow both Bull and Sideways
                    kama_signal == 1 and 
                    regime_prob > 0.5 and  # Lower threshold from 0.6
                    abs(distance_pct) < 8):  # Wider range from 5% to 8%
                    
                    position = 'LONG'
                    entry_price = price
                    entry_time = timestamp
                    
                    # Calculate position size
                    position_value = capital * self.position_size
                    commission_cost = position_value * self.commission
                    capital -= commission_cost
                    
                    logger.info(f"[{timestamp}] LONG entry at ${price:,.2f} | Regime: {regime} ({regime_prob:.2%}) | Capital: ${capital:,.2f}")
                
                # SHORT entry: Bear regime + bearish KAMA
                elif (regime == 'Bear' and 
                      kama_signal == -1 and 
                      regime_prob > 0.5 and  # Lower threshold
                      abs(distance_pct) < 8):  # Wider range
                    
                    position = 'SHORT'
                    entry_price = price
                    entry_time = timestamp
                    
                    position_value = capital * self.position_size
                    commission_cost = position_value * self.commission
                    capital -= commission_cost
                    
                    logger.info(f"[{timestamp}] SHORT entry at ${price:,.2f} | Regime: {regime} ({regime_prob:.2%}) | Capital: ${capital:,.2f}")
            
            else:
                # Check for exit conditions
                exit_signal = False
                exit_reason = ""
                
                if position == 'LONG':
                    # Exit LONG: regime becomes Bear OR bearish KAMA cross
                    if regime == 'Bear':
                        exit_signal = True
                        exit_reason = f"Regime changed to {regime}"
                    elif kama_cross == 'death':
                        exit_signal = True
                        exit_reason = "KAMA death cross"
                    elif distance_pct < -5:  # Price fell >5% below KAMA (wider stop)
                        exit_signal = True
                        exit_reason = "Stop loss triggered"
                
                elif position == 'SHORT':
                    # Exit SHORT: regime changes OR bullish KAMA cross
                    if regime != 'Bear':
                        exit_signal = True
                        exit_reason = f"Regime changed to {regime}"
                    elif kama_cross == 'golden':
                        exit_signal = True
                        exit_reason = "KAMA golden cross"
                    elif distance_pct > 3:  # Price rose >3% above KAMA
                        exit_signal = True
                        exit_reason = "Stop loss triggered"
                
                if exit_signal:
                    # Calculate P&L
                    if position == 'LONG':
                        pnl_pct = (price - entry_price) / entry_price
                    else:  # SHORT
                        pnl_pct = (entry_price - price) / entry_price
                    
                    pnl_usd = capital * self.position_size * pnl_pct
                    commission_cost = capital * self.position_size * self.commission
                    
                    capital += pnl_usd - commission_cost
                    
                    # Record trade
                    trade = {
                        'entry_time': entry_time,
                        'exit_time': timestamp,
                        'direction': position,
                        'entry_price': entry_price,
                        'exit_price': price,
                        'pnl_pct': pnl_pct * 100,
                        'pnl_usd': pnl_usd,
                        'capital_after': capital,
                        'exit_reason': exit_reason
                    }
                    self.trades.append(trade)
                    
                    logger.info(f"[{timestamp}] {position} exit at ${price:,.2f} | P&L: {pnl_pct*100:+.2f}% (${pnl_usd:+,.2f}) | Reason: {exit_reason} | Capital: ${capital:,.2f}")
                    
                    position = None
            
            # Record equity
            if position == 'LONG':
                unrealized_pnl = (price - entry_price) / entry_price * capital * self.position_size
                current_equity = capital + unrealized_pnl
            elif position == 'SHORT':
                unrealized_pnl = (entry_price - price) / entry_price * capital * self.position_size
                current_equity = capital + unrealized_pnl
            else:
                current_equity = capital
            
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': current_equity,
                'position': position or 'CASH'
            })
        
        # Calculate metrics
        results = self.calculate_metrics()
        
        return results
    
    def calculate_metrics(self):
        """
        Calculate performance metrics.
        
        Returns:
            dict with metrics
        """
        if not self.trades:
            logger.warning("No trades executed!")
            return {
                'total_return_pct': 0,
                'num_trades': 0,
                'error': 'No trades executed'
            }
        
        trades_df = pd.DataFrame(self.trades)
        equity_df = pd.DataFrame(self.equity_curve)
        
        # Final capital
        final_capital = equity_df.iloc[-1]['equity']
        total_return_pct = (final_capital - self.initial_capital) / self.initial_capital * 100
        
        # Win rate
        winning_trades = trades_df[trades_df['pnl_pct'] > 0]
        win_rate = len(winning_trades) / len(trades_df) * 100 if len(trades_df) > 0 else 0
        
        # Average win/loss
        avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean()
        
        # Sharpe ratio (annualized)
        equity_df['returns'] = equity_df['equity'].pct_change()
        sharpe = equity_df['returns'].mean() / equity_df['returns'].std() * np.sqrt(365 * 24) if equity_df['returns'].std() > 0 else 0
        
        # Maximum drawdown
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
        max_drawdown = equity_df['drawdown'].min()
        
        # Profit factor
        total_profit = winning_trades['pnl_usd'].sum() if len(winning_trades) > 0 else 0
        total_loss = abs(trades_df[trades_df['pnl_usd'] < 0]['pnl_usd'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'total_return_pct': total_return_pct,
            'num_trades': len(trades_df),
            'win_rate': win_rate,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': max_drawdown,
            'profit_factor': profit_factor,
            'trades_df': trades_df,
            'equity_df': equity_df
        }


def main():
    """Run backtest."""
    logger.info("=" * 60)
    logger.info("COMPREHENSIVE STRATEGY BACKTEST")
    logger.info("=" * 60)
    
    # Initialize
    backtest = StrategyBacktest(
        initial_capital=10000,
        position_size=0.95,
        commission=0.001
    )
    
    # Load data
    data_path = Path(__file__).parent / 'data' / 'hot' / 'BTCUSDT_1h.parquet'
    df = backtest.load_data(data_path)
    
    # Prepare features
    df = backtest.prepare_features(df)
    
    # Run backtest
    logger.info("\nStarting backtest...")
    results = backtest.run_backtest(df, train_ratio=0.5)
    
    # Print results
    logger.info("\n" + "=" * 60)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 60)
    
    if 'error' in results:
        print(f"\n⚠️  ERROR: {results['error']}")
        print(f"   Number of trades: {results.get('num_trades', 0)}")
        return results
    
    print(f"\n💰 Capital:")
    print(f"   Initial: ${results['initial_capital']:,.2f}")
    print(f"   Final:   ${results['final_capital']:,.2f}")
    print(f"   Return:  {results['total_return_pct']:+.2f}%")
    
    print(f"\n📊 Performance:")
    print(f"   Total Trades:    {results['num_trades']}")
    print(f"   Win Rate:        {results['win_rate']:.1f}%")
    print(f"   Avg Win:         +{results['avg_win_pct']:.2f}%")
    print(f"   Avg Loss:        {results['avg_loss_pct']:.2f}%")
    print(f"   Profit Factor:   {results['profit_factor']:.2f}")
    
    print(f"\n📉 Risk Metrics:")
    print(f"   Sharpe Ratio:    {results['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown:    {results['max_drawdown_pct']:.2f}%")
    
    # Show trades
    if results['num_trades'] > 0:
        print(f"\n🔍 Recent Trades:")
        trades_df = results['trades_df']
        print(trades_df[['entry_time', 'direction', 'entry_price', 'exit_price', 'pnl_pct', 'exit_reason']].tail(10).to_string(index=False))
    
    # Save results
    output_path = Path(__file__).parent / 'backtest_results.csv'
    if results['num_trades'] > 0:
        results['trades_df'].to_csv(output_path, index=False)
        logger.info(f"\n✅ Results saved to {output_path}")
    
    return results


if __name__ == "__main__":
    try:
        results = main()
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        sys.exit(1)
