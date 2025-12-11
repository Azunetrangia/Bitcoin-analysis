"""
Trading Signal Analyzer

Combines multiple data sources to generate actionable trading signals:
- Spot price action (WebSocket)
- Risk metrics (VaR, Sharpe, Sortino)
- Derivatives market (Funding, OI, Long/Short)
- Technical indicators (RSI, MACD, Bollinger Bands)

Signal Types:
1. Funding Rate Arbitrage
2. Liquidation Cascade Warning
3. OI Divergence (Price ↑ OI ↓ = Bearish)
4. Overcrowded Positions
5. Risk-Adjusted Entry/Exit

Author: Bitcoin Market Intelligence Team
Created: 2025-12-10
Priority: HIGH (Phase 1 - Signal Generation)
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from src.infrastructure.data.derivatives_client import DerivativesDataClient
from src.domain.services.websocket_handler import WebSocketDataHandler
from src.domain.services.risk_calculator import RiskCalculatorService

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of trading signals."""
    FUNDING_ARBITRAGE = "funding_arbitrage"
    LIQUIDATION_WARNING = "liquidation_warning"
    OI_DIVERGENCE = "oi_divergence"
    OVERCROWDED_LONG = "overcrowded_long"
    OVERCROWDED_SHORT = "overcrowded_short"
    HIGH_RISK = "high_risk"
    ENTRY_OPPORTUNITY = "entry_opportunity"
    EXIT_SIGNAL = "exit_signal"


class SignalStrength(Enum):
    """Signal strength levels."""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4


@dataclass
class TradingSignal:
    """Trading signal with metadata."""
    
    signal_type: SignalType
    strength: SignalStrength
    direction: str  # "long", "short", "neutral"
    price: float
    timestamp: datetime
    reason: str
    data: Dict[str, Any]
    
    def __str__(self) -> str:
        """String representation of signal."""
        emoji = {
            "long": "🟢",
            "short": "🔴",
            "neutral": "⚪"
        }
        
        return (
            f"{emoji[self.direction]} {self.signal_type.value.upper()} "
            f"[{self.strength.name}] @ ${self.price:,.2f}\n"
            f"   Reason: {self.reason}"
        )


class TradingSignalAnalyzer:
    """
    Analyzes multiple data sources to generate trading signals.
    
    Features:
    - Real-time signal generation
    - Multi-factor analysis
    - Risk-adjusted recommendations
    - Alert triggering
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1m",
        risk_threshold: float = 0.03  # 3% VaR threshold
    ):
        """
        Initialize signal analyzer.
        
        Args:
            symbol: Trading pair
            interval: Candle interval
            risk_threshold: VaR threshold for high risk alerts
        """
        self.symbol = symbol
        self.interval = interval
        self.risk_threshold = risk_threshold
        
        # Services
        self.derivatives_client: Optional[DerivativesDataClient] = None
        self.ws_handler: Optional[WebSocketDataHandler] = None
        
        # Signal history
        self.signals: List[TradingSignal] = []
        
    async def start(self) -> None:
        """Start signal analyzer."""
        logger.info(f"🚀 Starting Trading Signal Analyzer for {self.symbol}")
        
        # Initialize services
        self.derivatives_client = DerivativesDataClient()
        await self.derivatives_client.__aenter__()
        
        self.ws_handler = WebSocketDataHandler(
            symbol=self.symbol,
            interval=self.interval,
            buffer_size=500
        )
        
        # Start analysis loop
        await asyncio.gather(
            self.ws_handler.start(),
            self._analysis_loop()
        )
    
    async def stop(self) -> None:
        """Stop signal analyzer."""
        if self.ws_handler:
            await self.ws_handler.stop()
        
        if self.derivatives_client:
            await self.derivatives_client.__aexit__(None, None, None)
        
        logger.info("🛑 Signal analyzer stopped")
    
    async def _analysis_loop(self) -> None:
        """Main analysis loop."""
        while True:
            try:
                # Wait for some data to accumulate
                await asyncio.sleep(60)
                
                # Run analysis
                signals = await self.analyze()
                
                # Process new signals
                for signal in signals:
                    self.signals.append(signal)
                    logger.info(f"📊 {signal}")
                
            except Exception as e:
                logger.error(f"Analysis loop error: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def analyze(self) -> List[TradingSignal]:
        """
        Run comprehensive analysis and generate signals.
        
        Returns:
            List of trading signals
        """
        signals = []
        
        # Get current data
        current_price = self.ws_handler.get_current_price()
        if not current_price:
            return signals
        
        # Fetch derivatives data
        deriv_summary = await self.derivatives_client.get_derivatives_summary(self.symbol)
        
        # 1. Check funding rate arbitrage
        funding_signal = self._check_funding_arbitrage(deriv_summary, current_price)
        if funding_signal:
            signals.append(funding_signal)
        
        # 2. Check overcrowded positions
        crowd_signal = self._check_overcrowded_positions(deriv_summary, current_price)
        if crowd_signal:
            signals.append(crowd_signal)
        
        # 3. Check risk metrics
        risk_signal = self._check_risk_levels(current_price)
        if risk_signal:
            signals.append(risk_signal)
        
        # 4. Check OI divergence (requires historical OI - TODO)
        
        return signals
    
    def _check_funding_arbitrage(
        self,
        deriv_summary: Dict[str, Any],
        price: float
    ) -> Optional[TradingSignal]:
        """
        Check for funding rate arbitrage opportunities.
        
        Positive funding (longs pay shorts) > 0.05% = consider shorting
        Negative funding (shorts pay longs) < -0.05% = consider longing
        
        Args:
            deriv_summary: Derivatives market summary
            price: Current price
            
        Returns:
            TradingSignal or None
        """
        avg_funding = deriv_summary.get('avg_funding_rate', 0)
        avg_annual = deriv_summary.get('avg_funding_annual', 0)
        
        # Threshold: 0.05% (8h) = 18.25% annual
        if avg_funding > 0.0005:  # 0.05%
            strength = SignalStrength.STRONG if avg_funding > 0.001 else SignalStrength.MODERATE
            
            return TradingSignal(
                signal_type=SignalType.FUNDING_ARBITRAGE,
                strength=strength,
                direction="short",
                price=price,
                timestamp=datetime.now(),
                reason=f"High funding rate {avg_funding*100:.4f}% (8h) = {avg_annual*100:.2f}% annual. Longs overpaying.",
                data={'funding_rate': avg_funding, 'annual_rate': avg_annual}
            )
        
        elif avg_funding < -0.0005:  # Negative funding
            strength = SignalStrength.STRONG if avg_funding < -0.001 else SignalStrength.MODERATE
            
            return TradingSignal(
                signal_type=SignalType.FUNDING_ARBITRAGE,
                strength=strength,
                direction="long",
                price=price,
                timestamp=datetime.now(),
                reason=f"Negative funding {avg_funding*100:.4f}% (8h). Shorts overpaying.",
                data={'funding_rate': avg_funding, 'annual_rate': avg_annual}
            )
        
        return None
    
    def _check_overcrowded_positions(
        self,
        deriv_summary: Dict[str, Any],
        price: float
    ) -> Optional[TradingSignal]:
        """
        Check for overcrowded long/short positions.
        
        Long ratio > 65% = potential cascade liquidation on downmove
        Short ratio > 65% = potential short squeeze on upmove
        
        Args:
            deriv_summary: Derivatives market summary
            price: Current price
            
        Returns:
            TradingSignal or None
        """
        ls_ratio = deriv_summary.get('long_short_ratio')
        
        if not ls_ratio:
            return None
        
        # Overcrowded longs (bearish)
        if ls_ratio.long_ratio > 0.65:
            strength = SignalStrength.VERY_STRONG if ls_ratio.long_ratio > 0.70 else SignalStrength.STRONG
            
            return TradingSignal(
                signal_type=SignalType.OVERCROWDED_LONG,
                strength=strength,
                direction="short",
                price=price,
                timestamp=datetime.now(),
                reason=f"Overcrowded longs {ls_ratio.long_ratio*100:.1f}%. Risk of liquidation cascade.",
                data={'long_ratio': ls_ratio.long_ratio, 'short_ratio': ls_ratio.short_ratio}
            )
        
        # Overcrowded shorts (bullish)
        elif ls_ratio.short_ratio > 0.65:
            strength = SignalStrength.VERY_STRONG if ls_ratio.short_ratio > 0.70 else SignalStrength.STRONG
            
            return TradingSignal(
                signal_type=SignalType.OVERCROWDED_SHORT,
                strength=strength,
                direction="long",
                price=price,
                timestamp=datetime.now(),
                reason=f"Overcrowded shorts {ls_ratio.short_ratio*100:.1f}%. Risk of short squeeze.",
                data={'long_ratio': ls_ratio.long_ratio, 'short_ratio': ls_ratio.short_ratio}
            )
        
        return None
    
    def _check_risk_levels(self, price: float) -> Optional[TradingSignal]:
        """
        Check current risk metrics.
        
        Args:
            price: Current price
            
        Returns:
            TradingSignal or None
        """
        metrics = self.ws_handler.get_risk_metrics()
        
        if not metrics:
            return None
        
        # Check if Modified VaR exceeds threshold
        if metrics.var_95_modified and abs(metrics.var_95_modified) > self.risk_threshold:
            
            return TradingSignal(
                signal_type=SignalType.HIGH_RISK,
                strength=SignalStrength.STRONG,
                direction="neutral",
                price=price,
                timestamp=datetime.now(),
                reason=f"High risk detected. VaR(95%): {metrics.var_95_modified*100:.2f}%, Skew: {metrics.skewness:.2f}",
                data={
                    'var_95_modified': metrics.var_95_modified,
                    'skewness': metrics.skewness,
                    'kurtosis': metrics.kurtosis
                }
            )
        
        return None
    
    def get_latest_signals(self, n: int = 10) -> List[TradingSignal]:
        """Get latest N signals."""
        return self.signals[-n:]
    
    def get_signal_summary(self) -> Dict[str, Any]:
        """Get summary of all signals."""
        if not self.signals:
            return {
                'total_signals': 0,
                'by_type': {},
                'by_strength': {},
                'by_direction': {}
            }
        
        by_type = {}
        by_strength = {}
        by_direction = {}
        
        for signal in self.signals:
            # Count by type
            signal_type = signal.signal_type.value
            by_type[signal_type] = by_type.get(signal_type, 0) + 1
            
            # Count by strength
            strength = signal.strength.name
            by_strength[strength] = by_strength.get(strength, 0) + 1
            
            # Count by direction
            direction = signal.direction
            by_direction[direction] = by_direction.get(direction, 0) + 1
        
        return {
            'total_signals': len(self.signals),
            'by_type': by_type,
            'by_strength': by_strength,
            'by_direction': by_direction,
            'latest': self.signals[-1] if self.signals else None
        }


# ==================== EXAMPLE USAGE ====================

async def main():
    """Example usage."""
    analyzer = TradingSignalAnalyzer(
        symbol="BTCUSDT",
        interval="1m",
        risk_threshold=0.03
    )
    
    try:
        # Run for 3 minutes to generate some signals
        print("🧪 Running Signal Analyzer for 3 minutes...")
        print("="*70)
        
        await asyncio.wait_for(analyzer.start(), timeout=180)
        
    except asyncio.TimeoutError:
        print("\n⏰ Test completed")
        
    finally:
        await analyzer.stop()
        
        # Print summary
        summary = analyzer.get_signal_summary()
        
        print("\n" + "="*70)
        print("📊 SIGNAL SUMMARY")
        print("="*70)
        print(f"Total signals: {summary['total_signals']}")
        
        if summary['by_type']:
            print("\nBy Type:")
            for sig_type, count in summary['by_type'].items():
                print(f"   {sig_type:.<30} {count:>3}")
        
        if summary['by_strength']:
            print("\nBy Strength:")
            for strength, count in summary['by_strength'].items():
                print(f"   {strength:.<30} {count:>3}")
        
        if summary['by_direction']:
            print("\nBy Direction:")
            for direction, count in summary['by_direction'].items():
                emoji = {"long": "🟢", "short": "🔴", "neutral": "⚪"}
                print(f"   {emoji.get(direction, '')} {direction:.<25} {count:>3}")
        
        print("\n" + "="*70)
        
        # Show latest signals
        latest = analyzer.get_latest_signals(5)
        if latest:
            print("\n📌 LATEST SIGNALS:")
            for signal in latest:
                print(f"\n{signal}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )
    
    asyncio.run(main())
