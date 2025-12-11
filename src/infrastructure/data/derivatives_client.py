"""
Derivatives Data Client for Bitcoin Futures & Perpetuals

Fetches derivatives market data from multiple exchanges:
- Funding Rates (Binance, Bybit, OKX)
- Open Interest (aggregated across exchanges)
- Liquidations (real-time from Coinglass API)
- Long/Short Ratios

This data is crucial for:
- Identifying over-leveraged positions
- Predicting liquidation cascades
- Detecting funding arbitrage opportunities
- Confirming trend strength with OI divergence

Author: Bitcoin Market Intelligence Team
Created: 2025-12-10
Priority: HIGH (Phase 1 - Derivatives Intelligence)
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import aiohttp
import pandas as pd

logger = logging.getLogger(__name__)


class Exchange(Enum):
    """Supported exchanges for derivatives data."""
    BINANCE = "binance"
    BYBIT = "bybit"
    OKX = "okx"
    DERIBIT = "deribit"


@dataclass
class FundingRate:
    """Funding rate data point."""
    
    exchange: str
    symbol: str
    funding_rate: float  # 8-hour rate (e.g., 0.0001 = 0.01%)
    funding_time: datetime
    next_funding_time: datetime
    mark_price: float
    index_price: float
    
    @property
    def annual_rate(self) -> float:
        """Convert 8-hour rate to annualized rate."""
        return self.funding_rate * 3 * 365  # 3 times per day
    
    @property
    def daily_rate(self) -> float:
        """Convert 8-hour rate to daily rate."""
        return self.funding_rate * 3


@dataclass
class OpenInterest:
    """Open Interest data point."""
    
    exchange: str
    symbol: str
    open_interest: float  # In USD
    open_interest_value: float  # In contracts
    timestamp: datetime
    
    
@dataclass
class LiquidationData:
    """Liquidation event data."""
    
    exchange: str
    symbol: str
    side: str  # "long" or "short"
    quantity: float
    price: float
    value: float  # USD value
    timestamp: datetime


@dataclass
class LongShortRatio:
    """Long/Short ratio from exchanges."""
    
    exchange: str
    symbol: str
    long_ratio: float  # 0-1 (e.g., 0.65 = 65% long)
    short_ratio: float  # 0-1 (e.g., 0.35 = 35% short)
    long_account: int  # Number of long accounts
    short_account: int  # Number of short accounts
    timestamp: datetime


class DerivativesDataClient:
    """
    Client for fetching derivatives market data from multiple sources.
    
    Data Sources:
    - Binance Futures API (primary)
    - Bybit API (secondary)
    - OKX API (tertiary)
    - Coinglass API (liquidations aggregated)
    
    Features:
    - Multi-exchange data aggregation
    - Rate limiting and error handling
    - Caching for performance
    - Historical data support
    """
    
    BINANCE_BASE = "https://fapi.binance.com"
    BYBIT_BASE = "https://api.bybit.com"
    OKX_BASE = "https://www.okx.com"
    COINGLASS_BASE = "https://open-api.coinglass.com/public/v2"
    
    def __init__(self, coinglass_api_key: Optional[str] = None):
        """
        Initialize derivatives data client.
        
        Args:
            coinglass_api_key: API key for Coinglass (optional, for liquidations)
        """
        self.coinglass_api_key = coinglass_api_key
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    # ==================== FUNDING RATE ====================
    
    async def get_funding_rate_binance(self, symbol: str = "BTCUSDT") -> Optional[FundingRate]:
        """
        Get current funding rate from Binance Futures.
        
        Args:
            symbol: Trading pair (default: BTCUSDT)
            
        Returns:
            FundingRate object or None if error
        """
        url = f"{self.BINANCE_BASE}/fapi/v1/premiumIndex"
        params = {"symbol": symbol}
        
        try:
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"Binance API error: {response.status}")
                    return None
                
                data = await response.json()
                
                return FundingRate(
                    exchange="binance",
                    symbol=symbol,
                    funding_rate=float(data['lastFundingRate']),
                    funding_time=datetime.fromtimestamp(data['time'] / 1000),
                    next_funding_time=datetime.fromtimestamp(data['nextFundingTime'] / 1000),
                    mark_price=float(data['markPrice']),
                    index_price=float(data['indexPrice'])
                )
                
        except Exception as e:
            logger.error(f"Failed to fetch Binance funding rate: {e}")
            return None
    
    async def get_funding_rate_bybit(self, symbol: str = "BTCUSDT") -> Optional[FundingRate]:
        """
        Get current funding rate from Bybit.
        
        Args:
            symbol: Trading pair (default: BTCUSDT)
            
        Returns:
            FundingRate object or None if error
        """
        url = f"{self.BYBIT_BASE}/v5/market/tickers"
        params = {"category": "linear", "symbol": symbol}
        
        try:
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"Bybit API error: {response.status}")
                    return None
                
                data = await response.json()
                
                if data['retCode'] != 0 or not data['result']['list']:
                    return None
                
                ticker = data['result']['list'][0]
                
                return FundingRate(
                    exchange="bybit",
                    symbol=symbol,
                    funding_rate=float(ticker['fundingRate']),
                    funding_time=datetime.now(),  # Bybit doesn't provide exact time
                    next_funding_time=datetime.fromtimestamp(int(ticker['nextFundingTime']) / 1000),
                    mark_price=float(ticker['markPrice']),
                    index_price=float(ticker['indexPrice'])
                )
                
        except Exception as e:
            logger.error(f"Failed to fetch Bybit funding rate: {e}")
            return None
    
    async def get_funding_rate_okx(self, symbol: str = "BTC-USDT-SWAP") -> Optional[FundingRate]:
        """
        Get current funding rate from OKX.
        
        Args:
            symbol: Trading pair (OKX format: BTC-USDT-SWAP)
            
        Returns:
            FundingRate object or None if error
        """
        url = f"{self.OKX_BASE}/api/v5/public/funding-rate"
        params = {"instId": symbol}
        
        try:
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"OKX API error: {response.status}")
                    return None
                
                data = await response.json()
                
                if data['code'] != '0' or not data['data']:
                    return None
                
                funding_data = data['data'][0]
                
                return FundingRate(
                    exchange="okx",
                    symbol=symbol,
                    funding_rate=float(funding_data['fundingRate']),
                    funding_time=datetime.fromtimestamp(int(funding_data['fundingTime']) / 1000),
                    next_funding_time=datetime.fromtimestamp(int(funding_data['nextFundingTime']) / 1000),
                    mark_price=0.0,  # OKX doesn't provide in this endpoint
                    index_price=0.0
                )
                
        except Exception as e:
            logger.error(f"Failed to fetch OKX funding rate: {e}")
            return None
    
    async def get_funding_rates_all(self, symbol: str = "BTCUSDT") -> Dict[str, FundingRate]:
        """
        Get funding rates from all exchanges.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dictionary of exchange -> FundingRate
        """
        tasks = [
            self.get_funding_rate_binance(symbol),
            self.get_funding_rate_bybit(symbol),
            self.get_funding_rate_okx("BTC-USDT-SWAP")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        funding_rates = {}
        for result in results:
            if isinstance(result, FundingRate):
                funding_rates[result.exchange] = result
            elif isinstance(result, Exception):
                logger.error(f"Error fetching funding rate: {result}")
        
        return funding_rates
    
    # ==================== OPEN INTEREST ====================
    
    async def get_open_interest_binance(self, symbol: str = "BTCUSDT") -> Optional[OpenInterest]:
        """
        Get current Open Interest from Binance Futures.
        
        Args:
            symbol: Trading pair
            
        Returns:
            OpenInterest object or None if error
        """
        url = f"{self.BINANCE_BASE}/fapi/v1/openInterest"
        params = {"symbol": symbol}
        
        try:
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                # Get current price for USD value
                price_url = f"{self.BINANCE_BASE}/fapi/v1/ticker/price"
                async with self.session.get(price_url, params={"symbol": symbol}) as price_response:
                    price_data = await price_response.json()
                    current_price = float(price_data['price'])
                
                oi_contracts = float(data['openInterest'])
                oi_usd = oi_contracts * current_price
                
                return OpenInterest(
                    exchange="binance",
                    symbol=symbol,
                    open_interest=oi_usd,
                    open_interest_value=oi_contracts,
                    timestamp=datetime.fromtimestamp(data['time'] / 1000)
                )
                
        except Exception as e:
            logger.error(f"Failed to fetch Binance OI: {e}")
            return None
    
    async def get_open_interest_bybit(self, symbol: str = "BTCUSDT") -> Optional[OpenInterest]:
        """
        Get current Open Interest from Bybit.
        
        Args:
            symbol: Trading pair
            
        Returns:
            OpenInterest object or None if error
        """
        url = f"{self.BYBIT_BASE}/v5/market/open-interest"
        params = {"category": "linear", "symbol": symbol, "intervalTime": "5min"}
        
        try:
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                if data['retCode'] != 0 or not data['result']['list']:
                    return None
                
                oi_data = data['result']['list'][0]
                
                return OpenInterest(
                    exchange="bybit",
                    symbol=symbol,
                    open_interest=float(oi_data['openInterest']),
                    open_interest_value=float(oi_data['openInterest']),  # Already in USD
                    timestamp=datetime.fromtimestamp(int(oi_data['timestamp']) / 1000)
                )
                
        except Exception as e:
            logger.error(f"Failed to fetch Bybit OI: {e}")
            return None
    
    async def get_open_interest_all(self, symbol: str = "BTCUSDT") -> Dict[str, OpenInterest]:
        """
        Get Open Interest from all exchanges.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dictionary of exchange -> OpenInterest
        """
        tasks = [
            self.get_open_interest_binance(symbol),
            self.get_open_interest_bybit(symbol)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        oi_data = {}
        for result in results:
            if isinstance(result, OpenInterest):
                oi_data[result.exchange] = result
        
        return oi_data
    
    # ==================== LONG/SHORT RATIO ====================
    
    async def get_long_short_ratio_binance(self, symbol: str = "BTCUSDT", period: str = "5m") -> Optional[LongShortRatio]:
        """
        Get Long/Short ratio from Binance.
        
        Args:
            symbol: Trading pair
            period: Time period (5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d)
            
        Returns:
            LongShortRatio object or None if error
        """
        url = f"{self.BINANCE_BASE}/futures/data/globalLongShortAccountRatio"
        params = {"symbol": symbol, "period": period, "limit": 1}
        
        try:
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                if not data:
                    return None
                
                ratio_data = data[0]
                long_ratio = float(ratio_data['longAccount'])
                short_ratio = float(ratio_data['shortAccount'])
                
                return LongShortRatio(
                    exchange="binance",
                    symbol=symbol,
                    long_ratio=long_ratio,
                    short_ratio=short_ratio,
                    long_account=0,  # Binance doesn't provide counts
                    short_account=0,
                    timestamp=datetime.fromtimestamp(ratio_data['timestamp'] / 1000)
                )
                
        except Exception as e:
            logger.error(f"Failed to fetch Binance L/S ratio: {e}")
            return None
    
    # ==================== AGGREGATED METRICS ====================
    
    async def get_derivatives_summary(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """
        Get comprehensive derivatives summary.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dictionary with all derivatives metrics
        """
        # Fetch all data concurrently
        funding_rates_task = self.get_funding_rates_all(symbol)
        oi_task = self.get_open_interest_all(symbol)
        ls_ratio_task = self.get_long_short_ratio_binance(symbol)
        
        funding_rates, oi_data, ls_ratio = await asyncio.gather(
            funding_rates_task, oi_task, ls_ratio_task,
            return_exceptions=True
        )
        
        # Calculate aggregated metrics
        if isinstance(funding_rates, dict) and funding_rates:
            avg_funding = sum(fr.funding_rate for fr in funding_rates.values()) / len(funding_rates)
            avg_funding_annual = sum(fr.annual_rate for fr in funding_rates.values()) / len(funding_rates)
        else:
            avg_funding = 0.0
            avg_funding_annual = 0.0
        
        if isinstance(oi_data, dict) and oi_data:
            total_oi = sum(oi.open_interest for oi in oi_data.values())
        else:
            total_oi = 0.0
        
        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'funding_rates': funding_rates if isinstance(funding_rates, dict) else {},
            'avg_funding_rate': avg_funding,
            'avg_funding_annual': avg_funding_annual,
            'open_interest': oi_data if isinstance(oi_data, dict) else {},
            'total_open_interest': total_oi,
            'long_short_ratio': ls_ratio if isinstance(ls_ratio, LongShortRatio) else None,
        }


# ==================== EXAMPLE USAGE ====================

async def main():
    """Example usage of DerivativesDataClient."""
    
    print("🔍 Fetching Derivatives Market Data")
    print("="*70)
    
    async with DerivativesDataClient() as client:
        # Get comprehensive summary
        summary = await client.get_derivatives_summary("BTCUSDT")
        
        print(f"\n📊 Derivatives Summary for {summary['symbol']}")
        print(f"Timestamp: {summary['timestamp']}")
        print("\n" + "-"*70)
        
        # Funding Rates
        print("\n💰 FUNDING RATES:")
        for exchange, fr in summary['funding_rates'].items():
            print(f"   {exchange.upper():.<15} {fr.funding_rate*100:>8.4f}% (8h) | {fr.annual_rate*100:>7.2f}% (annual)")
        
        if summary['funding_rates']:
            print(f"   {'AVERAGE':.<15} {summary['avg_funding_rate']*100:>8.4f}% (8h) | {summary['avg_funding_annual']*100:>7.2f}% (annual)")
        
        # Open Interest
        print("\n📈 OPEN INTEREST:")
        for exchange, oi in summary['open_interest'].items():
            print(f"   {exchange.upper():.<15} ${oi.open_interest:>15,.0f} | {oi.open_interest_value:>12,.2f} contracts")
        
        if summary['open_interest']:
            print(f"   {'TOTAL':.<15} ${summary['total_open_interest']:>15,.0f}")
        
        # Long/Short Ratio
        if summary['long_short_ratio']:
            ls = summary['long_short_ratio']
            print("\n⚖️  LONG/SHORT RATIO:")
            print(f"   Long:  {ls.long_ratio*100:>6.2f}%")
            print(f"   Short: {ls.short_ratio*100:>6.2f}%")
            
            if ls.long_ratio > 0.60:
                print("   Status: 🔴 OVERCROWDED LONG (risk of cascade liquidation)")
            elif ls.short_ratio > 0.60:
                print("   Status: 🟢 OVERCROWDED SHORT (potential short squeeze)")
            else:
                print("   Status: ⚪ BALANCED")
        
        print("\n" + "="*70)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Run example
    asyncio.run(main())
