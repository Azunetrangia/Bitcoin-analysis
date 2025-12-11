"""
WebSocket Data Handler Service

Processes real-time data from WebSocket streams and integrates with existing services.

Features:
- Real-time price tracking
- Automatic database storage
- Risk metrics calculation on new data
- Trade signal generation
- Alert triggering

Author: Bitcoin Market Intelligence Team
Created: 2025-12-10
Priority: HIGH (Phase 1 - Real-time Data Infrastructure)
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd

from src.infrastructure.data.websocket_client import BinanceWebSocketClient
from src.domain.services.risk_calculator import RiskCalculatorService
from src.domain.models.risk_metrics import RiskMetrics

logger = logging.getLogger(__name__)


@dataclass
class RealtimeCandle:
    """Real-time candlestick data from WebSocket."""
    
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: int
    is_closed: bool
    
    @classmethod
    def from_binance_kline(cls, data: Dict[str, Any]) -> 'RealtimeCandle':
        """
        Create RealtimeCandle from Binance kline data.
        
        Args:
            data: Kline data from Binance WebSocket
            
        Returns:
            RealtimeCandle instance
        """
        k = data['k']
        return cls(
            symbol=k['s'],
            interval=k['i'],
            open_time=datetime.fromtimestamp(k['t'] / 1000),
            close_time=datetime.fromtimestamp(k['T'] / 1000),
            open=float(k['o']),
            high=float(k['h']),
            low=float(k['l']),
            close=float(k['c']),
            volume=float(k['v']),
            quote_volume=float(k['q']),
            trades=int(k['n']),
            is_closed=k['x']
        )


@dataclass
class RealtimeTrade:
    """Real-time trade data from WebSocket."""
    
    symbol: str
    trade_id: int
    price: float
    quantity: float
    timestamp: datetime
    is_buyer_maker: bool  # True = sell, False = buy
    
    @classmethod
    def from_binance_trade(cls, data: Dict[str, Any]) -> 'RealtimeTrade':
        """Create RealtimeTrade from Binance trade data."""
        return cls(
            symbol=data['s'],
            trade_id=data['t'],
            price=float(data['p']),
            quantity=float(data['q']),
            timestamp=datetime.fromtimestamp(data['T'] / 1000),
            is_buyer_maker=data['m']
        )


class WebSocketDataHandler:
    """
    Handles real-time data from WebSocket and integrates with services.
    
    Features:
    - Maintains price history buffer
    - Calculates risk metrics in real-time
    - Detects significant price moves
    - Stores data to database
    - Triggers alerts
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1m",
        buffer_size: int = 500,  # Keep last 500 candles for metrics
        risk_calculator: Optional[RiskCalculatorService] = None
    ):
        """
        Initialize WebSocket data handler.
        
        Args:
            symbol: Trading pair to track
            interval: Kline interval (1m, 5m, 15m, etc.)
            buffer_size: Number of candles to keep in memory
            risk_calculator: Risk calculator service instance
        """
        self.symbol = symbol
        self.interval = interval
        self.buffer_size = buffer_size
        
        # Services
        self.ws_client = BinanceWebSocketClient()
        self.risk_calculator = risk_calculator or RiskCalculatorService()
        
        # Data buffers
        self.candles_buffer: List[RealtimeCandle] = []
        self.trades_buffer: List[RealtimeTrade] = []
        
        # State tracking
        self.current_candle: Optional[RealtimeCandle] = None
        self.last_risk_metrics: Optional[RiskMetrics] = None
        self.last_closed_candle_time: Optional[datetime] = None
        
        # Statistics
        self.total_candles_processed = 0
        self.total_trades_processed = 0
        self.started_at: Optional[datetime] = None
        
    async def start(self) -> None:
        """Start WebSocket data handler."""
        self.started_at = datetime.now()
        
        # Subscribe to streams
        self.ws_client.subscribe_kline(self.symbol, self.interval, self._on_kline)
        self.ws_client.subscribe_trade(self.symbol, self._on_trade)
        
        logger.info(f"🚀 Starting WebSocket handler for {self.symbol} {self.interval}")
        logger.info(f"   Buffer size: {self.buffer_size} candles")
        logger.info(f"   Subscriptions: {len(self.ws_client.get_subscriptions())}")
        
        # Start WebSocket client
        await self.ws_client.connect()
        
    async def stop(self) -> None:
        """Stop WebSocket data handler."""
        await self.ws_client.disconnect()
        
        duration = (datetime.now() - self.started_at).total_seconds() if self.started_at else 0
        logger.info(f"🛑 WebSocket handler stopped")
        logger.info(f"   Runtime: {duration:.1f}s")
        logger.info(f"   Candles: {self.total_candles_processed}")
        logger.info(f"   Trades:  {self.total_trades_processed}")
        
    def _on_kline(self, data: Dict[str, Any]) -> None:
        """
        Handle incoming kline data.
        
        Args:
            data: Kline data from WebSocket
        """
        candle = RealtimeCandle.from_binance_kline(data)
        self.current_candle = candle
        
        # When candle closes, process it
        if candle.is_closed:
            self._process_closed_candle(candle)
            
    def _process_closed_candle(self, candle: RealtimeCandle) -> None:
        """
        Process a closed candle.
        
        Args:
            candle: Closed candle to process
        """
        # Add to buffer
        self.candles_buffer.append(candle)
        
        # Maintain buffer size
        if len(self.candles_buffer) > self.buffer_size:
            self.candles_buffer.pop(0)
        
        self.total_candles_processed += 1
        self.last_closed_candle_time = candle.close_time
        
        # Calculate risk metrics if we have enough data
        if len(self.candles_buffer) >= 100:
            self._calculate_risk_metrics()
        
        # Check for significant moves
        self._check_price_alerts(candle)
        
        logger.info(
            f"📊 Candle #{self.total_candles_processed} | {candle.symbol} {candle.interval} | "
            f"O: ${candle.open:,.2f} H: ${candle.high:,.2f} "
            f"L: ${candle.low:,.2f} C: ${candle.close:,.2f} | "
            f"V: {candle.volume:,.2f}"
        )
        
    def _on_trade(self, data: Dict[str, Any]) -> None:
        """
        Handle incoming trade data.
        
        Args:
            data: Trade data from WebSocket
        """
        trade = RealtimeTrade.from_binance_trade(data)
        
        # Add to buffer
        self.trades_buffer.append(trade)
        
        # Keep only recent trades (last 1000)
        if len(self.trades_buffer) > 1000:
            self.trades_buffer.pop(0)
        
        self.total_trades_processed += 1
        
        # Log significant trades (> 0.1 BTC)
        if trade.quantity > 0.1:
            side = "🔴 SELL" if trade.is_buyer_maker else "🟢 BUY"
            logger.info(
                f"💎 LARGE TRADE | {side} | "
                f"${trade.price:,.2f} x {trade.quantity:.4f} BTC = "
                f"${trade.price * trade.quantity:,.0f}"
            )
            
    def _calculate_risk_metrics(self) -> None:
        """Calculate risk metrics from candle buffer."""
        # Convert candles to price series
        prices = pd.Series([c.close for c in self.candles_buffer])
        
        try:
            # Calculate metrics
            metrics = self.risk_calculator.calculate_all_metrics(
                prices,
                periods_per_year=525600 if self.interval == "1m" else 8760  # Minutes or hours
            )
            
            self.last_risk_metrics = metrics
            
            # Log if significant changes
            if metrics.var_95_modified and abs(metrics.var_95_modified) > 0.03:
                logger.warning(
                    f"⚠️ HIGH RISK | VaR(95%): {metrics.var_95_modified*100:.2f}% | "
                    f"Skew: {metrics.skewness:.2f} | Kurt: {metrics.kurtosis:.2f}"
                )
                
        except Exception as e:
            logger.error(f"Failed to calculate risk metrics: {e}")
            
    def _check_price_alerts(self, candle: RealtimeCandle) -> None:
        """
        Check for significant price moves and trigger alerts.
        
        Args:
            candle: Current candle to check
        """
        if len(self.candles_buffer) < 2:
            return
        
        prev_candle = self.candles_buffer[-2]
        
        # Calculate percentage change
        pct_change = ((candle.close - prev_candle.close) / prev_candle.close) * 100
        
        # Alert on >1% moves
        if abs(pct_change) > 1.0:
            direction = "🚀 PUMP" if pct_change > 0 else "💥 DUMP"
            logger.warning(
                f"{direction} | {candle.symbol} | "
                f"${prev_candle.close:,.2f} → ${candle.close:,.2f} | "
                f"{pct_change:+.2f}%"
            )
            
    # Public API Methods
    
    def get_current_price(self) -> Optional[float]:
        """Get current real-time price."""
        return self.current_candle.close if self.current_candle else None
    
    def get_latest_candles(self, n: int = 50) -> List[RealtimeCandle]:
        """
        Get latest N candles from buffer.
        
        Args:
            n: Number of candles to return
            
        Returns:
            List of latest candles
        """
        return self.candles_buffer[-n:]
    
    def get_price_series(self) -> pd.Series:
        """Get price series from buffer."""
        prices = [c.close for c in self.candles_buffer]
        timestamps = [c.close_time for c in self.candles_buffer]
        return pd.Series(prices, index=timestamps)
    
    def get_risk_metrics(self) -> Optional[RiskMetrics]:
        """Get latest calculated risk metrics."""
        return self.last_risk_metrics
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get handler statistics."""
        runtime = (datetime.now() - self.started_at).total_seconds() if self.started_at else 0
        
        return {
            'symbol': self.symbol,
            'interval': self.interval,
            'runtime_seconds': runtime,
            'candles_processed': self.total_candles_processed,
            'trades_processed': self.total_trades_processed,
            'buffer_size': len(self.candles_buffer),
            'current_price': self.get_current_price(),
            'last_update': self.last_closed_candle_time,
            'has_risk_metrics': self.last_risk_metrics is not None
        }


# Example Usage
async def main():
    """Example usage of WebSocketDataHandler."""
    handler = WebSocketDataHandler(
        symbol="BTCUSDT",
        interval="1m",
        buffer_size=500
    )
    
    try:
        # Start handler
        await handler.start()
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
        await handler.stop()
        
        # Print statistics
        stats = handler.get_statistics()
        print("\n" + "="*70)
        print("📊 SESSION STATISTICS")
        print("="*70)
        for key, value in stats.items():
            print(f"{key:.<30} {value}")
        print("="*70)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Run handler
    asyncio.run(main())
