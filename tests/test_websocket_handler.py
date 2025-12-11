#!/usr/bin/env python3
"""
Test WebSocket Data Handler

Validates real-time data processing, risk calculation, and alerting.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.services.websocket_handler import WebSocketDataHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)

logger = logging.getLogger(__name__)


async def test_handler(duration: int = 120):
    """
    Test WebSocket handler for specified duration.
    
    Args:
        duration: Test duration in seconds (default: 120 = 2 minutes)
    """
    logger.info("🧪 Testing WebSocket Data Handler")
    logger.info(f"Duration: {duration}s ({duration//60}m {duration%60}s)")
    logger.info("="*70)
    
    handler = WebSocketDataHandler(
        symbol="BTCUSDT",
        interval="1m",
        buffer_size=500
    )
    
    try:
        # Run with timeout
        await asyncio.wait_for(handler.start(), timeout=duration)
        
    except asyncio.TimeoutError:
        logger.info(f"\n⏰ Test completed ({duration}s)")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
        
    finally:
        await handler.stop()
        
        # Print detailed statistics
        stats = handler.get_statistics()
        
        print("\n" + "="*70)
        print("📊 TEST RESULTS")
        print("="*70)
        print(f"Symbol:              {stats['symbol']}")
        print(f"Interval:            {stats['interval']}")
        print(f"Runtime:             {stats['runtime_seconds']:.1f}s")
        print(f"Candles processed:   {stats['candles_processed']}")
        print(f"Trades processed:    {stats['trades_processed']}")
        print(f"Buffer size:         {stats['buffer_size']}")
        print(f"Current price:       ${stats['current_price']:,.2f}" if stats['current_price'] else "N/A")
        print(f"Last update:         {stats['last_update']}")
        print("-"*70)
        
        # Get risk metrics
        if stats['has_risk_metrics']:
            metrics = handler.get_risk_metrics()
            print("\n⚠️ RISK METRICS:")
            print(f"   VaR 95% (std):    {metrics.var_95*100:>7.3f}%")
            print(f"   VaR 95% (mod):    {metrics.var_95_modified*100:>7.3f}%")
            print(f"   VaR 99% (std):    {metrics.var_99*100:>7.3f}%")
            print(f"   VaR 99% (mod):    {metrics.var_99_modified*100:>7.3f}%")
            print(f"   Expected SF:      {metrics.expected_shortfall_95*100:>7.3f}%")
            print(f"   Max Drawdown:     {metrics.max_drawdown*100:>7.2f}%")
            print(f"   Sharpe Ratio:     {metrics.sharpe_ratio:>7.2f}")
            print(f"   Skewness:         {metrics.skewness:>7.3f}")
            print(f"   Kurtosis:         {metrics.kurtosis:>7.3f}")
        
        # Get latest candles
        recent = handler.get_latest_candles(5)
        if recent:
            print("\n🕯️ LAST 5 CANDLES:")
            for candle in recent:
                print(f"   {candle.close_time.strftime('%H:%M:%S')} | "
                      f"C: ${candle.close:>9,.2f} | "
                      f"H: ${candle.high:>9,.2f} | "
                      f"L: ${candle.low:>9,.2f} | "
                      f"V: {candle.volume:>8,.2f}")
        
        print("="*70)
        
        # Validation
        print("\n🎯 VALIDATION:")
        checks = [
            ("WebSocket connected", stats['runtime_seconds'] > 0),
            ("Candles received", stats['candles_processed'] > 0),
            ("Trades received", stats['trades_processed'] > 0),
            ("Buffer populated", stats['buffer_size'] > 0),
            ("Risk metrics calculated", stats['has_risk_metrics']),
        ]
        
        for name, result in checks:
            status = "✅" if result else "❌"
            print(f"   {status} {name}")
        
        if all(r for _, r in checks):
            print("\n🎉 ALL TESTS PASSED!")
            print("\n💡 Next steps:")
            print("   1. Integrate with database storage")
            print("   2. Add alert service integration")
            print("   3. Create REST API endpoints for real-time data")
            return 0
        else:
            print("\n⚠️ SOME TESTS FAILED")
            return 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=120, help="Test duration in seconds")
    args = parser.parse_args()
    
    try:
        exit_code = asyncio.run(test_handler(args.duration))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted")
        sys.exit(1)
