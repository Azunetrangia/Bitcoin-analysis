"""
WebSocket Client for Real-Time Cryptocurrency Data Streaming

Implements real-time data streaming from Binance WebSocket API.
Supports:
- Kline (candlestick) streams
- Trade streams
- Ticker streams
- Depth (order book) streams

Author: Bitcoin Market Intelligence Team
Created: 2025-12-10
Priority: HIGH (Phase 1 - Real-time Data Infrastructure)
"""

import json
import asyncio
import logging
from typing import Callable, Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

try:
    import websockets
    from websockets.asyncio.client import connect
except ImportError:
    raise ImportError(
        "websockets library required. Install with: pip install websockets"
    )

logger = logging.getLogger(__name__)


class StreamType(Enum):
    """WebSocket stream types supported by Binance."""
    
    KLINE = "kline"           # Candlestick data
    TRADE = "trade"           # Individual trades
    TICKER = "miniTicker"     # 24hr mini ticker
    DEPTH = "depth"           # Order book updates
    AGG_TRADE = "aggTrade"    # Aggregated trades


class BinanceWebSocketClient:
    """
    Async WebSocket client for Binance real-time data streaming.
    
    Features:
    - Auto-reconnection on disconnect
    - Multiple stream subscriptions
    - Callback-based message handling
    - Error handling and logging
    
    Example:
        ```python
        client = BinanceWebSocketClient()
        
        def on_kline(data):
            print(f"New candle: {data}")
        
        await client.subscribe_kline("BTCUSDT", "1m", on_kline)
        await client.connect()
        ```
    """
    
    BASE_URL = "wss://stream.binance.com:9443"
    TESTNET_URL = "wss://testnet.binance.vision"
    
    def __init__(self, testnet: bool = False):
        """
        Initialize WebSocket client.
        
        Args:
            testnet: Use testnet endpoint (default: False)
        """
        self.base_url = self.TESTNET_URL if testnet else self.BASE_URL
        self.websocket: Optional[websockets.ClientConnection] = None
        self.subscriptions: Dict[str, Callable] = {}
        self.is_running = False
        self._reconnect_delay = 5  # seconds
        self._max_reconnect_attempts = 5
        
    async def connect(self) -> None:
        """
        Establish WebSocket connection and start listening.
        
        Automatically reconnects on disconnect.
        """
        self.is_running = True
        reconnect_count = 0
        
        while self.is_running:
            try:
                # Build combined stream URL
                streams = list(self.subscriptions.keys())
                if not streams:
                    logger.warning("No streams subscribed. Waiting...")
                    await asyncio.sleep(1)
                    continue
                
                stream_path = "/".join(streams)
                url = f"{self.base_url}/stream?streams={stream_path}"
                
                logger.info(f"🔌 Connecting to Binance WebSocket: {len(streams)} streams")
                
                async with connect(url) as websocket:
                    self.websocket = websocket
                    reconnect_count = 0  # Reset on successful connection
                    logger.info("✅ WebSocket connected")
                    
                    # Listen for messages
                    await self._listen()
                    
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"⚠️ WebSocket closed: {e}")
                await self._handle_reconnect(reconnect_count)
                reconnect_count += 1
                
            except Exception as e:
                logger.error(f"❌ WebSocket error: {e}", exc_info=True)
                await self._handle_reconnect(reconnect_count)
                reconnect_count += 1
                
    async def _listen(self) -> None:
        """Listen for incoming WebSocket messages."""
        while self.is_running and self.websocket:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # Route message to appropriate callback
                await self._route_message(data)
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed while listening")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message: {e}")
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                
    async def _route_message(self, data: Dict[str, Any]) -> None:
        """
        Route incoming message to appropriate callback.
        
        Args:
            data: Parsed JSON message from WebSocket
        """
        stream_name = data.get("stream")
        
        if not stream_name:
            logger.warning(f"Message without stream name: {data}")
            return
        
        callback = self.subscriptions.get(stream_name)
        
        if callback:
            try:
                # Execute callback (may be sync or async)
                if asyncio.iscoroutinefunction(callback):
                    await callback(data.get("data", data))
                else:
                    callback(data.get("data", data))
            except Exception as e:
                logger.error(f"Callback error for {stream_name}: {e}", exc_info=True)
        else:
            logger.debug(f"No callback registered for stream: {stream_name}")
            
    async def _handle_reconnect(self, attempt: int) -> None:
        """
        Handle reconnection logic with exponential backoff.
        
        Args:
            attempt: Current reconnection attempt number
        """
        if attempt >= self._max_reconnect_attempts:
            logger.error(f"❌ Max reconnection attempts ({self._max_reconnect_attempts}) reached")
            self.is_running = False
            return
        
        delay = min(self._reconnect_delay * (2 ** attempt), 60)  # Max 60s
        logger.info(f"🔄 Reconnecting in {delay}s (attempt {attempt + 1}/{self._max_reconnect_attempts})")
        await asyncio.sleep(delay)
        
    async def disconnect(self) -> None:
        """Gracefully close WebSocket connection."""
        self.is_running = False
        
        if self.websocket:
            await self.websocket.close()
            logger.info("🔌 WebSocket disconnected")
            
    # Stream Subscription Methods
    
    def subscribe_kline(
        self,
        symbol: str,
        interval: str,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Subscribe to kline (candlestick) stream.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Kline interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            callback: Function to call with kline data
            
        Example:
            ```python
            def on_kline(data):
                k = data['k']
                print(f"{k['s']} close: {k['c']}")
            
            client.subscribe_kline("BTCUSDT", "1m", on_kline)
            ```
        """
        stream_name = f"{symbol.lower()}@kline_{interval}"
        self.subscriptions[stream_name] = callback
        logger.info(f"📊 Subscribed to kline: {stream_name}")
        
    def subscribe_trade(
        self,
        symbol: str,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Subscribe to trade stream (individual trades).
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            callback: Function to call with trade data
        """
        stream_name = f"{symbol.lower()}@trade"
        self.subscriptions[stream_name] = callback
        logger.info(f"💱 Subscribed to trades: {stream_name}")
        
    def subscribe_ticker(
        self,
        symbol: str,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Subscribe to 24hr mini ticker stream.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            callback: Function to call with ticker data
        """
        stream_name = f"{symbol.lower()}@miniTicker"
        self.subscriptions[stream_name] = callback
        logger.info(f"📈 Subscribed to ticker: {stream_name}")
        
    def subscribe_depth(
        self,
        symbol: str,
        levels: int = 20,
        update_speed: str = "1000ms",
        callback: Callable[[Dict[str, Any]], None] = None
    ) -> None:
        """
        Subscribe to order book depth stream.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            levels: Order book depth (5, 10, 20)
            update_speed: Update frequency (1000ms or 100ms)
            callback: Function to call with depth data
        """
        stream_name = f"{symbol.lower()}@depth{levels}@{update_speed}"
        self.subscriptions[stream_name] = callback
        logger.info(f"📚 Subscribed to depth: {stream_name}")
        
    def subscribe_agg_trade(
        self,
        symbol: str,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Subscribe to aggregated trade stream.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            callback: Function to call with aggregated trade data
        """
        stream_name = f"{symbol.lower()}@aggTrade"
        self.subscriptions[stream_name] = callback
        logger.info(f"🔀 Subscribed to aggregated trades: {stream_name}")
        
    def unsubscribe(self, stream_name: str) -> None:
        """
        Unsubscribe from a stream.
        
        Args:
            stream_name: Name of the stream to unsubscribe from
        """
        if stream_name in self.subscriptions:
            del self.subscriptions[stream_name]
            logger.info(f"🚫 Unsubscribed from: {stream_name}")
        else:
            logger.warning(f"Stream not found: {stream_name}")
            
    def unsubscribe_all(self) -> None:
        """Unsubscribe from all streams."""
        count = len(self.subscriptions)
        self.subscriptions.clear()
        logger.info(f"🚫 Unsubscribed from all {count} streams")
        
    # Utility Methods
    
    def get_subscriptions(self) -> List[str]:
        """Get list of active stream subscriptions."""
        return list(self.subscriptions.keys())
    
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        return self.websocket is not None and self.is_running


# Example Usage & Testing
async def main():
    """Example usage of BinanceWebSocketClient."""
    client = BinanceWebSocketClient()
    
    # Define callbacks
    def on_kline(data):
        """Handle kline data."""
        k = data['k']
        logger.info(
            f"🕯️ {k['s']} {k['i']} | "
            f"O: {k['o']} H: {k['h']} L: {k['l']} C: {k['c']} | "
            f"V: {k['v']} | Closed: {k['x']}"
        )
    
    def on_trade(data):
        """Handle trade data."""
        logger.info(
            f"💱 {data['s']} | "
            f"Price: {data['p']} | Qty: {data['q']} | "
            f"Buyer: {'Maker' if data['m'] else 'Taker'}"
        )
    
    def on_ticker(data):
        """Handle ticker data."""
        logger.info(
            f"📈 {data['s']} | "
            f"Price: {data['c']} | "
            f"24h Change: {data['P']}% | "
            f"24h Volume: {data['v']}"
        )
    
    # Subscribe to streams
    client.subscribe_kline("BTCUSDT", "1m", on_kline)
    client.subscribe_trade("BTCUSDT", on_trade)
    client.subscribe_ticker("BTCUSDT", on_ticker)
    
    # Connect and run
    try:
        await client.connect()
    except KeyboardInterrupt:
        logger.info("⚠️ Interrupted by user")
        await client.disconnect()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Run example
    asyncio.run(main())
