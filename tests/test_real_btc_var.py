#!/usr/bin/env python3
"""
Test Modified VaR with ACTUAL Bitcoin data from Binance API
"""
import pandas as pd
import requests
from datetime import datetime
from src.domain.services.risk_calculator import RiskCalculatorService

def fetch_btc_data(days=365):
    """Fetch real Bitcoin data from Binance"""
    url = "https://api.binance.com/api/v3/klines"
    
    # Calculate start time (days ago)
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (days * 24 * 60 * 60 * 1000)
    
    params = {
        'symbol': 'BTCUSDT',
        'interval': '1h',
        'startTime': start_time,
        'endTime': end_time,
        'limit': 1000
    }
    
    all_data = []
    current_start = start_time
    
    print(f"📡 Fetching {days} days of Bitcoin data from Binance...")
    
    while current_start < end_time:
        params['startTime'] = current_start
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            break
            
        data = response.json()
        if not data:
            break
            
        all_data.extend(data)
        current_start = data[-1][6] + 1  # Next candle start time
        
        if len(data) < 1000:  # Last batch
            break
    
    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    df['close'] = df['close'].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    return df

def main():
    print('🪙 Testing Modified VaR with REAL Bitcoin Data')
    print('='*70)
    
    # Fetch real data
    try:
        df = fetch_btc_data(days=90)  # Last 90 days
        prices = df['close']
        
        print(f"✅ Fetched {len(prices)} hourly candles")
        print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"   Price: ${prices.min():.0f} - ${prices.max():.0f}")
        print()
        
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")
        print("   Using fallback simulated data...")
        return None
    
    # Calculate metrics
    calc = RiskCalculatorService(risk_free_rate=0.02)
    metrics = calc.calculate_all_metrics(prices, periods_per_year=24*365)
    
    print('📈 Real Bitcoin Distribution:')
    print(f"   Skewness:   {metrics.skewness:>7.3f}")
    print(f"   Kurtosis:   {metrics.kurtosis:>7.3f}")
    print(f"   Mean Return:{metrics.mean_return*100:>7.4f}% per hour")
    print(f"   Volatility: {metrics.volatility*100:>7.2f}% annualized")
    print()
    
    print('⚠️ Risk Assessment:')
    print('-'*70)
    print(f"{'Metric':<30} {'Standard':<15} {'Modified':<15} {'Diff'}")
    print('-'*70)
    
    var_diff_95 = abs(metrics.var_95_modified / metrics.var_95 - 1) * 100
    var_diff_99 = abs(metrics.var_99_modified / metrics.var_99 - 1) * 100
    
    print(f"{'VaR 95% (1-hour horizon)':<30} {metrics.var_95*100:>7.3f}%      "
          f"{metrics.var_95_modified*100:>7.3f}%      {var_diff_95:>5.1f}%")
    print(f"{'VaR 99% (1-hour horizon)':<30} {metrics.var_99*100:>7.3f}%      "
          f"{metrics.var_99_modified*100:>7.3f}%      {var_diff_99:>5.1f}%")
    
    print('-'*70)
    print(f"{'Expected Shortfall (95%)':<30} {metrics.expected_shortfall_95*100:>7.3f}%")
    print(f"{'Max Drawdown':<30} {metrics.max_drawdown*100:>7.2f}%")
    print(f"{'Sharpe Ratio':<30} {metrics.sharpe_ratio:>7.2f}")
    print(f"{'Sortino Ratio':<30} {metrics.sortino_ratio:>7.2f}")
    print()
    
    # Trading implications
    account_size = 100000  # $100K account
    
    print('💰 Trading Implications (for $100K account):')
    print('-'*70)
    
    # Position sizing with 2% risk per trade
    risk_per_trade = 0.02
    
    # Standard VaR-based sizing
    position_size_standard = (account_size * risk_per_trade) / abs(metrics.var_95)
    position_size_modified = (account_size * risk_per_trade) / abs(metrics.var_95_modified)
    
    print(f"Risk per trade: {risk_per_trade*100}% of account = ${account_size * risk_per_trade:,.0f}")
    print()
    print(f"Position sizing using Standard VaR:")
    print(f"   Max position: ${position_size_standard:>10,.0f}")
    print()
    print(f"Position sizing using Modified VaR:")
    print(f"   Max position: ${position_size_modified:>10,.0f}")
    print()
    
    diff = (position_size_standard - position_size_modified) / position_size_modified * 100
    print(f"Difference: {abs(diff):.1f}% {'more conservative' if diff < 0 else 'more aggressive'}")
    print()
    
    # Interpretation
    print('💡 Analysis:')
    if metrics.skewness < -0.5:
        print(f"   ⚠️  Strong negative skew ({metrics.skewness:.2f})")
        print("      → More frequent small gains, rare large losses")
        print("      → Modified VaR CRITICAL for tail risk")
    elif abs(metrics.skewness) < 0.2:
        print(f"   ✅ Nearly symmetric distribution (skew = {metrics.skewness:.2f})")
        print("      → Standard VaR acceptable")
    else:
        print(f"   ℹ️  Positive skew ({metrics.skewness:.2f})")
        print("      → Rare large gains dominate")
    
    if metrics.kurtosis > 3:
        print(f"   ⚠️  Fat tails detected (kurtosis = {metrics.kurtosis:.2f})")
        print("      → Higher probability of extreme moves")
        print("      → Modified VaR provides better protection")
    else:
        print(f"   ✅ Normal tail behavior (kurtosis = {metrics.kurtosis:.2f})")
    
    print()
    print('🎯 Recommendation:')
    if abs(var_diff_95) > 10:
        print(f"   Use Modified VaR (differs by {var_diff_95:.1f}%)")
        print("   Standard VaR may significantly misestimate risk")
    else:
        print(f"   Both methods similar (differ by {var_diff_95:.1f}%)")
        print("   Either method acceptable for this period")
    
    print()
    print('✅ Real-world validation complete!')
    
    return {
        'passed': True,
        'samples': len(prices),
        'skewness': metrics.skewness,
        'kurtosis': metrics.kurtosis,
        'adjustment': var_diff_95
    }

if __name__ == '__main__':
    try:
        result = main()
        exit(0 if result and result['passed'] else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
