# 🪙 Bitcoin Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.13.5-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-15.5.7-black.svg)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.2.0-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A production-ready, real-time Bitcoin analytics platform featuring **AI-Powered Trading Signals**, **Market Regime Classification (HMM)**, **Risk Management (VaR)**, and **Live Data Streaming** from Binance API with institutional-grade quantitative analysis.

## 🎯 Project Overview

A comprehensive Bitcoin market intelligence system combining **machine learning**, **real-time data streaming**, and **advanced risk analytics** to provide actionable trading insights. Built with modern web technologies and production-grade architecture.

### ✨ Core Features

#### 🤖 AI-Powered Trading Signals
- **Multi-Factor Analysis**: HMM Regime + KAMA Indicator + Technical Signals + On-chain Metrics
- **Composite Scoring**: Weighted signal aggregation (-100 to +100 scale)
- **Confidence Levels**: Low/Medium/High confidence classification
- **Real-time Updates**: Live BTC price from Binance API (10s polling)
- **Signal Breakdown**: Contributing factors with individual weights

#### 🎯 Market Regime Classification (HMM)
- **Hidden Markov Model**: 4-state probabilistic regime detection
- **States**: Bull, Bear, Sideways, High Volatility
- **High Accuracy**: 90%+ probability detection in trending markets
- **Confidence Scoring**: Algorithm certainty measurement
- **Historical Analysis**: Regime distribution and timeline visualization

#### ⚠️ Risk Management System
- **Value at Risk (VaR)**: 95% and 99% confidence levels
- **Sharpe Ratio**: Risk-adjusted returns analysis
- **Maximum Drawdown**: Peak-to-trough loss calculation
- **Volatility Metrics**: Daily annualized volatility
- **Historical Tracking**: Returns, drawdown, cumulative performance

#### 📊 Technical Analysis Suite
- **RSI (14-period)**: Overbought/Oversold detection
- **MACD**: Trend momentum with signal line crossovers
- **Bollinger Bands**: Dynamic support/resistance levels
- **KAMA Indicator**: Adaptive moving average for trend confirmation
- **Moving Averages**: MA20, MA50, MA200 with golden/death cross detection

#### 📈 Interactive Data Visualization
- **Custom Candlestick Charts**: OHLC rendering with volume analysis
- **Multi-timeframe Support**: 7D, 30D, 90D, 180D, 1Y views
- **Synchronized Charts**: Price, indicators, and volume alignment
- **Real-time Updates**: Live data refresh without page reload
- **Responsive Design**: Mobile-first, dark theme UI

#### 🚀 Performance & Architecture
- **No Database Required**: Parquet-based storage (52K+ hourly candles)
- **In-Memory Caching**: Sub-100ms API response times
- **Live Data Integration**: Binance Futures API for real-time prices
- **Scalable Backend**: FastAPI with async/await support
- **Modern Frontend**: Next.js 15 App Router + React 19

### What This Project Does

✅ Analyze historical Bitcoin price patterns  
✅ Calculate technical indicators in real-time  
✅ Visualize market regimes and risk metrics  
✅ Provide investment decision recommendations  
✅ Educational tool for learning quantitative finance  

### What This Project DOES NOT Do

❌ Predict future Bitcoin prices (scientifically unreliable)  
❌ Execute automated trading (no API keys, no orders)  
❌ Provide financial advice (educational purposes only)  
❌ Guarantee trading profits (high-risk market)  

## 🏗️ Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 15)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Market     │  │  Technical   │  │     Risk     │      │
│  │   Overview   │  │   Analysis   │  │   Analysis   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────────────────────────────────────────┐       │
│  │         Candlestick Chart Component              │       │
│  │  (Custom Recharts with OHLC + Volume)           │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                            ↓ REST API
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  /candles    │  │ /indicators  │  │   /regimes   │      │
│  │  /summary    │  │    /risk     │  │  /decisions  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              DATA LAYER (Parquet Files)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  data/hot/BTCUSDT_1h.parquet                         │   │
│  │  - 52,068 hourly candles (~6 years)                  │   │
│  │  - Columnar storage (fast filtering)                 │   │
│  │  - In-memory caching for performance                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

**Frontend:**
- Next.js 15.5.7 (React framework)
- React 19.2.0 (UI library)
- TypeScript (type safety)
- Recharts (charting library)
- shadcn/ui (component library)
- Tailwind CSS (styling)

**Backend:**
- FastAPI (Python web framework)
- Pandas + NumPy (data processing)
- Uvicorn (ASGI server)

**Data:**
- Parquet files (Apache Arrow columnar format)
- No database required (file-based)

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Git**

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Azunetrangia/Bitcoin-analysis.git
cd Bitcoin-analysis
```

2. **Backend Setup**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -r requirements.txt
```

3. **Frontend Setup**
```bash
cd frontend-nextjs
npm install
```

4. **Data Setup**
The repository includes sample data in `data/hot/BTCUSDT_1h.parquet`. For fresh data:
```bash
python download_historical_data.py
```

### Running the Application

**Terminal 1 - Start Backend:**
```bash
cd Data-analysis-bitcoin
python -m uvicorn src.api.api_server_parquet:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend-nextjs
npm run dev
```

**Access the app:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📊 Dashboard Pages

### 🏠 Bitcoin Overview Dashboard (`/bitcoin`)
**Main Hub for Real-time Market Intelligence**

- **Trading Signals Component** (NEW):
  - Signal Badge: BUY/SELL/HOLD with confidence level
  - Composite Score: Multi-factor weighted analysis (-100 to +100)
  - Current Price: Live BTC/USDT from Binance
  - Market Regime: HMM classification (Bull/Bear/Sideways/High Vol)
  - KAMA Indicator: Adaptive moving average with distance %
  - Signal Breakdown: 4 contributing factors with individual weights

- **Quick Stats**: 
  - Current Price (live 10s updates)
  - 24h Volume
  - Volatility (elevated/normal)
  - Sharpe Ratio (risk-adjusted returns)

- **Navigation Cards**: Quick links to detailed analysis pages

### 📈 Market Overview (`/bitcoin/market`)
**Deep-Dive Price Analysis**

- **OHLC Candlestick Chart**: Custom Recharts implementation
  - Green/Red candles (close vs open)
  - Proper body/wick rendering
  - Volume bars with MA coloring
  - OHLC legend display
  
- **Moving Averages**: MA20, MA50, MA200 overlay
- **Timeframe Selector**: 7D/30D/90D/180D/1Y
- **Market Summary**: High, Low, 24h Change, Volume

### 🔧 Technical Analysis (`/bitcoin/technical`)
**Multi-Indicator Dashboard**

- **RSI Chart**: 14-period with overbought/oversold zones
- **MACD Chart**: MACD line, Signal line, Histogram
- **Bollinger Bands**: Upper/Middle/Lower bands with price
- **Indicator Cards**: Current values and signals
- **Synchronized X-axis**: All charts aligned by timestamp

### ⚠️ Risk Analysis (`/bitcoin/risk`)
**Portfolio Risk Metrics**

- **VaR Analysis**: 95% and 99% confidence levels
- **Sharpe Ratio**: Risk-adjusted performance measurement
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Volatility**: Daily annualized standard deviation
- **Historical Charts**:
  - Daily Returns distribution
  - Drawdown timeline
  - Cumulative Returns progression

### 🎯 Regime Detection (`/bitcoin/regime`)
**Market State Classification**

- **Current Regime Card**: Bull/Bear/Sideways/High Volatility
- **Regime Distribution**: Pie chart showing historical percentages
- **Timeline Visualization**: Scatter plot of regime changes over time
- **Price & Volatility**: Correlation analysis with dual Y-axis

### 🧭 Navigation System
- **Breadcrumb Component**: Dashboard → Current Page navigation
- **Clickable Header**: "BITCOIN INTELLIGENCE" returns to dashboard
- **Consistent Layout**: Shared sidebar and navigation across all pages

## � API Endpoints

### Trading Signals & Analysis

| Endpoint | Method | Description | Update Frequency |
|----------|--------|-------------|------------------|
| `/api/v1/signals/comprehensive` | GET | **Multi-factor trading signals** (HMM + KAMA + Technical + On-chain) | Real-time |
| `/api/v1/signals/onchain` | GET | On-chain metrics (funding rates, open interest, network stats) | 5 min cache |
| `/api/v1/analysis/indicators` | GET | Technical indicators (RSI, MACD, BB, MA) | Real-time |
| `/api/v1/analysis/regimes` | GET | HMM market regime classification (4 states) | Real-time |
| `/api/v1/analysis/risk` | GET | Risk metrics (VaR 95%/99%, Sharpe, Drawdown) | Real-time |

### Market Data

| Endpoint | Method | Description | Update Frequency |
|----------|--------|-------------|------------------|
| `/api/v1/candles/{symbol}` | GET | Raw OHLC candlestick data with volume | Historical |
| `/api/v1/summary/{symbol}` | GET | Quick market summary (24h stats) | Real-time |
| `/api/v1/decisions/{symbol}` | GET | Investment recommendation (Buy/Sell/Hold) | Real-time |

### Live Data Integration

**Price Data Source**: Binance Futures API
- Endpoint: `https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT`
- Update: Every 10 seconds (frontend polling)
- Fallback: Parquet historical data if API unavailable

### Example Requests

**Get Comprehensive Trading Signals:**
```bash
curl "http://localhost:8000/api/v1/signals/comprehensive?symbol=BTCUSDT&interval=1h"
```

**Response:**
```json
{
  "timestamp": "2025-12-12T10:30:00Z",
  "current_price": 92244.42,
  "recommendation": "BUY",
  "confidence": "Medium",
  "composite_score": 40,
  "regime": {
    "regime": "Bull",
    "probability": 0.901,
    "confidence": "high"
  },
  "kama": {
    "signal": "BULLISH",
    "value": 91600,
    "distance_pct": 0.78
  },
  "factors": [
    {"name": "Regime", "signal": "Bull (High Confidence)", "weight": 30},
    {"name": "KAMA", "signal": "Bullish Trend", "weight": 15},
    {"name": "Funding", "signal": "Neutral (Healthy)", "weight": 5},
    {"name": "Market Cap", "signal": "Overvalued", "weight": -10}
  ]
}
```

**Get Technical Indicators:**
```bash
curl "http://localhost:8000/api/v1/analysis/indicators?symbol=BTCUSDT&interval=1h&limit=100"
```

**Get Risk Metrics:**
```bash
curl "http://localhost:8000/api/v1/analysis/risk?symbol=BTCUSDT&interval=1h&days=30"
```

## 🧪 Technical Implementation

### Trading Signal Algorithm

**Multi-Factor Composite Scoring (-100 to +100):**

```python
# 1. HMM Regime Classification (Weight: -30 to +30)
if regime == "Bull" and confidence == "high":
    score += 30
elif regime == "Bear" and confidence == "high":
    score -= 30
elif regime == "Sideways":
    score += 0  # neutral

# 2. KAMA Indicator (Weight: -15 to +15)
if kama_signal == "BULLISH" and distance > 0:
    score += 15
elif kama_signal == "BEARISH" and distance < 0:
    score -= 15

# 3. Funding Rate (Weight: -10 to +10)
if funding_rate > 0.02:
    score -= 10  # overheated long positions
elif funding_rate < -0.02:
    score += 10  # strong short positions

# 4. Market Cap Valuation (Weight: -10 to +10)
if market_cap_signal == "Undervalued":
    score += 10
elif market_cap_signal == "Overvalued":
    score -= 10

# Final Recommendation
if score > 30: return "BUY"
elif score < -30: return "SELL"
else: return "HOLD"

# Confidence Level
if abs(score) > 60: confidence = "High"
elif abs(score) > 30: confidence = "Medium"
else: confidence = "Low"
```

### HMM Regime Classification

**Hidden Markov Model with 4 States:**

```python
from hmmlearn.hmm import GaussianHMM

# Feature Engineering
features = ['returns', 'volatility', 'volume']
X = df[features].values

# Model Training
model = GaussianHMM(n_components=4, covariance_type="full", n_iter=1000)
model.fit(X)

# State Prediction
hidden_states = model.predict(X)
probabilities = model.predict_proba(X)

# State Labeling Logic
for state in range(4):
    avg_return = returns[hidden_states == state].mean()
    avg_volatility = volatility[hidden_states == state].mean()
    
    if avg_volatility > volatility.quantile(0.75):
        label = "High Volatility"
    elif avg_return > 0:
        label = "Bull"
    elif avg_return < 0:
        label = "Bear"
    else:
        label = "Sideways"
```

### KAMA (Kaufman Adaptive Moving Average)

**Adaptive indicator that adjusts to market conditions:**

```python
def calculate_kama(prices, n=10, fast=2, slow=30):
    # Efficiency Ratio
    change = abs(prices - prices.shift(n))
    volatility = (prices - prices.shift(1)).abs().rolling(n).sum()
    er = change / volatility
    
    # Smoothing Constant
    fast_sc = 2/(fast + 1)
    slow_sc = 2/(slow + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
    
    # KAMA Calculation
    kama = prices.copy()
    for i in range(n, len(prices)):
        kama.iloc[i] = kama.iloc[i-1] + sc.iloc[i] * (prices.iloc[i] - kama.iloc[i-1])
    
    return kama
```

**Signal Generation:**
- BULLISH: Price > KAMA and distance > 0.5%
- BEARISH: Price < KAMA and distance < -0.5%
- NEUTRAL: |distance| < 0.5%

### Technical Indicators

**RSI (Relative Strength Index):**
- Formula: `RSI = 100 - (100 / (1 + RS))` where `RS = Avg Gain / Avg Loss`
- Period: 14
- Overbought: RSI > 70
- Oversold: RSI < 30

**MACD (Moving Average Convergence Divergence):**
- MACD Line: EMA(12) - EMA(26)
- Signal Line: EMA(9) of MACD
- Histogram: MACD - Signal
- Bullish Crossover: MACD crosses above Signal

**Bollinger Bands:**
- Middle Band: 20-period SMA
- Upper Band: Middle + (2 × StdDev)
- Lower Band: Middle - (2 × StdDev)
- Squeeze: Bands narrowing (low volatility)

### Risk Metrics

**Value at Risk (VaR):**
```python
returns = df['close'].pct_change()
var_95 = returns.quantile(0.05)  # 5th percentile
var_99 = returns.quantile(0.01)  # 1st percentile

# Interpretation: 95% confidence we won't lose more than VaR% tomorrow
```

**Sharpe Ratio:**
```python
mean_return = returns.mean()
std_return = returns.std()
sharpe_ratio = (mean_return / std_return) * sqrt(252)  # Annualized

# Sharpe > 1: Good, > 2: Excellent, > 3: Outstanding
```

**Maximum Drawdown:**
```python
cumulative = (1 + returns).cumprod()
running_max = cumulative.cummax()
drawdown = (cumulative - running_max) / running_max
max_drawdown = drawdown.min()
```

## 📚 Project Structure

```
Data-analysis-bitcoin/
├── frontend-nextjs/              # Next.js frontend
│   ├── app/
│   │   └── bitcoin/
│   │       ├── market/          # Market Overview page
│   │       ├── technical/       # Technical Analysis page
│   │       ├── risk/            # Risk Analysis page
│   │       └── regime/          # Regime Classification page
│   ├── components/
│   │   ├── charts/
│   │   │   └── CandlestickChart.tsx  # Custom candlestick component
│   │   ├── dashboard/           # Layout components
│   │   └── ui/                  # shadcn/ui components
│   └── lib/
│       └── bitcoin-api.ts       # API client
│
├── src/
│   ├── api/
│   │   └── api_server_parquet.py    # FastAPI server (595 lines)
│   ├── domain/                  # Business logic models
│   ├── infrastructure/          # Data access layer
│   └── shared/                  # Utilities, config
│
├── data/
│   └── hot/
│       └── BTCUSDT_1h.parquet   # Market data (52K candles)
│
├── tests/                       # Test files
├── scripts/                     # Automation scripts
├── docs/                        # Documentation
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🎓 Key Technical Decisions

### 1. Why Parquet Instead of Database?
- **Performance**: Columnar storage → fast filtering by timestamp
- **Simplicity**: No database setup, just file reads
- **Size**: Built-in compression (52K rows = ~10MB)
- **Portability**: Easy to backup, version, and share

### 2. Why Custom Candlestick Chart?
- **Tried Libraries**: lightweight-charts (API issues), react-financial-charts (React 19 incompatibility)
- **Solution**: Custom Recharts shape component with SVG rendering
- **Features**: Proper body/wick, green/red coloring, volume bars, OHLC legend

### 3. Performance Optimizations
- **In-memory caching**: Parquet files cached in Python dict (sub-100ms reads)
- **Scatter downsampling**: 2160 points → 500 points (5x faster rendering)
- **Animation disabled**: `isAnimationActive={false}` on all Recharts
- **Auto Y-axis**: `domain={['auto', 'auto']}` prevents scaling bugs
- **Dynamic X-intervals**: Show ~8 labels regardless of data size
- **API response caching**: On-chain metrics cached for 5 minutes

### 5. UI/UX Design System

**Component Hierarchy:**
```typescript
// DashboardStat component pattern (reference template)
<Card className="relative overflow-hidden">
  <CardHeader className="pb-2">
    <CardTitle className="flex items-center gap-2 text-sm">
      <Bullet /> {/* rounded-[1.5px] bg-primary size-2 */}
      {label}
    </CardTitle>
    <Icon className="size-3.5" />
  </CardHeader>
  <CardContent className="bg-accent flex-1 pt-2 pb-3">
    {/* Content with tight spacing */}
  </CardContent>
</Card>
```

**Design Principles:**
- **Bullet Component**: 2px colored square for visual consistency
- **Icon Size**: 3.5 (14px) for headers
- **Spacing**: Compact (gap-1.5, space-y-1.5, pb-2)
- **Badge Size**: text-sm (14px) for most badges
- **Font Hierarchy**: text-xs (labels), text-sm (values), text-lg (emphasis)
- **Colors**: Green (#22c55e) for bullish, Red (#ef4444) for bearish, Blue (#3b82f6) for info
- **Background**: bg-accent for content areas
- **Hover Effects**: Simple hover:bg-accent/50 transitions

### 6. Trading Signals Component Evolution

**Iteration History:**
- **Version 1**: Original simple 3-column layout
- **Version 2**: Over-designed with 4xl badges, gradients, animations ❌
- **Version 3**: Minimal design matching site pattern ✅

**Final Design (Version 3):**
- Compact card sizes (pb-2, pt-2 pb-3)
- Small badges (text-sm px-3 py-0.5)
- Tight spacing (gap-1.5, space-y-1.5)
- Flex justify-between for metrics
- Consistent with DashboardStat template
- 4-column grid on large screens

### 7. Risk Metrics

**Value at Risk (VaR)**:
- VaR 95% = 5th percentile of returns
- Interpretation: Maximum expected loss with 95% confidence

**Sharpe Ratio**:
- Formula: `(Mean Return / Std Dev) × √(periods_per_year)`
- Sharpe > 1: Good risk-adjusted returns
- Sharpe > 2: Excellent

**Maximum Drawdown**:
- Largest peak-to-trough decline
- Shows worst-case loss scenario

## � Project Status & Roadmap

### ✅ Completed Features (Phase 1 & 2)

**Phase 1: Core Infrastructure** (100% Complete)
- ✅ FastAPI backend with 8+ endpoints
- ✅ Parquet-based data storage (52K+ hourly candles)
- ✅ Next.js 15 frontend with React 19
- ✅ Custom candlestick chart component
- ✅ Technical indicators (RSI, MACD, BB, MA)
- ✅ Risk metrics (VaR, Sharpe, Drawdown)
- ✅ Basic regime classification

**Phase 2: Advanced Analytics** (100% Complete)
- ✅ Live data integration (Binance API)
- ✅ HMM regime classification with 4 states
- ✅ KAMA adaptive indicator
- ✅ Multi-factor trading signals
- ✅ Composite scoring algorithm
- ✅ Trading Signals dashboard component
- ✅ On-chain metrics (funding rates, open interest)
- ✅ Navigation system (breadcrumbs + clickable header)
- ✅ Page structure refactoring (5 pages)
- ✅ UI/UX improvements (compact design, consistent styling)

### 🔄 In Progress (Phase 3)

**Performance Optimization:**
- ⏳ API caching (Redis or in-memory)
- ⏳ On-chain endpoint optimization (currently >10s)
- ⏳ WebSocket for real-time price updates

**Advanced Risk Models:**
- ⏳ Cornish-Fisher VaR (fat-tail distribution)
- ⏳ Expected Shortfall (CVaR)
- ⏳ Rolling VaR windows

### 📋 Planned Features (Phase 3)

**Backtesting Framework:**
- Strategy testing engine
- Order simulator with slippage/fees
- Performance metrics & reports
- Monte Carlo simulation

**Alert System:**
- Price threshold notifications
- Regime change alerts
- Risk level warnings
- Email/Telegram integration

**Multi-Symbol Support:**
- ETH, SOL, BNB, and other major coins
- Portfolio aggregation
- Correlation analysis

**Advanced Visualization:**
- Heatmaps for correlation
- Volume profile analysis
- Order flow imbalance
- Funding rate history

### ⚠️ Known Limitations

**Current Constraints:**
- Single symbol (BTCUSDT only)
- 1-hour interval only
- No backtesting capability
- No alert notifications
- No order execution
- Frontend polling (not WebSocket)

**Performance Notes:**
- On-chain endpoint: ~10s response (needs caching)
- Historical data: Dec 2018 - Dec 2024 (6 years)
- Memory usage: ~500MB (backend with cached data)

### 🐛 Bug Fixes Log

**December 2025:**
- ✅ Fixed price discrepancy (backend $92k vs frontend $45k)
- ✅ Implemented live price fetching from Binance
- ✅ Fixed duplicate page content (/bitcoin vs /bitcoin/market)
- ✅ Added breadcrumb navigation system
- ✅ Fixed Trading Signals UI (3 design iterations)
- ✅ Matched design system with DashboardStat components
- ✅ Reduced component sizes for better visual hierarchy
- ✅ Fixed Market Regime confidence badge color
- ✅ Improved Signal card layout alignment

**November 2025:**
- ✅ Y-axis scaling bug (709k-35k range)
- ✅ NaN display in descriptions
- ✅ Moving average lines not rendering
- ✅ Scatter plot performance (2160 points lag)
- ✅ Candlestick library incompatibility (React 19)

## 🔒 Security Notes

**For Production:**
- [ ] Restrict CORS origins (currently allows all)
- [ ] Add rate limiting (e.g., 100 requests/minute)
- [ ] Enable HTTPS with reverse proxy
- [ ] Add API authentication
- [ ] Implement input sanitization

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- **Binance** - Free historical data API
- **Recharts** - React charting library
- **shadcn/ui** - Beautiful component library
- **FastAPI** - Modern Python web framework
- **Next.js Team** - Amazing React framework

## ⚠️ Disclaimer

This project is for **educational and research purposes only**. It is NOT financial advice. 

**Important:**
- Cryptocurrency trading involves substantial risk of loss
- Past performance does not guarantee future results
- Always do your own research (DYOR)
- Never invest more than you can afford to lose
- Consult a licensed financial advisor before trading

---

**Built with ❤️ using Clean Architecture & Modern Web Technologies**

**Author**: Azunetrangia  
**Year**: 2025  
**Tech Stack**: Next.js 15 · React 19 · FastAPI · Python · TypeScript

