# Installation Guide

## Quick Start

### Docker (Recommended)
```bash
docker-compose up -d
```

### Local Development

**Backend:**
```bash
pip install -r requirements.txt
uvicorn src.api.api_server_parquet:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend-nextjs
npm install
npm run dev
```

## Detailed Setup

See [FRONTEND_SETUP.md](../../FRONTEND_SETUP.md) for complete frontend installation.

See [DOCKER_QUICKSTART.md](../../DOCKER_QUICKSTART.md) for Docker deployment.
