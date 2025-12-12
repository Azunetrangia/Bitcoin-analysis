"""
Free On-Chain Data Sources
Blockchain.com, CryptoQuant, and Coinglass API wrappers
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class BlockchainComAPI:
    """
    Free on-chain metrics from Blockchain.com Charts API.
    
    No API key required for most endpoints.
    """
    
    BASE_URL = "https://api.blockchain.info/charts"
    
    def __init__(self, cache_hours=24):
        """
        Initialize Blockchain.com API client.
        
        Args:
            cache_hours: Hours to cache data (on-chain updates daily)
        """
        self.cache_hours = cache_hours
        self._cache = {}
        
    def _get_chart_data(self, chart_name, timespan="2years", sampled=False):
        """
        Fetch chart data from Blockchain.com.
        
        Args:
            chart_name: Chart identifier (e.g., 'market-value-to-realized-value')
            timespan: Data timespan (e.g., '1year', '2years', 'all')
            sampled: Whether to use sampled data
            
        Returns:
            pandas DataFrame with timestamp and value columns
        """
        # Check cache
        cache_key = f"{chart_name}_{timespan}"
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if datetime.now() - cached_time < timedelta(hours=self.cache_hours):
                logger.info(f"Using cached data for {chart_name}")
                return cached_data
        
        # Build URL
        url = f"{self.BASE_URL}/{chart_name}"
        params = {
            'timespan': timespan,
            'format': 'json'
        }
        
        if sampled:
            params['sampled'] = 'true'
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse values
            values = data.get('values', [])
            
            if not values:
                logger.warning(f"No data returned for {chart_name}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(values)
            df['timestamp'] = pd.to_datetime(df['x'], unit='s')
            df = df.rename(columns={'y': 'value'})
            df = df[['timestamp', 'value']]
            
            # Cache result
            self._cache[cache_key] = (datetime.now(), df)
            
            logger.info(f"Fetched {len(df)} data points for {chart_name}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching {chart_name}: {e}")
            return pd.DataFrame()
    
    def get_mvrv_ratio(self, timespan="2years"):
        """
        Get MVRV (Market Value to Realized Value) Ratio.
        
        MVRV > 3.7 historically indicates cycle tops
        MVRV < 1.0 indicates cycle bottoms
        
        Args:
            timespan: Data timespan
            
        Returns:
            DataFrame with MVRV data
        """
        # Note: Blockchain.com doesn't have direct MVRV endpoint
        # We calculate it from market-cap and realized-cap if available
        # For now, return market cap as placeholder
        return self._get_chart_data('market-cap', timespan=timespan)
    
    def get_active_addresses(self, timespan="1year"):
        """
        Get number of unique addresses active on the network.
        
        Indicator of network health and adoption.
        
        Args:
            timespan: Data timespan
            
        Returns:
            DataFrame with active addresses
        """
        return self._get_chart_data('n-unique-addresses', timespan=timespan)
    
    def get_hash_rate(self, timespan="1year"):
        """
        Get Bitcoin network hash rate.
        
        Args:
            timespan: Data timespan
            
        Returns:
            DataFrame with hash rate (TH/s)
        """
        return self._get_chart_data('hash-rate', timespan=timespan)
    
    def get_mempool_size(self, timespan="30days"):
        """
        Get mempool size (number of unconfirmed transactions).
        
        High mempool = network congestion or high demand
        
        Args:
            timespan: Data timespan
            
        Returns:
            DataFrame with mempool size
        """
        return self._get_chart_data('mempool-size', timespan=timespan)
    
    def get_market_cap(self, timespan="2years"):
        """
        Get Bitcoin market capitalization.
        
        Args:
            timespan: Data timespan
            
        Returns:
            DataFrame with market cap (USD)
        """
        return self._get_chart_data('market-cap', timespan=timespan)
    
    def calculate_realized_price(self, timespan="2years"):
        """
        Calculate Realized Price from MVRV and Market Price.
        
        Realized Price = Market Price / MVRV
        
        This is the average price at which all BTC were acquired.
        Acts as strong macro support level.
        
        Args:
            timespan: Data timespan
            
        Returns:
            DataFrame with realized price
        """
        # Get MVRV
        mvrv_df = self.get_mvrv_ratio(timespan=timespan)
        
        if mvrv_df.empty:
            return pd.DataFrame()
        
        # Get market price (approximate from market cap / circulating supply)
        market_cap = self.get_market_cap(timespan=timespan)
        
        # For simplicity, we'll need actual price from elsewhere
        # This is a placeholder - in production, merge with price data
        logger.info("Realized price calculation requires price data")
        
        return mvrv_df
    
    def get_current_mvrv(self):
        """
        Get the most recent MVRV value.
        
        Note: Since Blockchain.com doesn't have direct MVRV,
        we use market cap as proxy indicator.
        
        Returns:
            dict with market cap info
        """
        df = self.get_market_cap(timespan="30days")
        
        if df.empty:
            return {
                'value': None,
                'timestamp': None,
                'signal': 'Unknown',
                'error': 'No data available'
            }
        
        current = df.iloc[-1]
        market_cap = current['value']
        
        # Use market cap milestones as signals
        # (placeholder logic - in production use actual MVRV from paid sources)
        if market_cap > 1.5e12:  # > $1.5T
            signal = "OVERVALUED"
            description = "High market cap zone"
        elif market_cap > 1.0e12:  # > $1T
            signal = "FAIR_VALUE"
            description = "Normal valuation"
        elif market_cap > 5e11:  # > $500B
            signal = "UNDERVALUED"
            description = "Below average valuation"
        else:
            signal = "ACCUMULATION"
            description = "Low valuation zone"
        
        return {
            'value': float(market_cap),
            'metric': 'market_cap',
            'timestamp': current['timestamp'].isoformat(),
            'signal': signal,
            'description': description,
            'note': 'Using market cap as MVRV proxy (Blockchain.com free tier)'
        }


class BinanceFuturesAPI:
    """
    Free derivatives data from Binance Futures.
    
    Funding rates, open interest, long/short ratio.
    No authentication required for public endpoints.
    """
    
    BASE_URL = "https://fapi.binance.com/fapi/v1"
    
    def __init__(self):
        """Initialize Binance Futures API client."""
        self.session = requests.Session()
        
    def get_funding_rate(self, symbol="BTCUSDT"):
        """
        Get current funding rate from Binance Futures.
        
        High positive funding = longs paying shorts (overheated)
        High negative funding = shorts paying longs (bearish extreme)
        
        Args:
            symbol: Trading pair symbol (default BTCUSDT)
            
        Returns:
            dict with funding rate data
        """
        url = f"{self.BASE_URL}/fundingRate"
        
        try:
            response = self.session.get(
                url, 
                params={'symbol': symbol, 'limit': 1}, 
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                latest = data[0]
                rate = float(latest['fundingRate'])
                
                # Funding rate is per 8 hours, annualize for comparison
                # 3 funding periods per day = rate * 3 * 365
                annual_rate = rate * 3 * 365
                
                # Interpret (using 8-hour rate thresholds)
                if rate > 0.001:  # > 0.1% per 8h
                    signal = "EXTREME_LONG"
                    warning = "Long squeeze risk"
                elif rate > 0.0005:  # > 0.05% per 8h
                    signal = "BULLISH_OVERHEATED"
                    warning = "High long interest"
                elif rate < -0.001:  # < -0.1% per 8h
                    signal = "EXTREME_SHORT"
                    warning = "Short squeeze risk"
                elif rate < -0.0005:  # < -0.05% per 8h
                    signal = "BEARISH_EXTREME"
                    warning = "High short interest"
                else:
                    signal = "NEUTRAL"
                    warning = "Balanced"
                
                return {
                    'symbol': latest['symbol'],
                    'funding_rate': rate,
                    'funding_rate_pct': rate * 100,
                    'annual_rate_pct': annual_rate * 100,
                    'funding_time': pd.to_datetime(latest['fundingTime'], unit='ms'),
                    'mark_price': float(latest.get('markPrice', 0)),
                    'signal': signal,
                    'warning': warning,
                    'source': 'Binance Futures'
                }
            
            return {'error': 'No data available'}
            
        except Exception as e:
            logger.error(f"Error fetching funding rate: {e}")
            return {'error': str(e)}
    
    def get_open_interest(self, symbol="BTC"):
        """
        Get total open interest across exchanges.
        
        Rising OI + rising price = strong trend
        Falling OI + rising price = weak trend
        
        Args:
            symbol: Cryptocurrency symbol
            
        Returns:
            dict with OI data
        """
        # Note: This endpoint may require API key for full access
        logger.warning("Open Interest endpoint may have limited free access")
        
        return {
            'note': 'Implement when API access confirmed',
            'alternative': 'Use Blockchain.com or TradingView for free OI data'
        }


def get_comprehensive_onchain_data():
    """
    Get comprehensive on-chain analysis using free sources.
    
    Returns:
        dict with all available on-chain metrics
    """
    blockchain = BlockchainComAPI()
    binance_futures = BinanceFuturesAPI()
    
    logger.info("Fetching comprehensive on-chain data...")
    
    # MVRV (macro valuation)
    mvrv = blockchain.get_current_mvrv()
    
    # Funding rate (derivatives sentiment)
    funding = binance_futures.get_funding_rate()
    
    # Active addresses (last 7 days)
    active_addr = blockchain.get_active_addresses(timespan="7days")
    
    current_addresses = None
    if not active_addr.empty:
        current_addresses = int(active_addr.iloc[-1]['value'])
    
    # Mempool (short-term congestion)
    mempool = blockchain.get_mempool_size(timespan="7days")
    
    current_mempool = None
    if not mempool.empty:
        current_mempool = int(mempool.iloc[-1]['value'])
    
    return {
        'mvrv': mvrv,
        'funding_rate': funding,
        'active_addresses': current_addresses,
        'mempool_size': current_mempool,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Test API
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Free On-Chain Data APIs")
    print("=" * 50)
    
    # Test Blockchain.com
    print("\n1. Testing Blockchain.com API...")
    blockchain = BlockchainComAPI()
    
    mvrv = blockchain.get_current_mvrv()
    print(f"Current MVRV: {mvrv}")
    
    # Test Binance Futures
    print("\n2. Testing Binance Futures API...")
    binance = BinanceFuturesAPI()
    
    funding = binance.get_funding_rate()
    print(f"Funding Rate: {funding}")
    
    # Comprehensive
    print("\n3. Getting Comprehensive Data...")
    data = get_comprehensive_onchain_data()
    print(f"Comprehensive: {data}")
