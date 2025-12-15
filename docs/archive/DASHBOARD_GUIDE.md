# 🎯 Bitcoin Intelligence Dashboard - User Guide

## 🚀 Quick Start

### Access the Dashboard
```
http://localhost:8501
```

### System Status Check
```bash
# Check API
curl http://localhost:8000/health

# Check Streamlit
curl http://localhost:8501

# Run validation script
python tests/validate_dashboard.py

# Run integration tests
python tests/integration/test_dashboard_pages.py
```

---

## 📊 Dashboard Pages

### 1. 📊 Market Overview
**Purpose**: Real-time price and volume analysis with technical indicators

**Features**:
- **Tab 1: Candlestick Chart**
  - OHLC price data with volume bars
  - Interactive zoom and pan
  - Configurable chart height

- **Tab 2: Moving Averages** ⭐ NEW
  - Price line with MA20, MA50, MA200
  - MA crossover signals:
    - ✅ Green = Price above MA (bullish)
    - ⚠️ Orange = Price below MA (bearish)
  - Real-time signal interpretation

- **Tab 3: Volume Analysis** ⭐ NEW
  - Volume bars colored by 20-period MA
  - 🟢 Green = Above average volume
  - 🔴 Red = Below average volume
  - Volume ratio alerts (high/normal/low)

**Metrics Displayed**:
- Current price with 24h change
- 24h high/low range
- 24h volume (USD)
- Price statistics (mean, std, min, max, median)
- Volume statistics
- Trend indicators
- Volatility level
- Market insights

**Quick Selectors**: 7D | 30D | 90D

---

### 2. 📈 Technical Analysis
**Purpose**: RSI, MACD, Bollinger Bands analysis with trading signals

**Features**:
- **4 Tabs**: RSI | MACD | Bollinger Bands | Summary
- Enhanced Summary with multi-indicator scoring system
- Overall trading signal (Strong Buy → Strong Sell)
- Individual signal cards for each indicator
- Key insights and trading recommendations
- Download CSV functionality

**Summary Tab Scoring**:
- Score range: -6 to +6
- RSI: ±2 points (oversold/overbought)
- MACD: ±2 points (bullish/bearish crossover)
- BB: ±1 point (price outside bands)
- Signals: Strong Buy (≥4) | Buy (≥2) | Hold | Sell (≤-2) | Strong Sell (≤-4)

**Quick Selectors**: 7D | 30D | 90D

---

### 3. ⚠️ Risk Analysis
**Purpose**: Comprehensive risk metrics for portfolio management

**Key Metrics**:
1. **Value at Risk (VaR 95%)**
   - Expected maximum loss with 95% confidence
   - Color-coded by severity (🔴🟡🟢)

2. **Sharpe Ratio**
   - Risk-adjusted returns
   - Quality rating: Excellent (>2) | Good (>1) | Fair (>0) | Poor (<0)

3. **Volatility**
   - Annualized daily volatility
   - Level indicator: High (>5%) | Medium (2-5%) | Low (<2%)

4. **Max Drawdown**
   - Largest peak-to-trough decline
   - Severity indicator

**Additional Metrics**:
- Sortino Ratio (downside-only risk)
- CVaR (Conditional VaR - average of worst cases)
- Downside Volatility
- Average Drawdown
- Average Recovery Time

**Visualizations**:
- **Drawdown Chart**: Underwater periods
- **Realized Volatility Cone** ⭐ NEW
  - Multi-window analysis: 7D, 14D, 30D, 60D, 90D
  - Gray area: Historical min-max range
  - Blue area: 25-75 percentile (normal range)
  - Blue line: Median volatility
  - Red dashed: Current volatility
  - Automatic alerts for elevated/low volatility

**Risk Assessment**:
- Overall risk level (Low/Medium/High)
- Risk score calculation (0-4 scale)
- Plain language interpretation

**Quick Selectors**: 30D | 90D | 180D

---

### 4. 🎯 Regime Classification
**Purpose**: Market regime detection using GMM and HMM

**Regime Types**:
- 🐂 **Bull**: Uptrend, positive returns, moderate volatility
- 🐻 **Bear**: Downtrend, negative returns, increasing volatility
- 😐 **Neutral**: Sideways, low momentum, low volatility
- ⚡ **High Volatility**: Unstable, high swings, uncertain direction

**Visualizations**:
- **Tab 1: Timeline**
  - Price chart colored by regime
  - Visual regime transitions

- **Tab 2: Probability Evolution** ⭐ NEW
  - 100% stacked area chart
  - All regime probabilities over time
  - Shows model confidence
  - Identifies uncertain periods
  - Interpretation guide included

- **Tab 3: Transition Matrix** ⭐ NEW
  - Heatmap of transition probabilities
  - From regime (rows) → To regime (columns)
  - Diagonal = stability (staying in same regime)
  - Regime stability percentage
  - Color-coded: Red (0%) → Green (100%)

**Statistics**:
- Regime distribution (pie chart & table)
- Regime statistics (count, %, avg return, avg volatility)
- Transition history (last 10 transitions)
- Regime stability metrics

**Trading Implications**:
- 🐂 Bullish → Consider long positions, ride trend
- 🐻 Bearish → Avoid longs, wait for reversal
- ⚡ Volatile → Reduce position sizes, widen stops
- 😐 Neutral → Range trading, wait for breakout

**Quick Selectors**: 30D | 90D | 180D

---

## 🎨 Design Features

### Visual Elements
- Gradient background cards for key metrics
- Emoji indicators (🟢🟡🔴) for quick status
- Consistent color scheme:
  - 🟢 Green: Bullish/Positive
  - 🔴 Red: Bearish/Negative
  - 🔵 Blue: Neutral/Info
  - 🟣 Purple: Special indicators
  - 🟠 Orange: Warnings

### Interactive Elements
- Tab-based navigation for complex views
- Expandable sections for detailed data
- Tooltips and captions for clarity
- Download CSV buttons on all pages
- Quick date range selectors
- Adjustable chart heights
- Hover details on charts

---

## 📊 Data Information

**Symbol**: BTCUSDT  
**Interval**: 1 hour (1h)  
**Date Range**: January 2020 - December 2024  
**Total Records**: 52,049 rows  
**Update Frequency**: On-demand via API

### Data Endpoints
```bash
# Get market data
GET http://localhost:8000/api/v1/market-data/
  ?symbol=BTCUSDT
  &start=2024-01-01
  &end=2024-12-10
  &interval=1h
  &limit=1000

# Get technical indicators
GET http://localhost:8000/api/v1/analysis/indicators
  ?symbol=BTCUSDT
  &start=2024-11-01
  &end=2024-12-10
  &interval=1h

# Get risk metrics
GET http://localhost:8000/api/v1/analysis/risk-metrics
  ?symbol=BTCUSDT
  &start=2024-11-01
  &end=2024-12-10
  &interval=1h

# Get regime classification
GET http://localhost:8000/api/v1/analysis/regimes
  ?symbol=BTCUSDT
  &start=2024-11-01
  &end=2024-12-10
  &interval=1h

# Get investment decision
GET http://localhost:8000/api/v1/analysis/decision
  ?symbol=BTCUSDT
  &start=2024-11-01
  &end=2024-12-10
  &interval=1h
```

---

## 🧪 Testing

### Run All Tests
```bash
# Integration tests (11 tests)
python tests/integration/test_dashboard_pages.py

# Validation script (7 checks)
python tests/validate_dashboard.py
```

### Test Coverage
- ✅ API health check
- ✅ Market data retrieval
- ✅ Technical indicators (RSI, MACD, BB)
- ✅ Risk metrics calculation
- ✅ Regime classification
- ✅ Investment decision engine
- ✅ Data completeness
- ✅ Indicator accuracy
- ✅ Price sanity checks
- ✅ Response time (indicators < 5s)
- ✅ Response time (decision < 10s)

**Current Status**: 11/11 tests passing ✅

---

## 🛠️ Technical Stack

### Backend
- **FastAPI**: REST API server
- **DuckDB**: Analytical database
- **NumPy/Pandas**: Data processing
- **scikit-learn**: Machine learning (GMM, HMM)

### Frontend
- **Streamlit**: Dashboard framework
- **Plotly**: Interactive charts
- **Requests**: API client

### Chart Components
1. `create_candlestick_chart()` - OHLCV candlesticks
2. `create_price_with_ma_chart()` - Price with moving averages ⭐
3. `create_volume_analysis_chart()` - Volume with MA comparison ⭐
4. `create_rsi_chart()` - RSI with overbought/oversold
5. `create_macd_chart()` - MACD with histogram
6. `create_bollinger_bands_chart()` - Price with BB bands
7. `create_drawdown_chart()` - Underwater drawdown
8. `create_volatility_cone_chart()` - Volatility distribution ⭐
9. `create_regime_timeline()` - Price colored by regime
10. `create_regime_transition_matrix()` - Transition heatmap ⭐
11. `create_regime_probability_timeline()` - Probability evolution ⭐

---

## 🚀 Performance

### Response Times
- Market data query: < 1s
- Technical indicators: < 5s
- Risk metrics: < 5s
- Regime classification: < 3s
- Investment decision: < 10s

### Data Loading
- Initial page load: < 3s
- Chart rendering: < 1s
- API calls cached for 5 minutes

---

## 💡 Tips & Best Practices

### General Usage
1. Start with Market Overview to understand current price action
2. Use Technical Analysis for entry/exit signals
3. Check Risk Analysis before position sizing
4. Monitor Regime Classification for market context

### Date Range Selection
- **Short-term (7D)**: Intraday patterns, recent signals
- **Medium-term (30D)**: Trend confirmation, monthly patterns
- **Long-term (90D-180D)**: Regime analysis, volatility studies

### Interpretation Guidelines
1. **Multiple Indicators**: Don't rely on single indicator
2. **Context Matters**: Consider current regime when trading
3. **Risk First**: Always check risk metrics before trading
4. **Volume Confirmation**: Use volume to confirm price moves
5. **Regime Awareness**: Adapt strategy to current market regime

### Common Workflows

**Day Trading**:
1. Market Overview → Check 7D price action
2. Technical Analysis → RSI + MACD signals
3. Risk Analysis → Current volatility
4. Execute with tight stops

**Swing Trading**:
1. Market Overview → Check 30D trend + MAs
2. Regime Classification → Confirm regime
3. Technical Analysis → Entry signals
4. Risk Analysis → Position sizing

**Position Trading**:
1. Regime Classification → 90D regime analysis
2. Market Overview → Long-term MAs
3. Risk Analysis → 180D risk metrics
4. Technical Analysis → Final entry timing

---

## 📝 Changelog

### Latest Enhancement (December 2025)
- ✅ Added 3-tab chart system to Market Overview
- ✅ Added Moving Average analysis (MA20, MA50, MA200)
- ✅ Added Volume Analysis with MA comparison
- ✅ Added Realized Volatility Cone to Risk Analysis
- ✅ Added Regime Probability Evolution chart
- ✅ Added Regime Transition Matrix heatmap
- ✅ Enhanced all pages with gradient cards
- ✅ Updated date ranges to full dataset (2020-2025)
- ✅ Added quick date selectors to all pages
- ✅ Fixed all integration tests (11/11 passing)
- ✅ Created comprehensive validation script

---

## 🎯 Future Enhancements (Roadmap)

### Phase 7: Real-time Features
- [ ] WebSocket integration for live price updates
- [ ] Real-time alerts system (email/Telegram)
- [ ] Streaming data visualization

### Phase 8: Advanced Analytics
- [ ] Portfolio tracking (multi-asset)
- [ ] Correlation analysis
- [ ] Sector rotation indicators

### Phase 9: Backtesting
- [ ] Strategy backtesting engine
- [ ] Performance attribution
- [ ] Monte Carlo simulation

### Phase 10: AI/ML Enhancements
- [ ] Price prediction models
- [ ] Sentiment analysis integration
- [ ] Anomaly detection

---

## 🆘 Troubleshooting

### Dashboard Not Loading
```bash
# Check Streamlit status
ps aux | grep streamlit

# Restart Streamlit
pkill -9 streamlit
cd /path/to/project
nohup streamlit run src/presentation/streamlit_app/app.py --server.headless=true &
```

### API Errors
```bash
# Check API status
curl http://localhost:8000/health

# Restart API
pkill -9 -f uvicorn
cd /path/to/project
nohup uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
```

### Missing Data
```bash
# Download data via API
curl -X POST "http://localhost:8000/api/v1/market-data/download" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol":"BTCUSDT",
    "start":"2020-01-01T00:00:00",
    "end":"2024-12-10T23:59:59",
    "interval":"1h"
  }'
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

---

## 📞 Support

### Documentation
- API Docs: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

### Testing
- Run validation: `python tests/validate_dashboard.py`
- Run tests: `python tests/integration/test_dashboard_pages.py`

---

**Last Updated**: December 10, 2025  
**Version**: 1.0.0  
**Status**: Production Ready ✅
