# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Docker support with multi-stage builds
- Real-time metrics calculation (Volume, Volatility, Sharpe)
- Live price integration from Binance API
- Health check endpoints for monitoring
- Next.js standalone output mode

### Fixed
- NaN validation in market overview page
- Data freshness issues (auto-update integration)
- PYTHONPATH configuration for Docker

### Changed
- Reorganized documentation structure
- Simplified README for better readability
- Moved legacy docs to archive

## [1.0.0] - 2025-12-15

### Added
- Initial release
- AI-powered trading signals with HMM
- Market regime classification (4 states)
- Risk analytics (VaR, Sharpe, Drawdown)
- Technical analysis suite (RSI, MACD, Bollinger Bands)
- Interactive candlestick charts
- FastAPI backend with Parquet storage
- Next.js 15 frontend with React 19
- Real-time Binance API integration
- Comprehensive test suite

---

**Format:** Based on [Keep a Changelog](https://keepachangelog.com/)  
**Versioning:** [Semantic Versioning](https://semver.org/)
