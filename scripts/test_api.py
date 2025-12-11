#!/usr/bin/env python
"""
API Demo Script - Bitcoin Market Intelligence API

Tests all major API endpoints and displays results.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any


BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_health_endpoints():
    """Test health and info endpoints."""
    print_section("🏥 HEALTH & INFO ENDPOINTS")
    
    # Health check
    r = requests.get(f"{BASE_URL}/health")
    print("✅ GET /health")
    print(json.dumps(r.json(), indent=2))
    
    # Root info
    r = requests.get(f"{BASE_URL}/")
    print("\n✅ GET /")
    print(json.dumps(r.json(), indent=2))


def test_scheduler_endpoints():
    """Test scheduler management endpoints."""
    print_section("⏰ SCHEDULER ENDPOINTS")
    
    # Get status
    r = requests.get(f"{BASE_URL}/api/v1/scheduler/status")
    print("✅ GET /api/v1/scheduler/status")
    print(json.dumps(r.json(), indent=2))
    
    # Start scheduler
    r = requests.post(f"{BASE_URL}/api/v1/scheduler/start")
    print("\n✅ POST /api/v1/scheduler/start")
    print(json.dumps(r.json(), indent=2))
    
    # Get status again
    r = requests.get(f"{BASE_URL}/api/v1/scheduler/status")
    print("\n✅ GET /api/v1/scheduler/status (after start)")
    print(json.dumps(r.json(), indent=2))
    
    # Stop scheduler
    r = requests.post(f"{BASE_URL}/api/v1/scheduler/stop")
    print("\n✅ POST /api/v1/scheduler/stop")
    print(json.dumps(r.json(), indent=2))


def test_market_data_endpoints():
    """Test market data endpoints."""
    print_section("📈 MARKET DATA ENDPOINTS")
    
    print("Note: These endpoints require actual data in storage.")
    print("If no data exists, they will return 404 errors.\n")
    
    # Latest candle
    try:
        r = requests.get(f"{BASE_URL}/api/v1/market-data/latest?symbol=BTCUSDT&interval=1h")
        print("✅ GET /api/v1/market-data/latest")
        if r.status_code == 200:
            print(json.dumps(r.json(), indent=2))
        else:
            print(f"⚠️  Status {r.status_code}: {r.json().get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Query data
    try:
        end = datetime.now()
        start = end - timedelta(hours=24)
        r = requests.get(
            f"{BASE_URL}/api/v1/market-data/",
            params={
                "symbol": "BTCUSDT",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "interval": "1h",
                "limit": 10
            }
        )
        print("\n✅ GET /api/v1/market-data/ (query)")
        if r.status_code == 200:
            data = r.json()
            print(f"Count: {data.get('count', 0)} candles")
            print(f"Symbol: {data.get('symbol')}")
            print(f"Interval: {data.get('interval')}")
        else:
            print(f"⚠️  Status {r.status_code}: {r.json().get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_analysis_endpoints():
    """Test analysis endpoints."""
    print_section("🔬 ANALYSIS ENDPOINTS")
    
    print("Note: Analysis endpoints require market data to be present.\n")
    
    # Technical indicators
    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/analysis/indicators",
            params={"symbol": "BTCUSDT", "interval": "1h", "limit": 5}
        )
        print("✅ GET /api/v1/analysis/indicators")
        if r.status_code == 200:
            data = r.json()
            print(f"Count: {data.get('count', 0)} indicators")
        else:
            print(f"⚠️  Status {r.status_code}: {r.json().get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Risk metrics
    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/analysis/risk-metrics",
            params={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "window": 30,
                "risk_free_rate": 0.02,
                "confidence_level": 0.95
            }
        )
        print("\n✅ GET /api/v1/analysis/risk-metrics")
        if r.status_code == 200:
            data = r.json()
            print(f"Symbol: {data.get('symbol')}")
            print(f"Interval: {data.get('interval')}")
            if 'sharpe_ratio' in data:
                print(f"Sharpe Ratio: {data['sharpe_ratio'].get('sharpe_ratio', 'N/A')}")
        else:
            print(f"⚠️  Status {r.status_code}: {r.json().get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_pipeline_endpoints():
    """Test pipeline execution endpoints."""
    print_section("🔄 PIPELINE ENDPOINTS")
    
    print("Note: Pipeline endpoints trigger actual data operations.\n")
    
    # Incremental update
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/scheduler/pipeline/update",
            params={"symbol": "BTCUSDT", "interval": "1h", "limit": 2}
        )
        print("✅ POST /api/v1/scheduler/pipeline/update")
        if r.status_code == 200:
            data = r.json()
            print(f"Pipeline: {data.get('pipeline_type')}")
            print(f"Success: {data.get('success')}")
            print(f"Duration: {data.get('duration_seconds', 0):.2f}s")
            if data.get('metrics'):
                print(f"Metrics: {json.dumps(data['metrics'], indent=2)}")
        else:
            print(f"⚠️  Status {r.status_code}: {r.json().get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all API tests."""
    print("\n" + "="*60)
    print("  🚀 Bitcoin Market Intelligence API - Demo Script")
    print("="*60)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test all endpoint categories
        test_health_endpoints()
        test_scheduler_endpoints()
        test_market_data_endpoints()
        test_analysis_endpoints()
        test_pipeline_endpoints()
        
        print_section("✅ ALL TESTS COMPLETED")
        print("API is running and responding correctly!")
        print(f"\n📚 Interactive docs: {BASE_URL}/docs")
        print(f"📋 OpenAPI schema: {BASE_URL}/openapi.json")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to API server")
        print(f"Make sure the server is running at {BASE_URL}")
        print("\nStart the server with:")
        print("  python -m src.api.main")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")


if __name__ == "__main__":
    main()
