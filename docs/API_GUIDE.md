# Bitcoin Market Intelligence API - Complete Guide

## 🚀 Overview

Production-ready REST API for Bitcoin market data analysis. Built with FastAPI, provides real-time market data access, technical indicators, risk metrics, and automated scheduling.

**Base URL:** `http://localhost:8000`  
**Interactive Docs:** http://localhost:8000/docs  
**OpenAPI Schema:** http://localhost:8000/openapi.json

**Features:**
- ✅ Real-time market data from Binance
- ✅ 15+ technical indicators (RSI, MACD, BB, ATR, MAs)
- ✅ 10+ risk metrics (VaR, Sharpe, drawdown, volatility)
- ✅ Automated scheduling and pipelines
- ✅ OpenAPI/Swagger documentation
- ✅ 122 unit tests (57% coverage)

---

## 📦 Quick Start

### Installation

```bash
# Install dependencies
pip install fastapi uvicorn pandas pyarrow pydantic

# Or from requirements
pip install -r requirements.txt
```

### Start Server

```bash
# Development (with auto-reload)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Production (4 workers)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Verify

```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"1.0.0","timestamp":"..."}
```

---

## 📚 API Reference

### 🏥 Health & Info

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-12-10T08:57:31"
}
```

#### `GET /`
API information and endpoint list.

---

### 📈 Market Data Endpoints

#### `GET /api/v1/market-data/`
Query historical OHLCV data.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| symbol | string | BTCUSDT | Trading pair |
| start | datetime | - | Start time (ISO 8601) |
| end | datetime | - | End time (ISO 8601) |
| interval | string | 1h | 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w |
| limit | int | - | Max rows to return |

**Example:**
```bash
curl "http://localhost:8000/api/v1/market-data/?symbol=BTCUSDT&start=2024-11-15T00:00:00&end=2024-11-16T00:00:00&interval=1h&limit=5"
```

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "count": 5,
  "data": [
    {
      "timestamp": "2024-11-15T00:00:00+00:00",
      "open": 90377.89,
      "high": 91461.01,
      "low": 90324.85,
      "close": 91447.98,
      "volume": 3159.43
    }
  ]
}
```

---

#### `GET /api/v1/market-data/latest`
Get most recent candle.

**Example:**
```bash
curl "http://localhost:8000/api/v1/market-data/latest?symbol=BTCUSDT&interval=1h"
```

**Response:**
```json
{
  "timestamp": "2024-11-30T00:00:00Z",
  "open": 97460.0,
  "high": 97463.95,
  "low": 96946.06,
  "close": 96968.06,
  "volume": 713.95
}
```

---

#### `POST /api/v1/market-data/download`
Download historical data from Binance.

**Request Body:**
```json
{
  "symbol": "BTCUSDT",
  "start": "2024-11-01T00:00:00",
  "end": "2024-12-01T00:00:00",
  "interval": "1h"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/market-data/download" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "start": "2024-11-01T00:00:00",
    "end": "2024-12-01T00:00:00",
    "interval": "1h"
  }'
```

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "rows_added": 720,
  "start": "2024-11-01T00:00:00",
  "end": "2024-12-01T00:00:00",
  "message": "Successfully downloaded 720 candles"
}
```

---

#### `POST /api/v1/market-data/update`
Update with latest candles (incremental).

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| symbol | string | BTCUSDT | Trading pair |
| interval | string | 1h | Timeframe |
| limit | int | 2 | Number of recent candles |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/market-data/update?symbol=BTCUSDT&interval=1h&limit=100"
```

---

### 🔬 Analysis Endpoints

#### `GET /api/v1/analysis/indicators`
Calculate technical indicators.

**Indicators Included:**
- **Trend:** SMA(20, 50), EMA(20), MACD
- **Momentum:** RSI(14)
- **Volatility:** Bollinger Bands, ATR(14)

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| symbol | string | BTCUSDT | Trading pair |
| start | datetime | - | Start time |
| end | datetime | - | End time |
| interval | string | 1h | Timeframe |
| limit | int | 100 | Max rows |

**Example:**
```bash
curl "http://localhost:8000/api/v1/analysis/indicators?symbol=BTCUSDT&start=2024-11-01T00:00:00&end=2024-11-30T00:00:00&interval=1h&limit=2"
```

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "count": 2,
  "data": [
    {
      "timestamp": "2024-11-29T23:00:00+00:00",
      "open": 97292.69,
      "high": 97486.27,
      "low": 97111.47,
      "close": 97460.0,
      "volume": 895.59,
      "rsi": 63.62,
      "macd": 431.75,
      "macd_signal": 467.39,
      "macd_histogram": -35.64,
      "bb_upper": 98325.94,
      "bb_middle": 96980.04,
      "bb_lower": 95634.15,
      "bb_bandwidth": 0.0278,
      "atr": 624.79,
      "sma_20": 96980.04,
      "sma_50": 96121.66,
      "ema_20": 96988.28
    }
  ]
}
```

---

#### `GET /api/v1/analysis/risk-metrics`
Calculate comprehensive risk metrics.

**Metrics Included:**
- Max Drawdown
- Volatility (historical, annualized)
- Sharpe Ratio
- Sortino Ratio
- Value at Risk (VaR 95%, 99%)
- Expected Shortfall (ES/CVaR)
- Mean Return

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| symbol | string | BTCUSDT | Trading pair |
| start | datetime | - | Start time |
| end | datetime | - | End time |
| interval | string | 1h | Timeframe |
| confidence_level | float | 0.95 | VaR confidence (0-1) |

**Example:**
```bash
curl "http://localhost:8000/api/v1/analysis/risk-metrics?symbol=BTCUSDT&start=2024-11-01T00:00:00&end=2024-11-30T00:00:00&interval=1h"
```

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "start": "2024-11-01T00:00:00",
  "end": "2024-11-30T00:00:00",
  "metrics": {
    "max_drawdown": -0.0245,
    "volatility": 0.1141,
    "sharpe_ratio": 1.3682,
    "sortino_ratio": 2.1534,
    "var_95": -0.0083,
    "var_99": -0.0142,
    "expected_shortfall_95": -0.0115,
    "expected_shortfall_99": -0.0178,
    "mean_return": 0.0003,
    "timestamp": "2024-11-30T00:00:00+00:00"
  }
}
```

---

#### Individual Metric Endpoints

Get specific metrics without full calculation:

**`GET /api/v1/analysis/volatility`**
```bash
curl "http://localhost:8000/api/v1/analysis/volatility?symbol=BTCUSDT&start=2024-11-01T00:00:00&end=2024-11-30T00:00:00&interval=1h"
# {"volatility": 0.1141}
```

**`GET /api/v1/analysis/sharpe`**
```bash
curl "http://localhost:8000/api/v1/analysis/sharpe?symbol=BTCUSDT&start=2024-11-01T00:00:00&end=2024-11-30T00:00:00&interval=1h"
# {"sharpe_ratio": 1.3682}
```

**`GET /api/v1/analysis/var`**
```bash
curl "http://localhost:8000/api/v1/analysis/var?symbol=BTCUSDT&start=2024-11-01T00:00:00&end=2024-11-30T00:00:00&interval=1h&confidence_level=0.95"
# {"var_95": -0.0083}
```

**`GET /api/v1/analysis/drawdown`**
```bash
curl "http://localhost:8000/api/v1/analysis/drawdown?symbol=BTCUSDT&start=2024-11-01T00:00:00&end=2024-11-30T00:00:00&interval=1h"
# {"max_drawdown": -0.0245}
```

---

### ⏰ Scheduler Endpoints

#### `GET /api/v1/scheduler/status`
Get scheduler status and active jobs.

**Example:**
```bash
curl http://localhost:8000/api/v1/scheduler/status
```

**Response:**
```json
{
  "running": true,
  "jobs_count": 3,
  "timezone": "UTC",
  "jobs": [
    {
      "id": "incremental_update",
      "name": "Incremental Update",
      "next_run": "2025-12-10T09:00:00+00:00",
      "trigger": "cron[hour='*/1']"
    }
  ]
}
```

---

#### `POST /api/v1/scheduler/start`
Start the scheduler.

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/start
```

**Response:**
```json
{
  "message": "Scheduler started successfully",
  "running": true,
  "jobs_count": 0
}
```

---

#### `POST /api/v1/scheduler/stop`
Stop the scheduler.

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/stop
```

---

#### `POST /api/v1/scheduler/pipeline/update`
Run incremental update pipeline.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| symbol | string | BTCUSDT | Trading pair |
| interval | string | 1h | Timeframe |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/scheduler/pipeline/update?symbol=BTCUSDT&interval=1h"
```

---

## ⚙️ Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# API
ENVIRONMENT=development
LOG_LEVEL=INFO

# Storage
STORAGE_PATH=./data/parquet

# Binance API (optional for public data)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_secret
BINANCE_BASE_URL=https://api.binance.com
```

### Settings Class

Modify `src/shared/config/settings.py`:

```python
class Settings(BaseSettings):
    # API Configuration
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Storage
    STORAGE_PATH: str = "./data/parquet"
    
    # Binance
    BINANCE_BASE_URL: str = "https://api.binance.com"
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None
    
    class Config:
        env_file = ".env"
```

---

## 🔒 Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Success |
| 400 | Bad Request | Invalid parameters |
| 404 | Not Found | No data for date range |
| 500 | Internal Server Error | Processing error |
| 502 | Bad Gateway | Binance API error |

### Error Response Format

```json
{
  "error": "Descriptive error message",
  "status_code": 500
}
```

### Common Errors

**404 - No data found:**
```json
{
  "error": "No data found for BTCUSDT 1h in range 2025-12-01 to 2025-12-10",
  "status_code": 404
}
```

**500 - Calculation failed:**
```json
{
  "error": "Insufficient data for MACD (need 26, got 25)",
  "status_code": 500
}
```

**502 - Binance API error:**
```json
{
  "error": "No data downloaded for BTCUSDT 1h",
  "status_code": 502
}
```

---

## 🧪 Testing

### Run Unit Tests

```bash
# All unit tests
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=src --cov-report=html

# Specific test file
pytest tests/unit/test_market_data_service.py -v
```

### API Integration Tests

```bash
# Ensure server is running
uvicorn src.api.main:app --reload &

# Run test script
python scripts/test_api.py
```

### Test Results

```
✅ 122 tests passing
📊 57% code coverage
⏱️ 3.49s runtime
```

---

## 📂 Project Structure

```
src/
├── api/                        # FastAPI application
│   ├── main.py                # App entry point, CORS, middleware
│   ├── dependencies.py        # Dependency injection container
│   ├── models.py              # Pydantic request/response models
│   └── routes/
│       ├── market_data.py     # Market data endpoints
│       ├── analysis.py        # Analysis endpoints
│       └── scheduler.py       # Scheduler endpoints
│
├── application/               # Business logic layer
│   └── services/
│       ├── market_data_service.py      # Market data operations
│       ├── analysis_service.py         # Analysis orchestration
│       ├── scheduler_service.py        # Job scheduling
│       └── pipeline_orchestrator.py    # Pipeline management
│
├── domain/                    # Core domain logic
│   ├── models/               # Domain entities
│   └── services/
│       ├── technical_analysis_service.py    # TA calculations
│       ├── risk_calculator_service.py       # Risk metrics
│       └── regime_classifier_service.py     # Market regimes
│
├── infrastructure/           # External integrations
│   ├── data/
│   │   └── binance_client.py           # Binance API client
│   └── storage/
│       ├── parquet_repository.py       # Data repository
│       └── parquet_manager.py          # Parquet I/O
│
└── shared/                   # Shared utilities
    ├── config/              # Configuration
    ├── exceptions/          # Custom exceptions
    └── utils/              # Helper functions
```

---

## 🚀 Performance Optimization

### Query Optimization

1. **Use specific date ranges:**
   ```bash
   # Good: 1 month range
   start=2024-11-01&end=2024-12-01
   
   # Avoid: Very large ranges
   start=2020-01-01&end=2024-12-01
   ```

2. **Set appropriate limits:**
   ```bash
   # For previews
   limit=10
   
   # For charts
   limit=100
   ```

3. **Use cached intervals:**
   - 1h, 4h, 1d are most cached
   - Minute data is larger

### Data Management

1. **Partition strategy:** Data automatically partitioned by month
2. **Storage:** Parquet format with snappy compression
3. **Cleanup:** Remove old partitions periodically

```bash
# Check storage size
du -sh data/parquet/

# Remove old data
rm -rf data/parquet/btcusdt/1h/2020-*
```

### Scaling Tips

1. **Multiple workers:**
   ```bash
   uvicorn src.api.main:app --workers 4
   ```

2. **Add caching layer:**
   - Redis for frequently accessed queries
   - Cache technical indicators

3. **Load balancing:**
   - Nginx reverse proxy
   - Multiple API instances

---

## 🐛 Troubleshooting

### Server Issues

**Port already in use:**
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn src.api.main:app --port 8001
```

**Import errors:**
```bash
# Set PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Or use absolute imports
python -m uvicorn src.api.main:app
```

### Data Issues

**No data returned:**
1. Check storage path:
   ```bash
   ls -R data/parquet/
   ```

2. Verify date range has data:
   ```bash
   ls data/parquet/btcusdt/1h/
   ```

3. Download data first:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/market-data/download" \
     -H "Content-Type: application/json" \
     -d '{"symbol":"BTCUSDT","start":"2024-11-01T00:00:00","end":"2024-12-01T00:00:00","interval":"1h"}'
   ```

**Calculation errors:**
- Ensure sufficient data (MACD needs 26+ rows)
- Check for gaps in data
- Verify data quality

### API Errors

**500 errors:**
1. Check logs:
   ```bash
   tail -f /tmp/api.log
   ```

2. Enable debug mode:
   ```python
   # main.py
   app = FastAPI(debug=True)
   ```

**Slow responses:**
1. Add query limits
2. Reduce date range
3. Check data volume:
   ```bash
   # Count rows
   python -c "import pyarrow.parquet as pq; print(pq.read_table('data/parquet/btcusdt/1h/2024-11/data.parquet').num_rows)"
   ```

---

## 📈 Future Enhancements

### Phase 6: Authentication & Security
- [ ] API key authentication
- [ ] Rate limiting
- [ ] Request throttling
- [ ] HTTPS/TLS

### Phase 7: Advanced Features
- [ ] WebSocket streaming
- [ ] Real-time alerts
- [ ] Custom indicators
- [ ] Backtesting API

### Phase 8: Infrastructure
- [ ] Redis caching
- [ ] PostgreSQL metadata
- [ ] Docker deployment
- [ ] Kubernetes orchestration

### Phase 9: Monitoring
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Error tracking (Sentry)
- [ ] Performance profiling

---

## 📖 Additional Resources

- **Interactive API Docs:** http://localhost:8000/docs
- **OpenAPI Schema:** http://localhost:8000/openapi.json
- **ReDoc Documentation:** http://localhost:8000/redoc
- **Test Script:** `scripts/test_api.py`

---

## 📝 Changelog

### v1.0.0 (2025-12-10)
- ✅ Complete REST API with 25 endpoints
- ✅ Market data query and download
- ✅ Technical indicators (15+ indicators)
- ✅ Risk metrics (10+ metrics)
- ✅ Scheduler with automated pipelines
- ✅ OpenAPI documentation
- ✅ 122 passing unit tests (57% coverage)
- ✅ Production-ready error handling

---

**Version:** 1.0.0  
**Status:** Production Ready  
**Last Updated:** December 10, 2025  
**Maintainer:** Bitcoin Market Intelligence Team
