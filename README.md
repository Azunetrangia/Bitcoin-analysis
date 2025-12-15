# 🪙 Bitcoin Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Real-time Bitcoin analytics platform with AI trading signals, market regime detection, and institutional-grade risk management.**

---

## 🎯 Overview

Professional Bitcoin market intelligence system combining machine learning, real-time data streaming, and advanced quantitative analysis. Built for traders, researchers, and quant developers.

**Live Demo:** [View Dashboard](http://localhost:3000) | **API Docs:** [FastAPI Swagger](http://localhost:8000/docs)

---

## ✨ Key Features

| Feature | Technology | Description |
|---------|-----------|-------------|
| 🤖 **AI Trading Signals** | HMM + KAMA + Technical | Multi-factor composite scoring (-100 to +100) |
| 📊 **Market Regime** | Hidden Markov Model | 4-state classification (Bull/Bear/Sideways/Volatile) |
| ⚠️ **Risk Analytics** | VaR + Sharpe + Drawdown | Institutional-grade risk metrics |
| 📈 **Technical Analysis** | RSI, MACD, Bollinger Bands | Full indicator suite with visualizations |
| 🔴 **Real-time Data** | Binance API | Live price updates every 10 seconds |
| 🐳 **Docker Ready** | Multi-stage builds | Production-optimized containers |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ or Docker
- Node.js 20+ (for frontend)
- 4GB RAM minimum

### 🐳 Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/Azunetrangia/Bitcoin-analysis.git
cd Bitcoin-analysis

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Access
# Frontend: http://localhost:3000
# API: http://localhost:8000/docs
```

### 💻 Local Development

```bash
# Backend
cd Data-analysis-bitcoin
pip install -r requirements.txt
uvicorn src.api.api_server_parquet:app --reload

# Frontend (new terminal)
cd frontend-nextjs
npm install
npm run dev
```

**Full setup guide:** [docs/setup/INSTALLATION.md](docs/setup/INSTALLATION.md)

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Next.js 15 Frontend                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Market    │  │ Technical  │  │    Risk    │            │
│  │  Overview  │  │  Analysis  │  │  Analytics │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
                          ↓ REST API
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Endpoints │  │ ML Models  │  │    Data    │            │
│  │   Router   │  │ HMM + KAMA │  │   Manager  │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│            Parquet Storage + Binance API                     │
│         52K+ candles | 369 days | Real-time feed            │
└─────────────────────────────────────────────────────────────┘
```

**Stack:**
- **Backend:** FastAPI + Pandas + DuckDB + HMMLearn
- **Frontend:** Next.js 15 + React 19 + Recharts + Tailwind
- **Data:** Parquet files (52K+ candles, 369 days)
- **Deployment:** Docker + Docker Compose

---

## 📁 Project Structure

```
Bitcoin-analysis/
├── src/                    # Backend Python source
│   ├── api/               # FastAPI endpoints
│   ├── analysis/          # Trading logic & ML models
│   └── services/          # Data fetching & processing
├── frontend-nextjs/        # Next.js application
│   ├── app/               # Pages & components
│   └── lib/               # API client & utilities
├── data/                   # Parquet data storage
│   └── hot/               # Live trading data
├── docs/                   # Documentation
│   ├── setup/             # Installation guides
│   └── archive/           # Historical docs
├── tests/                  # Test suites
├── docker-compose.yml      # Container orchestration
└── requirements.txt        # Python dependencies
```

---

## 🎓 Documentation

| Document | Description |
|----------|-------------|
| [API Reference](docs/API_GUIDE.md) | Complete API documentation |
| [Docker Guide](DOCKER_QUICKSTART.md) | Container deployment |
| [Architecture](docs/architecture.md) | System design & data flow |

---

## 🔧 Configuration

### Environment Variables

**Backend** (`.env`):
```env
PYTHONPATH=/app
DATA_HOT_PATH=./data/hot
LOG_LEVEL=info
```

**Frontend** (`.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 📈 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/summary/{symbol}` | GET | Market overview & statistics |
| `/api/v1/candles/{symbol}` | GET | Historical OHLCV data |
| `/api/v1/indicators/{symbol}` | GET | Technical indicators (RSI, MACD, etc.) |
| `/api/v1/regimes/{symbol}` | GET | HMM regime classification |
| `/api/v1/risk/{symbol}` | GET | VaR, Sharpe, Drawdown metrics |
| `/api/v1/decisions/{symbol}` | GET | AI trading signals |
| `/api/v1/health` | GET | Service health check |

**Interactive API docs:** `http://localhost:8000/docs`

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test
pytest tests/test_api.py -v
```

---

## 🚢 Deployment

### Production Build

```bash
# Build optimized images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Data Updates

```bash
# Manual update
docker-compose exec backend python src/services/auto_update_data.py

# Automated (cron)
0 */4 * * * cd /path/to/project && docker-compose exec backend python src/services/auto_update_data.py
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## ⚠️ Disclaimer

**For educational and research purposes only.** This software does not provide financial advice. Cryptocurrency trading carries significant risk. Always conduct your own research and consult financial professionals before making investment decisions.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Data Source:** [Binance API](https://binance-docs.github.io/apidocs/)
- **ML Libraries:** scikit-learn, hmmlearn, statsmodels
- **UI Components:** shadcn/ui, Recharts
- **Inspired by:** Quantitative finance research & institutional trading systems

---

## 📞 Contact

**Author:** Azunetrangia  
**GitHub:** [@Azunetrangia](https://github.com/Azunetrangia)  
**Project Link:** [Bitcoin-analysis](https://github.com/Azunetrangia/Bitcoin-analysis)

---

<div align="center">
  
**⭐ Star this repo if you find it useful!**

Made with ❤️ and ☕ by [Azunetrangia](https://github.com/Azunetrangia)

</div>

