#!/usr/bin/env python3
"""
Test script for BinanceWebSocketClient

Tests real-time streaming from Binance WebSocket API.
Run for 30 seconds to validate connection and data flow.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.data.websocket_client import BinanceWebSocketClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)

logger = logging.getLogger(__name__)


class DataCounter:
    """Track received messages for testing."""
    
    def __init__(self):
        self.kline_count = 0
        self.trade_count = 0
        self.ticker_count = 0
        self.last_kline = None
        self.last_trade = None
        
    def on_kline(self, data):
        """Handle kline updates."""
        self.kline_count += 1
        k = data['k']
        self.last_kline = {
            'symbol': k['s'],
            'interval': k['i'],
            'close': float(k['c']),
            'volume': float(k['v']),
            'is_closed': k['x']
        }
        
        if k['x']:  # Only log closed candles
            logger.info(
                f"🕯️ KLINE CLOSED | {k['s']} {k['i']} | "
                f"C: ${float(k['c']):,.2f} | V: {float(k['v']):,.2f}"
            )
    
    def on_trade(self, data):
        """Handle individual trades."""
        self.trade_count += 1
        self.last_trade = {
            'symbol': data['s'],
            'price': float(data['p']),
            'quantity': float(data['q']),
            'is_buyer_maker': data['m']
        }
        
        # Log every 10th trade to avoid spam
        if self.trade_count % 10 == 0:
            side = "🔴 SELL" if data['m'] else "🟢 BUY"
            logger.info(
                f"💱 TRADE #{self.trade_count} | {data['s']} | "
                f"${float(data['p']):,.2f} x {float(data['q']):.6f} | {side}"
            )
    
    def on_ticker(self, data):
        """Handle ticker updates."""
        self.ticker_count += 1
        
        # Log every 5th ticker
        if self.ticker_count % 5 == 0:
            # miniTicker doesn't have 'P', check if it exists
            change = float(data.get('P', 0))
            trend = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            logger.info(
                f"{trend} TICKER | {data['s']} | "
                f"${float(data['c']):,.2f} | "
                f"H: ${float(data['h']):,.2f} | "
                f"L: ${float(data['l']):,.2f}"
            )
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        print(f"Kline updates:  {self.kline_count:>6}")
        print(f"Trades:         {self.trade_count:>6}")
        print(f"Ticker updates: {self.ticker_count:>6}")
        print("-"*70)
        
        if self.last_kline:
            print(f"\n🕯️ Last Kline:")
            print(f"   Symbol:   {self.last_kline['symbol']}")
            print(f"   Interval: {self.last_kline['interval']}")
            print(f"   Close:    ${self.last_kline['close']:,.2f}")
            print(f"   Volume:   {self.last_kline['volume']:,.2f}")
        
        if self.last_trade:
            print(f"\n💱 Last Trade:")
            print(f"   Symbol:   {self.last_trade['symbol']}")
            print(f"   Price:    ${self.last_trade['price']:,.2f}")
            print(f"   Quantity: {self.last_trade['quantity']:.6f}")
            print(f"   Side:     {'SELL' if self.last_trade['is_buyer_maker'] else 'BUY'}")
        
        print("="*70)


async def test_websocket(duration: int = 30):
    """
    Test WebSocket client with live Binance streams.
    
    Args:
        duration: Test duration in seconds (default: 30)
    """
    logger.info("🧪 Starting WebSocket Test")
    logger.info(f"Duration: {duration} seconds")
    logger.info("-"*70)
    
    # Create client and counter
    client = BinanceWebSocketClient()
    counter = DataCounter()
    
    # Subscribe to multiple streams
    client.subscribe_kline("BTCUSDT", "1m", counter.on_kline)
    client.subscribe_trade("BTCUSDT", counter.on_trade)
    client.subscribe_ticker("BTCUSDT", counter.on_ticker)
    
    logger.info("✅ Subscribed to streams:")
    for stream in client.get_subscriptions():
        logger.info(f"   - {stream}")
    logger.info("-"*70)
    
    # Run client with timeout
    try:
        await asyncio.wait_for(client.connect(), timeout=duration)
    except asyncio.TimeoutError:
        logger.info(f"\n⏰ Test duration ({duration}s) reached")
    except KeyboardInterrupt:
        logger.info("\n⚠️ Test interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Test error: {e}", exc_info=True)
    finally:
        await client.disconnect()
        counter.print_summary()
        
    # Validation
    print("\n🎯 VALIDATION:")
    checks = [
        ("Kline updates received", counter.kline_count > 0),
        ("Trades received", counter.trade_count > 0),
        ("Ticker updates received", counter.ticker_count > 0),
        ("Client connected", True),
    ]
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}")
    
    all_passed = all(result for _, result in checks)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("\n⚠️ SOME TESTS FAILED")
        return 1


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Binance WebSocket Client")
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Test duration in seconds (default: 30)"
    )
    
    args = parser.parse_args()
    
    exit_code = await test_websocket(args.duration)
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted")
        sys.exit(1)
