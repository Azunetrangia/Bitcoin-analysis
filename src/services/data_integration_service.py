"""
Data Integration Service
Bridges real-time data collection with database storage.

Author: Bitcoin Market Intelligence Team
Created: 2025-12-10
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
import signal
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.infrastructure.data.websocket_client import BinanceWebSocketClient
from src.domain.services.websocket_handler import WebSocketDataHandler
from src.infrastructure.data.derivatives_client import DerivativesDataClient
from src.domain.services.signal_analyzer import TradingSignalAnalyzer
from src.infrastructure.database.repository import (
    DatabaseRepository,
    CandleData,
    TradeData,
    RiskMetrics,
    DerivativesMetrics,
    TradingSignalData
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataIntegrationService:
    """
    Integrates real-time data collection with database storage.
    Collects data from WebSocket + Derivatives APIs and stores in database.
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1m",
        derivatives_interval: int = 300,  # 5 minutes
        signal_interval: int = 60  # 1 minute
    ):
        """
        Initialize data integration service.
        
        Args:
            symbol: Trading pair to track
            interval: Candle interval
            derivatives_interval: Seconds between derivatives updates
            signal_interval: Seconds between signal generation
        """
        self.symbol = symbol
        self.interval = interval
        self.derivatives_interval = derivatives_interval
        self.signal_interval = signal_interval
        self.running = False
        
        # Initialize components
        self.db = DatabaseRepository()
        self.ws_handler = WebSocketDataHandler(
            symbol=self.symbol,
            interval=self.interval
        )
        self.derivatives_client = DerivativesDataClient()
        self.signal_analyzer = None  # Initialize later with dependencies
        
        # Stats
        self.stats = {
            'candles_saved': 0,
            'trades_saved': 0,
            'risk_metrics_saved': 0,
            'derivatives_saved': 0,
            'signals_saved': 0,
            'start_time': None
        }
    
    async def start(self):
        """Start the integration service"""
        logger.info(f"🚀 Starting Data Integration Service for {self.symbol}")
        logger.info("=" * 60)
        
        # Check database connection
        if not self.db.health_check():
            logger.error("❌ Database connection failed")
            return
        logger.info("✅ Database connected")
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Start WebSocket handler
        await self.ws_handler.start()
        logger.info(f"✅ WebSocket handler started ({self.interval} candles)")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self.stop()))
        signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(self.stop()))
        
        # Run main loops
        await asyncio.gather(
            self._candle_save_loop(),
            self._trade_save_loop(),
            self._risk_metrics_loop(),
            self._derivatives_loop(),
            self._signal_loop(),
            self._stats_loop()
        )
    
    async def _candle_save_loop(self):
        """Save closed candles to database"""
        logger.info("📊 Candle save loop started")
        
        while self.running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                # Get latest candles from handler
                candles = self.ws_handler.get_latest_candles(n=100)
                
                if candles:
                    # Convert to database models
                    candle_data = [
                        CandleData(
                            time=c.close_time,
                            symbol=self.symbol,
                            interval=self.interval,
                            open=Decimal(str(c.open)),
                            high=Decimal(str(c.high)),
                            low=Decimal(str(c.low)),
                            close=Decimal(str(c.close)),
                            volume=Decimal(str(c.volume)),
                            quote_volume=Decimal(str(c.quote_volume)),
                            trades=c.trades
                        )
                        for c in candles
                    ]
                    
                    # Save to database
                    if self.db.insert_candles(candle_data):
                        self.stats['candles_saved'] += len(candle_data)
                        logger.debug(f"💾 Saved {len(candle_data)} candles")
            
            except Exception as e:
                logger.error(f"Error in candle save loop: {e}")
                await asyncio.sleep(5)
    
    async def _trade_save_loop(self):
        """Save trades to database (sample large trades only)"""
        logger.info("💰 Trade save loop started")
        
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Get recent large trades (>0.1 BTC) from trades buffer
                # Note: WebSocketDataHandler stores trades in trades_buffer
                trades = [
                    t for t in self.ws_handler.trades_buffer
                    if t.quantity > 0.1
                ]
                
                if trades:
                    # Convert to database models
                    trade_data = [
                        TradeData(
                            time=t.timestamp,  # Use timestamp instead of time
                            symbol=self.symbol,
                            trade_id=t.trade_id,
                            price=Decimal(str(t.price)),
                            quantity=Decimal(str(t.quantity)),
                            is_buyer_maker=t.is_buyer_maker
                        )
                        for t in trades
                    ]
                    
                    # Save to database
                    if self.db.insert_trades(trade_data):
                        self.stats['trades_saved'] += len(trade_data)
                        logger.debug(f"💾 Saved {len(trade_data)} large trades")
            
            except Exception as e:
                logger.error(f"Error in trade save loop: {e}")
                await asyncio.sleep(5)
    
    async def _risk_metrics_loop(self):
        """Calculate and save risk metrics"""
        logger.info("📈 Risk metrics loop started")
        
        while self.running:
            try:
                await asyncio.sleep(60)  # Calculate every minute
                
                # Get risk metrics from handler
                risk_metrics = self.ws_handler.get_risk_metrics()
                
                if risk_metrics:
                    # risk_metrics is a RiskMetrics object, need to convert to DB model
                    from src.infrastructure.database.repository import RiskMetrics as DBRiskMetrics
                    
                    metrics = DBRiskMetrics(
                        time=datetime.now(),
                        symbol=self.symbol,
                        interval=self.interval,
                        mean_return=Decimal(str(risk_metrics.mean_return)) if risk_metrics.mean_return else None,
                        volatility=Decimal(str(risk_metrics.volatility)) if risk_metrics.volatility else None,
                        var_95=Decimal(str(risk_metrics.var_95)) if risk_metrics.var_95 else None,
                        var_99=Decimal(str(risk_metrics.var_99)) if risk_metrics.var_99 else None,
                        var_95_modified=Decimal(str(risk_metrics.var_95_modified)) if risk_metrics.var_95_modified else None,
                        var_99_modified=Decimal(str(risk_metrics.var_99_modified)) if risk_metrics.var_99_modified else None,
                        expected_shortfall_95=Decimal(str(risk_metrics.expected_shortfall_95)) if risk_metrics.expected_shortfall_95 else None,
                        expected_shortfall_99=Decimal(str(risk_metrics.expected_shortfall_99)) if risk_metrics.expected_shortfall_99 else None,
                        sharpe_ratio=Decimal(str(risk_metrics.sharpe_ratio)) if risk_metrics.sharpe_ratio else None,
                        sortino_ratio=Decimal(str(risk_metrics.sortino_ratio)) if risk_metrics.sortino_ratio else None,
                        max_drawdown=Decimal(str(risk_metrics.max_drawdown)) if risk_metrics.max_drawdown else None,
                        skewness=Decimal(str(risk_metrics.skewness)) if risk_metrics.skewness else None,
                        kurtosis=Decimal(str(risk_metrics.kurtosis)) if risk_metrics.kurtosis else None,
                        sample_size=risk_metrics.sample_size
                    )
                    
                    if self.db.insert_risk_metrics(metrics):
                        self.stats['risk_metrics_saved'] += 1
                        logger.debug(f"💾 Saved risk metrics")
            
            except Exception as e:
                logger.error(f"Error in risk metrics loop: {e}")
                await asyncio.sleep(5)
    
    async def _derivatives_loop(self):
        """Fetch and save derivatives data"""
        logger.info("📊 Derivatives loop started")
        
        while self.running:
            try:
                # Fetch derivatives summary
                summary = await self.derivatives_client.get_derivatives_summary(self.symbol)
                
                if summary:
                    current_time = datetime.now()
                    
                    # Save funding rates
                    for fr in summary['funding_rates']:
                        metrics = DerivativesMetrics(
                            time=current_time,
                            symbol=self.symbol,
                            exchange=fr.exchange,
                            funding_rate=Decimal(str(fr.rate)),
                            funding_rate_annual=Decimal(str(fr.annual_rate)),
                            open_interest=None,
                            open_interest_value=None,
                            long_ratio=None,
                            short_ratio=None,
                            mark_price=None,
                            index_price=None
                        )
                        
                        if self.db.insert_derivatives_metrics(metrics):
                            self.stats['derivatives_saved'] += 1
                    
                    # Save Open Interest
                    for oi in summary['open_interest']:
                        # Update existing record
                        metrics = DerivativesMetrics(
                            time=current_time,
                            symbol=self.symbol,
                            exchange=oi.exchange,
                            funding_rate=None,
                            funding_rate_annual=None,
                            open_interest=Decimal(str(oi.contracts)),
                            open_interest_value=Decimal(str(oi.value_usd)),
                            long_ratio=None,
                            short_ratio=None,
                            mark_price=None,
                            index_price=None
                        )
                        self.db.insert_derivatives_metrics(metrics)
                    
                    # Save Long/Short ratio
                    if summary['long_short_ratio']:
                        lsr = summary['long_short_ratio']
                        metrics = DerivativesMetrics(
                            time=current_time,
                            symbol=self.symbol,
                            exchange=lsr.exchange,
                            funding_rate=None,
                            funding_rate_annual=None,
                            open_interest=None,
                            open_interest_value=None,
                            long_ratio=Decimal(str(lsr.long_ratio)),
                            short_ratio=Decimal(str(lsr.short_ratio)),
                            mark_price=None,
                            index_price=None
                        )
                        self.db.insert_derivatives_metrics(metrics)
                    
                    logger.debug(f"💾 Saved derivatives data")
                
                await asyncio.sleep(self.derivatives_interval)
            
            except Exception as e:
                logger.error(f"Error in derivatives loop: {e}")
                await asyncio.sleep(30)
    
    async def _signal_loop(self):
        """Generate and save trading signals"""
        logger.info("🎯 Signal generation loop started")
        
        # Initialize signal analyzer (needs current price)
        await asyncio.sleep(10)  # Wait for first price data
        
        while self.running:
            try:
                # Get current price
                current_price = self.ws_handler.get_current_price()
                if not current_price:
                    await asyncio.sleep(self.signal_interval)
                    continue
                
                # Initialize analyzer if needed
                if not self.signal_analyzer:
                    self.signal_analyzer = TradingSignalAnalyzer(
                        symbol=self.symbol,
                        current_price=current_price
                    )
                    logger.info("✅ Signal analyzer initialized")
                
                # Get data for analysis
                risk_metrics = self.ws_handler.get_risk_metrics()
                derivatives_summary = await self.derivatives_client.get_derivatives_summary(self.symbol)
                
                # Analyze and generate signals
                signals = await self.signal_analyzer.analyze(
                    risk_metrics=risk_metrics,
                    derivatives_summary=derivatives_summary
                )
                
                # Save signals to database
                for signal in signals:
                    signal_data = TradingSignalData(
                        time=signal.timestamp,
                        symbol=self.symbol,
                        signal_type=signal.signal_type.value,
                        strength=signal.strength.value,
                        direction=signal.direction,
                        price=Decimal(str(signal.price)),
                        reason=signal.reason,
                        data=signal.data
                    )
                    
                    if self.db.insert_trading_signal(signal_data):
                        self.stats['signals_saved'] += 1
                        logger.info(f"🎯 Signal: {signal.signal_type.value} {signal.strength.value} {signal.direction}")
                
                await asyncio.sleep(self.signal_interval)
            
            except Exception as e:
                logger.error(f"Error in signal loop: {e}")
                await asyncio.sleep(10)
    
    async def _stats_loop(self):
        """Print statistics periodically"""
        while self.running:
            await asyncio.sleep(300)  # Every 5 minutes
            
            runtime = datetime.now() - self.stats['start_time']
            
            logger.info("=" * 60)
            logger.info("📊 DATA INTEGRATION STATISTICS")
            logger.info("=" * 60)
            logger.info(f"Runtime: {runtime}")
            logger.info(f"Candles saved: {self.stats['candles_saved']}")
            logger.info(f"Trades saved: {self.stats['trades_saved']}")
            logger.info(f"Risk metrics saved: {self.stats['risk_metrics_saved']}")
            logger.info(f"Derivatives saved: {self.stats['derivatives_saved']}")
            logger.info(f"Signals saved: {self.stats['signals_saved']}")
            
            # WebSocket stats
            ws_stats = self.ws_handler.get_statistics()
            logger.info(f"Total candles: {ws_stats['candles_processed']}")
            logger.info(f"Total trades: {ws_stats['trades_processed']}")
            current_price = ws_stats.get('current_price')
            if current_price:
                logger.info(f"Current price: ${current_price:,.2f}")
            logger.info("=" * 60)
    
    async def stop(self):
        """Stop the integration service"""
        logger.info("⏹️  Stopping Data Integration Service...")
        self.running = False
        
        await self.ws_handler.stop()
        self.db.close()
        
        logger.info("✅ Service stopped gracefully")


# ============================================================
# MAIN
# ============================================================

async def main():
    """Main entry point"""
    service = DataIntegrationService(
        symbol="BTCUSDT",
        interval="1m",
        derivatives_interval=300,  # 5 minutes
        signal_interval=60  # 1 minute
    )
    
    try:
        await service.start()
    except KeyboardInterrupt:
        await service.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await service.stop()


if __name__ == "__main__":
    print("=" * 60)
    print("🔄 Bitcoin Market Intelligence - Data Integration Service")
    print("=" * 60)
    print("📊 Collecting real-time data and storing in database")
    print("🎯 Generating trading signals")
    print("⌨️  Press Ctrl+C to stop")
    print("=" * 60)
    
    asyncio.run(main())
