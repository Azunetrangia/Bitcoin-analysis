"""
Integration tests for Streamlit dashboard pages.

Tests all 4 dashboard pages to ensure they work correctly.
"""

import pytest
import requests
from datetime import datetime, timedelta

API_BASE = "http://localhost:8000"


class TestAPIEndpoints:
    """Test all API endpoints used by dashboard."""
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = requests.get(f"{API_BASE}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_market_data_endpoint(self):
        """Test market data query endpoint."""
        params = {
            "symbol": "BTCUSDT",
            "interval": "1h",
            "limit": 10
        }
        response = requests.get(f"{API_BASE}/api/v1/market-data/", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert data["interval"] == "1h"
        assert len(data["data"]) > 0
        assert len(data["data"]) <= 10
    
    def test_indicators_endpoint(self):
        """Test technical indicators endpoint."""
        # Use valid historical date range (Dec 2024)
        end = datetime(2024, 12, 1)
        start = end - timedelta(days=7)
        params = {
            "symbol": "BTCUSDT",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "interval": "1h",
            "limit": 100
        }
        response = requests.get(f"{API_BASE}/api/v1/analysis/indicators", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] > 0
        assert "rsi" in data["data"][0]
        assert "macd" in data["data"][0]
        assert "bb_upper" in data["data"][0]
    
    def test_risk_metrics_endpoint(self):
        """Test risk metrics endpoint."""
        # Use valid historical date range (Nov 2024)
        end = datetime(2024, 12, 1)
        start = datetime(2024, 11, 1)
        params = {
            "symbol": "BTCUSDT",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "interval": "1h"
        }
        response = requests.get(f"{API_BASE}/api/v1/analysis/risk-metrics", params=params)
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        metrics = data["metrics"]
        assert "volatility" in metrics or "sharpe_ratio" in metrics or "max_drawdown" in metrics
    
    def test_regimes_endpoint(self):
        """Test regime classification endpoint."""
        # Use valid historical date range (Nov 2024)
        end = datetime(2024, 12, 1)
        start = datetime(2024, 11, 1)
        params = {
            "symbol": "BTCUSDT",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "interval": "1h"
        }
        response = requests.get(f"{API_BASE}/api/v1/analysis/regimes", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] > 0
        assert "regime" in data["regimes"][0]
        assert "bull_prob" in data["regimes"][0]
    
    def test_investment_decision_endpoint(self):
        """Test investment decision endpoint."""
        # Use valid historical date range (Nov 2024)
        end = datetime(2024, 12, 1)
        start = datetime(2024, 11, 1)
        params = {
            "symbol": "BTCUSDT",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "interval": "1h"
        }
        response = requests.get(f"{API_BASE}/api/v1/analysis/decision", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["signal"] in ["Mua mạnh", "Mua", "Giữ", "Bán", "Bán mạnh"]
        assert 0 <= data["score"] <= 100
        assert "factors" in data
        assert "insights" in data


class TestDataIntegrity:
    """Test data quality and consistency."""
    
    def test_data_completeness(self):
        """Test that we have data from 2020 to 2025."""
        params = {
            "symbol": "BTCUSDT",
            "start": "2020-01-01",
            "end": "2025-12-10",
            "interval": "1h",
            "limit": 1
        }
        response = requests.get(f"{API_BASE}/api/v1/market-data/", params=params)
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) > 0
        
        # Check date range
        first_date = datetime.fromisoformat(data["data"][0]["timestamp"])
        assert first_date.year >= 2020
    
    def test_no_missing_indicators(self):
        """Test that all indicators are calculated."""
        # Use valid historical date range (Dec 2024)
        end = datetime(2024, 12, 1)
        start = end - timedelta(days=7)
        params = {
            "symbol": "BTCUSDT",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "interval": "1h",
            "limit": 50
        }
        response = requests.get(f"{API_BASE}/api/v1/analysis/indicators", params=params)
        data = response.json()
        
        required_indicators = ["rsi", "macd", "macd_signal", "bb_upper", "bb_middle", "bb_lower"]
        for indicator in required_indicators:
            assert indicator in data["data"][0], f"Missing indicator: {indicator}"
    
    def test_price_sanity(self):
        """Test that prices are in reasonable range."""
        params = {
            "symbol": "BTCUSDT",
            "limit": 100
        }
        response = requests.get(f"{API_BASE}/api/v1/market-data/", params=params)
        data = response.json()
        
        for candle in data["data"]:
            # Bitcoin price should be positive and reasonable
            assert candle["close"] > 0
            assert candle["close"] < 500000  # Reasonable upper bound
            assert candle["high"] >= candle["close"]
            assert candle["low"] <= candle["close"]
            assert candle["volume"] >= 0


class TestPerformance:
    """Test API performance."""
    
    def test_response_time_indicators(self):
        """Test that indicators endpoint responds quickly."""
        import time
        # Use valid historical date range (Dec 2024)
        end = datetime(2024, 12, 1)
        start = end - timedelta(days=7)
        params = {
            "symbol": "BTCUSDT",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "interval": "1h",
            "limit": 100
        }
        
        start_time = time.time()
        response = requests.get(f"{API_BASE}/api/v1/analysis/indicators", params=params)
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed < 5.0, f"Response took {elapsed:.2f}s, should be < 5s"
    
    def test_response_time_decision(self):
        """Test that investment decision endpoint responds quickly."""
        import time
        # Use valid historical date range (Nov 2024)
        end = datetime(2024, 12, 1)
        start = datetime(2024, 11, 1)
        params = {
            "symbol": "BTCUSDT",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "interval": "1h"
        }
        
        start_time = time.time()
        response = requests.get(f"{API_BASE}/api/v1/analysis/decision", params=params)
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed < 10.0, f"Response took {elapsed:.2f}s, should be < 10s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
