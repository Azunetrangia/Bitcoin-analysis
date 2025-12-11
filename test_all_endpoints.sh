#!/bin/bash
# Test all API endpoints used by Streamlit pages

echo "=================================================="
echo "Testing All API Endpoints"
echo "=================================================="

echo ""
echo "1. Testing Market Data endpoint (Market Overview page)..."
curl -s "http://localhost:8000/api/v1/market-data/?symbol=BTCUSDT&interval=1h&start=2025-12-09T00:00:00&end=2025-12-10T23:59:59&limit=10" | jq '{success, count}'

echo ""
echo "2. Testing Indicators endpoint (Technical Analysis page)..."
curl -s "http://localhost:8000/api/v1/analysis/indicators?symbol=BTCUSDT&interval=1h&start=2025-12-09T00:00:00&end=2025-12-10T23:59:59" | jq '{success, count}'

echo ""
echo "3. Testing Regimes endpoint (Regime Classification page)..."
curl -s "http://localhost:8000/api/v1/analysis/regimes?symbol=BTCUSDT&interval=1h&start=2025-11-01T00:00:00&end=2025-12-10T23:59:59" | jq '{success, count}'

echo ""
echo "4. Testing Candles endpoint (Live Trading page)..."
curl -s "http://localhost:8000/api/v1/candles/BTCUSDT?limit=5" | jq 'length'

echo ""
echo "5. Testing Summary endpoint (Live Trading page)..."
curl -s "http://localhost:8000/api/v1/summary/BTCUSDT" | jq '{symbol, price: .price.close}'

echo ""
echo "=================================================="
echo "✅ All API Endpoints Tested"
echo "=================================================="
echo ""
echo "📊 Pages Status:"
echo "  1. Market Overview     → /api/v1/market-data/"
echo "  2. Technical Analysis  → /api/v1/analysis/indicators"
echo "  3. Risk Analysis       → /api/v1/market-data/ (local calculations)"
echo "  4. Regime Classification → /api/v1/analysis/regimes"
echo "  5. Live Trading        → /api/v1/candles/ + /api/v1/summary/"
echo ""
echo "🌐 Streamlit Dashboard: http://localhost:8501"
echo "=================================================="
