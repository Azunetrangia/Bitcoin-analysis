# 🪙 Bitcoin Market Intelligence & Risk Management Platform

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-15.5-black.svg)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A modern, production-grade analytics platform for Bitcoin market analysis, focusing on **Market Regime Classification** and **Risk Management** with real-time technical indicators and interactive candlestick charts.

## 🎯 Project Overview

This platform provides institutional-grade quantitative analysis for cryptocurrency markets, built with Clean Architecture principles and modern web technologies (Next.js 15 + React 19 + FastAPI).

### ✨ Key Features

- 📊 **Interactive Candlestick Charts** - Custom-built with Recharts, showing OHLC data with volume analysis
- 📈 **Technical Indicators** - RSI, MACD, Bollinger Bands, Moving Averages (20/50/200)
- ⚠️ **Risk Analytics** - Value at Risk (95%/99%), Sharpe Ratio, Maximum Drawdown, Volatility
- 🎯 **Market Regime Classification** - Automatic detection of Bullish/Bearish/Sideways/High Volatility periods
- 🚀 **High Performance** - Handles 6+ years of hourly data (52K+ candles) with optimized rendering
- 💾 **No Database Required** - Uses Parquet files for fast columnar data access
- 🌙 **Modern UI** - Dark theme dashboard with responsive design using shadcn/ui

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

## 📊 Features & Screenshots

### 1. Market Overview
- **Real-time OHLC Candlestick Chart** with custom body/wick rendering
- **Volume Analysis** with moving average coloring
- **24h Metrics**: Price, Volume, High, Low, Volatility
- **Moving Averages**: MA20, MA50, MA200 with color-coded lines
- **Date Range Selection**: 7D, 30D, 90D, or custom range

### 2. Technical Analysis
- **RSI (14-period)**: Overbought/Oversold detection
- **MACD**: Trend momentum indicator with signal line
- **Bollinger Bands**: Volatility-based support/resistance
- **Price + Indicators**: Synchronized multi-chart view

### 3. Risk Analysis
- **Value at Risk (VaR)**: 95% and 99% confidence levels
- **Sharpe Ratio**: Risk-adjusted return performance
- **Maximum Drawdown**: Worst peak-to-trough decline
- **Volatility**: Annualized price fluctuation
- **Historical Charts**: Returns, Drawdown, Cumulative Returns

### 4. Regime Classification
- **Current Regime**: Bullish, Bearish, Sideways, High Volatility
- **Regime Distribution**: Pie chart with percentages
- **Timeline Visualization**: Scatter plot showing regime changes
- **Price + Volatility**: Correlation analysis

## 📈 API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/candles/{symbol}` | GET | Raw OHLC candlestick data |
| `/api/v1/analysis/indicators` | GET | Technical indicators (RSI, MACD, BB, MA) |
| `/api/v1/analysis/regimes` | GET | Market regime classification |
| `/api/v1/analysis/risk` | GET | Risk metrics (VaR, Sharpe, Drawdown) |
| `/api/v1/decisions/{symbol}` | GET | Investment recommendation (Buy/Sell/Hold) |
| `/api/v1/summary/{symbol}` | GET | Quick market summary |

### Example Request

```bash
curl "http://localhost:8000/api/v1/analysis/indicators?symbol=BTCUSDT&interval=1h&start=2025-11-11T00:00:00Z&end=2025-12-11T00:00:00Z&limit=720"
```

## 🧪 Technical Indicators

### Moving Averages
- **SMA (Simple Moving Average)**: Arithmetic mean over N periods
- **EMA (Exponential Moving Average)**: Weighted average favoring recent prices

### RSI (Relative Strength Index)
- Range: 0-100
- Overbought: RSI > 70
- Oversold: RSI < 30
- Formula: `RSI = 100 - (100 / (1 + RS))` where `RS = Avg Gain / Avg Loss`

### MACD (Moving Average Convergence Divergence)
- MACD Line: EMA(12) - EMA(26)
- Signal Line: EMA(9) of MACD Line
- Histogram: MACD Line - Signal Line

### Bollinger Bands
- Middle Band: 20-period SMA
- Upper Band: Middle + (2 × StdDev)
- Lower Band: Middle - (2 × StdDev)

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
- **In-memory caching**: Loaded parquet files cached in Python dict
- **Scatter downsampling**: 2160 points → 500 points (5x faster)
- **Animation disabled**: isAnimationActive={false} on all charts
- **Auto Y-axis**: domain={['auto', 'auto']} prevents scaling bugs
- **Dynamic X-intervals**: Show ~8 labels regardless of data size

### 4. Regime Classification Logic
```python
IF volatility > 75th_percentile:
    regime = "High Volatility"
ELIF close > SMA20 AND returns > 0:
    regime = "Bullish"
ELIF close < SMA20 AND returns < 0:
    regime = "Bearish"
ELSE:
    regime = "Sideways"
```

### 5. Risk Metrics

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

## 🐛 Known Issues & Limitations

### Current Limitations
- ⚠️ **Single Symbol**: Only BTCUSDT supported
- ⚠️ **Static Data**: No real-time updates (manual refresh)
- ⚠️ **Single Interval**: Primarily 1-hour data
- ⚠️ **No Backtesting**: Cannot test trading strategies
- ⚠️ **No Alerts**: No price/regime notifications

### Fixed Issues
✅ Y-axis scaling bug (709k-35k range)  
✅ NaN display ("NaNNaNNaN" in descriptions)  
✅ MA lines not showing (first element check)  
✅ Scatter plot lag (90D view with 2160 points)  
✅ Candlestick rendering (lightweight-charts incompatibility)  

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

