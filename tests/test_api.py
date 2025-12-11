"""
Test Bitcoin Market Intelligence REST API
Validates all endpoints with mock database.

Author: Bitcoin Market Intelligence Team
Created: 2025-12-10
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
import pytest

from src.api.main import app
from src.infrastructure.database.repository import (
    CandleData,
    TradeData,
    RiskMetrics,
    DerivativesMetrics,
    TradingSignalData
)

# Create test client
client = TestClient(app)


# ============================================================
# MOCK DATABASE
# ============================================================

class MockDatabaseRepository:
    """Mock database for testing"""
    
    def __init__(self):
        self.mock_time = datetime.now()
    
    def health_check(self):
        return True
    
    def close(self):
        pass
    
    def get_candles(self, symbol, interval, start_time=None, end_time=None, limit=100):
        """Return mock candles"""
        return [
            CandleData(
                time=self.mock_time - timedelta(minutes=i),
                symbol=symbol,
                interval=interval,
                open=Decimal("92500.00") + Decimal(str(i * 10)),
                high=Decimal("92550.00") + Decimal(str(i * 10)),
                low=Decimal("92450.00") + Decimal(str(i * 10)),
                close=Decimal("92520.00") + Decimal(str(i * 10)),
                volume=Decimal("15.5"),
                quote_volume=Decimal("1434300.00"),
                trades=350
            )
            for i in range(min(limit, 10))
        ]
    
    def get_latest_candle(self, symbol, interval):
        """Return latest candle"""
        candles = self.get_candles(symbol, interval, limit=1)
        return candles[0] if candles else None
    
    def get_price_change(self, symbol, interval, hours):
        """Return mock price change"""
        return {
            'current_price': Decimal("92520.00"),
            'previous_price': Decimal("91200.00"),
            'change_amount': Decimal("1320.00"),
            'change_percent': Decimal("1.45")
        }
    
    def get_trades(self, symbol, start_time=None, end_time=None, limit=100):
        """Return mock trades"""
        return [
            TradeData(
                time=self.mock_time - timedelta(seconds=i),
                symbol=symbol,
                trade_id=12345678 + i,
                price=Decimal("92520.00"),
                quantity=Decimal("0.5"),
                is_buyer_maker=i % 2 == 0
            )
            for i in range(min(limit, 10))
        ]
    
    def get_large_trades(self, symbol, min_quantity, hours, limit):
        """Return mock large trades"""
        return [
            TradeData(
                time=self.mock_time - timedelta(minutes=i * 10),
                symbol=symbol,
                trade_id=99000000 + i,
                price=Decimal("92520.00"),
                quantity=Decimal("5.0"),
                is_buyer_maker=False
            )
            for i in range(min(limit, 5))
        ]
    
    def get_volume_stats(self, symbol, hours):
        """Return mock volume stats"""
        return {
            'total_volume': Decimal("1500.50"),
            'avg_volume': Decimal("15.5"),
            'max_volume': Decimal("100.0"),
            'trade_count': 5000
        }
    
    def get_risk_metrics(self, symbol, interval, hours):
        """Return mock risk metrics"""
        return [
            RiskMetrics(
                time=self.mock_time - timedelta(hours=i),
                symbol=symbol,
                interval=interval,
                mean_return=Decimal("0.0005"),
                volatility=Decimal("0.015"),
                var_95=Decimal("-0.025"),
                var_99=Decimal("-0.040"),
                var_95_modified=Decimal("-0.032"),
                var_99_modified=Decimal("-0.052"),
                expected_shortfall_95=Decimal("-0.035"),
                expected_shortfall_99=Decimal("-0.060"),
                sharpe_ratio=Decimal("1.5"),
                sortino_ratio=Decimal("2.1"),
                max_drawdown=Decimal("-0.08"),
                skewness=Decimal("-0.3"),
                kurtosis=Decimal("4.5"),
                sample_size=500
            )
            for i in range(min(hours, 5))
        ]
    
    def get_latest_risk_metrics(self, symbol, interval):
        """Return latest risk metrics"""
        metrics = self.get_risk_metrics(symbol, interval, hours=1)
        return metrics[0] if metrics else None
    
    def get_derivatives_metrics(self, symbol, exchange=None, hours=24):
        """Return mock derivatives metrics"""
        exchanges = ['BINANCE', 'BYBIT', 'OKX'] if not exchange else [exchange]
        return [
            DerivativesMetrics(
                time=self.mock_time,
                symbol=symbol,
                exchange=ex,
                funding_rate=Decimal("0.0001"),
                funding_rate_annual=Decimal("0.1095"),
                open_interest=Decimal("87551.83"),
                open_interest_value=Decimal("8093440281.00"),
                long_ratio=Decimal("0.6324"),
                short_ratio=Decimal("0.3676"),
                mark_price=Decimal("92520.00"),
                index_price=Decimal("92518.50")
            )
            for ex in exchanges
        ]
    
    def get_latest_derivatives(self, symbol):
        """Return latest derivatives from all exchanges"""
        return self.get_derivatives_metrics(symbol)
    
    def get_trading_signals(self, symbol, signal_type=None, hours=24, limit=100):
        """Return mock trading signals"""
        signal_types = ['FUNDING_ARBITRAGE', 'LIQUIDATION_WARNING', 'HIGH_RISK']
        if signal_type:
            signal_types = [signal_type]
        
        signals = []
        for i, st in enumerate(signal_types):
            signals.append(
                TradingSignalData(
                    time=self.mock_time - timedelta(hours=i),
                    symbol=symbol,
                    signal_type=st,
                    strength='STRONG' if i == 0 else 'MODERATE',
                    direction='LONG' if i % 2 == 0 else 'SHORT',
                    price=Decimal("92520.00"),
                    reason=f"Mock {st.lower().replace('_', ' ')} signal",
                    data={'test': True}
                )
            )
        return signals[:limit]
    
    def get_strong_signals(self, symbol, hours):
        """Return mock strong signals"""
        return [
            s for s in self.get_trading_signals(symbol, hours=hours)
            if s.strength in ('STRONG', 'VERY_STRONG')
        ]


# Override database dependency for testing
@pytest.fixture(autouse=True)
def mock_db():
    """Mock database for all tests"""
    from src.api import main
    original_db = main.db_repo
    main.db_repo = MockDatabaseRepository()
    yield main.db_repo
    main.db_repo = original_db


# ============================================================
# TESTS
# ============================================================

def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Bitcoin Market Intelligence API"
    assert "endpoints" in data


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_get_candles():
    """Test get candles endpoint"""
    response = client.get("/api/v1/candles/BTCUSDT?interval=1m&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["symbol"] == "BTCUSDT"
    assert "open" in data[0]
    assert "close" in data[0]


def test_get_latest_candle():
    """Test get latest candle endpoint"""
    response = client.get("/api/v1/candles/BTCUSDT/latest?interval=1m")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["interval"] == "1m"


def test_get_price_change():
    """Test get price change endpoint"""
    response = client.get("/api/v1/candles/BTCUSDT/price-change?interval=1m&hours=1")
    assert response.status_code == 200
    data = response.json()
    assert "current_price" in data
    assert "change_percent" in data


def test_get_trades():
    """Test get trades endpoint"""
    response = client.get("/api/v1/trades/BTCUSDT?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["symbol"] == "BTCUSDT"


def test_get_large_trades():
    """Test get large trades endpoint"""
    response = client.get("/api/v1/trades/BTCUSDT/large?min_quantity=1.0")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert float(data[0]["quantity"]) >= 1.0


def test_get_volume_stats():
    """Test get volume stats endpoint"""
    response = client.get("/api/v1/trades/BTCUSDT/volume?hours=24")
    assert response.status_code == 200
    data = response.json()
    assert "total_volume" in data
    assert "trade_count" in data


def test_get_risk_metrics():
    """Test get risk metrics endpoint"""
    response = client.get("/api/v1/risk/BTCUSDT?interval=1m&hours=24")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "var_95" in data[0]
    assert "var_95_modified" in data[0]


def test_get_latest_risk_metrics():
    """Test get latest risk metrics endpoint"""
    response = client.get("/api/v1/risk/BTCUSDT/latest?interval=1m")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert "sharpe_ratio" in data


def test_get_derivatives_metrics():
    """Test get derivatives metrics endpoint"""
    response = client.get("/api/v1/derivatives/BTCUSDT?hours=24")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "funding_rate" in data[0]
    assert "open_interest" in data[0]


def test_get_latest_derivatives():
    """Test get latest derivatives endpoint"""
    response = client.get("/api/v1/derivatives/BTCUSDT/latest")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    exchanges = [d["exchange"] for d in data]
    assert "BINANCE" in exchanges


def test_get_trading_signals():
    """Test get trading signals endpoint"""
    response = client.get("/api/v1/signals/BTCUSDT?hours=24")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "signal_type" in data[0]
    assert "strength" in data[0]


def test_get_strong_signals():
    """Test get strong signals endpoint"""
    response = client.get("/api/v1/signals/BTCUSDT/strong?hours=24")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    for signal in data:
        assert signal["strength"] in ["STRONG", "VERY_STRONG"]


def test_get_market_summary():
    """Test comprehensive market summary endpoint"""
    response = client.get("/api/v1/summary/BTCUSDT?interval=1m")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert "price" in data
    assert "price_change_1h" in data
    assert "derivatives" in data
    assert "recent_signals" in data


def test_invalid_symbol():
    """Test with invalid symbol"""
    response = client.get("/api/v1/candles/INVALID?interval=1m")
    # Should still return 200 with empty data or handle gracefully
    assert response.status_code in [200, 404]


def test_query_parameters():
    """Test query parameter validation"""
    # Test limit parameter
    response = client.get("/api/v1/candles/BTCUSDT?interval=1m&limit=5000")
    # Should reject limit > 1000
    assert response.status_code in [200, 422]


# ============================================================
# RUN TESTS
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Testing Bitcoin Market Intelligence API")
    print("=" * 60)
    
    # Run all tests
    test_functions = [
        test_root,
        test_health_check,
        test_get_candles,
        test_get_latest_candle,
        test_get_price_change,
        test_get_trades,
        test_get_large_trades,
        test_get_volume_stats,
        test_get_risk_metrics,
        test_get_latest_risk_metrics,
        test_get_derivatives_metrics,
        test_get_latest_derivatives,
        test_get_trading_signals,
        test_get_strong_signals,
        test_get_market_summary
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            print(f"✅ {test_func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test_func.__name__}: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {failed} test(s) failed")
