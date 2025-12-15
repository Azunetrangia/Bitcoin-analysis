# Docker Deployment Roadmap
## Bitcoin Intelligence Platform - Containerization Plan

**Target**: Production-ready Docker setup on Linux  
**Current State**: Development (manual processes, local ports)  
**Goal State**: Fully containerized, orchestrated, reproducible deployment

---

## 📋 Phase 1: Project Audit & Preparation (1-2 hours)

### 1.1 Environment Analysis
- [x] Backend: FastAPI Python app (port 8000)
- [x] Frontend: Next.js 15 app (port 3000)
- [x] Data: Parquet files in `data/hot/` (53KB-27KB)
- [x] Dependencies: `requirements.txt`, `package.json`
- [ ] Environment variables audit (.env files)
- [ ] External dependencies check (Binance API, Supabase, R2)

### 1.2 Data Strategy Decision
**Options:**
1. **Volume Mount** (Recommended for Dev): Mount local `data/` into container
2. **Named Volume**: Docker-managed persistent storage
3. **S3/R2 Only**: No local data, fetch on-demand

**Recommendation**: Hybrid approach
- Development: Volume mount for fast iteration
- Production: Named volumes + R2 backup

### 1.3 Port Mapping Plan
```
Host        Container       Service
8000    ->  8000            Backend API
3000    ->  3000            Frontend (Dev)
80      ->  3000            Frontend (Prod)
```

---

## 🐳 Phase 2: Backend Dockerization (2-3 hours)

### 2.1 Create Backend Dockerfile
**Location**: `/backend.Dockerfile`

**Requirements**:
- Base image: `python:3.11-slim` (lightweight)
- Install system dependencies (gcc for pandas, numpy)
- Copy requirements.txt → pip install
- Copy source code → `/app/src`
- Set PYTHONPATH
- Health check endpoint
- Non-root user for security

**Key Decisions**:
- Multi-stage build? **YES** (reduce image size ~500MB → ~200MB)
- Pip cache? **YES** (speed up rebuilds)
- Virtual environment? **NO** (container is already isolated)

### 2.2 Backend Environment Variables
**Required**:
```env
# API Server
PORT=8000
HOST=0.0.0.0
PYTHONPATH=/app

# Data Paths
DATA_HOT_PATH=/app/data/hot
DATA_RAW_PATH=/app/data/raw

# External Services (optional)
SUPABASE_URL=
SUPABASE_KEY=
R2_ENDPOINT=
R2_ACCESS_KEY=
R2_SECRET_KEY=
```

### 2.3 Backend Optimization
- [ ] Add `.dockerignore` (exclude `__pycache__`, `.git`, `tests/`)
- [ ] Separate dev/prod requirements
- [ ] Add gunicorn for production (instead of uvicorn dev mode)
- [ ] Configure logging to stdout (Docker best practice)

---

## 🎨 Phase 3: Frontend Dockerization (2-3 hours)

### 3.1 Create Frontend Dockerfile
**Location**: `/frontend.Dockerfile`

**Requirements**:
- Base image: `node:20-alpine` (smallest)
- Copy package files → npm install
- Copy source → `/app`
- Build Next.js → `.next/` directory
- Production server: `npm start`

**Multi-stage Build**:
```dockerfile
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./
RUN npm install next
CMD ["npm", "start"]
```

**Size Reduction**: ~1.2GB → ~150MB

### 3.2 Frontend Environment Variables
```env
NEXT_PUBLIC_API_URL=http://backend:8000/api/v1
NODE_ENV=production
```

### 3.3 Frontend Optimization
- [ ] Add `.dockerignore` (exclude `node_modules/`, `.next/`)
- [ ] Enable Next.js standalone mode (smaller bundle)
- [ ] Configure output: 'standalone' in next.config.js

---

## 🎭 Phase 4: Docker Compose Orchestration (1-2 hours)

### 4.1 Create docker-compose.yml
**Location**: `/docker-compose.yml`

**Services**:
```yaml
version: '3.9'

services:
  backend:
    build:
      context: .
      dockerfile: backend.Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - PYTHONPATH=/app
      - DATA_HOT_PATH=/app/data/hot
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend-nextjs
      dockerfile: ../frontend.Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000/api/v1
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

volumes:
  data:
  logs:

networks:
  default:
    name: bitcoin-platform
```

### 4.2 Compose Commands
```bash
# Development
docker-compose up                    # Start all services
docker-compose up -d                 # Detached mode
docker-compose logs -f backend       # Follow backend logs
docker-compose restart frontend      # Restart service

# Production
docker-compose -f docker-compose.prod.yml up -d

# Management
docker-compose ps                    # List services
docker-compose exec backend bash     # Shell into container
docker-compose down -v               # Stop and remove volumes
```

---

## 🔧 Phase 5: Development Workflow (1 hour)

### 5.1 Hot Reload Setup
**Backend**: Mount source as volume
```yaml
volumes:
  - ./src:/app/src:ro  # Read-only for safety
```
Uvicorn's `--reload` flag works automatically

**Frontend**: Next.js dev server
```yaml
command: npm run dev
volumes:
  - ./frontend-nextjs:/app
  - /app/node_modules  # Exclude node_modules
```

### 5.2 Docker Compose Override
**File**: `docker-compose.override.yml` (auto-loaded in dev)
```yaml
version: '3.9'
services:
  backend:
    command: uvicorn src.api.api_server_parquet:app --host 0.0.0.0 --reload
    volumes:
      - ./src:/app/src
  
  frontend:
    command: npm run dev
    volumes:
      - ./frontend-nextjs:/app
      - /app/node_modules
```

### 5.3 Data Update in Docker
```bash
# Option 1: Run script inside container
docker-compose exec backend python src/services/auto_update_data.py

# Option 2: Scheduled cron job (add to backend container)
# Option 3: Separate data-updater service
```

---

## 🚀 Phase 6: Production Optimization (2-3 hours)

### 6.1 Production Dockerfile Enhancements
**Backend**:
- [ ] Use gunicorn instead of uvicorn dev server
  ```dockerfile
  CMD ["gunicorn", "src.api.api_server_parquet:app", \
       "-w", "4", "-k", "uvicorn.workers.UvicornWorker", \
       "--bind", "0.0.0.0:8000"]
  ```
- [ ] Add health check script
- [ ] Enable logging to JSON (for log aggregation)
- [ ] Set resource limits (memory, CPU)

**Frontend**:
- [ ] Build with production optimizations
- [ ] Add nginx for static file serving (optional)
- [ ] Enable compression (gzip, brotli)

### 6.2 Production docker-compose.prod.yml
```yaml
version: '3.9'

services:
  backend:
    build:
      context: .
      dockerfile: backend.Dockerfile
      args:
        - BUILD_ENV=production
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    environment:
      - WORKERS=4
      - LOG_LEVEL=info

  frontend:
    build:
      context: ./frontend-nextjs
      dockerfile: ../frontend.Dockerfile
      args:
        - NODE_ENV=production
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M

  nginx:  # Reverse proxy
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - frontend
      - backend
```

### 6.3 Nginx Reverse Proxy
**File**: `/nginx.conf`
- Route `/api/*` → Backend (8000)
- Route `/*` → Frontend (3000)
- SSL termination
- Rate limiting
- Caching static assets

---

## 🔒 Phase 7: Security & Best Practices (1-2 hours)

### 7.1 Security Checklist
- [ ] Run containers as non-root user
- [ ] Scan images for vulnerabilities (`docker scan`)
- [ ] Use secrets management (not environment variables for sensitive data)
- [ ] Enable Docker Content Trust (image signing)
- [ ] Network isolation (separate frontend/backend networks)
- [ ] Read-only root filesystem where possible

### 7.2 Secrets Management
**Option 1**: Docker secrets (Swarm mode)
```yaml
secrets:
  supabase_key:
    file: ./secrets/supabase_key.txt

services:
  backend:
    secrets:
      - supabase_key
```

**Option 2**: External secrets (HashiCorp Vault, AWS Secrets Manager)

### 7.3 Image Security
```dockerfile
# Use specific version tags (not :latest)
FROM python:3.11.7-slim

# Create non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Read-only root filesystem
VOLUME /tmp
VOLUME /app/logs
```

---

## 📊 Phase 8: Monitoring & Logging (2 hours)

### 8.1 Container Monitoring
**Add to docker-compose**:
```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
```

### 8.2 Logging Strategy
**Centralized Logging**:
- Docker logs → stdout/stderr (already done)
- Log aggregation: ELK stack or Loki
- Log rotation: Docker daemon config

**Backend logging config**:
```python
# Use loguru with JSON output
logger.configure(
    handlers=[{"sink": sys.stdout, "serialize": True}]
)
```

### 8.3 Health Checks
**Backend** (`/api/v1/health`):
```python
@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "data_freshness": check_data_freshness(),
        "api_latency": measure_latency()
    }
```

**Frontend** (Next.js health endpoint):
```typescript
// pages/api/health.ts
export default function handler(req, res) {
  res.status(200).json({ status: 'healthy' })
}
```

---

## 🔄 Phase 9: CI/CD Integration (2-3 hours)

### 9.1 GitHub Actions Workflow
**File**: `.github/workflows/docker-build.yml`

```yaml
name: Docker Build & Push

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to DockerHub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      
      - name: Build and push backend
        uses: docker/build-push-action@v4
        with:
          context: .
          file: backend.Dockerfile
          push: true
          tags: yourusername/bitcoin-backend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Build and push frontend
        uses: docker/build-push-action@v4
        with:
          context: ./frontend-nextjs
          file: frontend.Dockerfile
          push: true
          tags: yourusername/bitcoin-frontend:latest
```

### 9.2 Automated Testing in Docker
```yaml
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run tests in Docker
        run: |
          docker-compose -f docker-compose.test.yml up --abort-on-container-exit
          docker-compose -f docker-compose.test.yml down
```

### 9.3 Deployment Strategy
**Options**:
1. **Docker Hub**: Public/private registry
2. **GitHub Container Registry**: Free for public repos
3. **AWS ECR / GCP GCR**: Cloud provider registries

**Auto-deploy**:
- Webhook to VPS on successful build
- Watchtower for automatic updates
- Blue-green deployment with multiple containers

---

## 📦 Phase 10: Data Management (1-2 hours)

### 10.1 Volume Strategy
```yaml
volumes:
  # Persistent data
  parquet-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/bitcoin-data
  
  # Logs
  app-logs:
    driver: local

services:
  backend:
    volumes:
      - parquet-data:/app/data/hot
      - app-logs:/app/logs
```

### 10.2 Backup Strategy
**Automated backups**:
```bash
#!/bin/bash
# backup.sh
docker-compose exec -T backend tar czf - /app/data/hot | \
  aws s3 cp - s3://bitcoin-backups/data-$(date +%Y%m%d).tar.gz
```

**Cron job**:
```cron
0 2 * * * /opt/bitcoin-platform/backup.sh
```

### 10.3 Data Update Service
**Option**: Separate container for updates
```yaml
  data-updater:
    build:
      context: .
      dockerfile: backend.Dockerfile
    command: python src/services/auto_update_data.py
    volumes:
      - parquet-data:/app/data/hot
    restart: "no"  # Run once
```

**Schedule with cron**:
```bash
0 */4 * * * docker-compose run --rm data-updater
```

---

## 🎯 Implementation Timeline

### Week 1: Core Setup
- **Day 1-2**: Phase 1-2 (Backend Dockerization)
- **Day 3-4**: Phase 3 (Frontend Dockerization)
- **Day 5**: Phase 4 (Docker Compose)
- **Day 6-7**: Testing & debugging

### Week 2: Production Ready
- **Day 1-2**: Phase 6 (Production optimization)
- **Day 3**: Phase 7 (Security)
- **Day 4**: Phase 8 (Monitoring)
- **Day 5**: Phase 9 (CI/CD)
- **Day 6-7**: Documentation & final testing

---

## 📝 Quick Start Commands (After Setup)

```bash
# Development
docker-compose up -d
docker-compose logs -f

# Production
docker-compose -f docker-compose.prod.yml up -d

# Update data
docker-compose exec backend python src/services/auto_update_data.py

# Rebuild after code changes
docker-compose up -d --build

# Clean slate
docker-compose down -v
docker system prune -a
```

---

## 🚧 Known Challenges & Solutions

### Challenge 1: Large Image Sizes
**Solution**: Multi-stage builds, Alpine base images, .dockerignore

### Challenge 2: Hot Reload in Docker
**Solution**: Volume mounts + docker-compose.override.yml

### Challenge 3: Data Persistence
**Solution**: Named volumes + backup scripts

### Challenge 4: Environment Variables
**Solution**: .env files + docker-compose env_file directive

### Challenge 5: PYTHONPATH Issues
**Solution**: Set in Dockerfile ENV and docker-compose environment

---

## ✅ Success Criteria

- [ ] Backend starts in <10 seconds
- [ ] Frontend accessible on http://localhost:3000
- [ ] API responds on http://localhost:8000/api/v1/summary/BTCUSDT
- [ ] Data persists across container restarts
- [ ] Auto-update script works in container
- [ ] Logs accessible via `docker-compose logs`
- [ ] Health checks pass
- [ ] Production build size <500MB total
- [ ] CI/CD pipeline passes all tests

---

## 📚 Next Steps After Dockerization

1. **Deploy to VPS**: DigitalOcean, Linode, AWS EC2
2. **Set up domain**: bitcoin-intelligence.com → nginx
3. **Enable HTTPS**: Let's Encrypt + Certbot
4. **Add Redis**: Cache for API responses
5. **Add PostgreSQL**: Store historical metrics
6. **Implement WebSocket**: Replace polling (per expert review)
7. **Add Celery**: Background tasks (auto-update)
8. **Kubernetes**: If scaling needed (overkill for now)

---

## 🔗 Resources

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Next.js Docker Example](https://github.com/vercel/next.js/tree/canary/examples/with-docker)
- [FastAPI Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [Docker Compose Docs](https://docs.docker.com/compose/)

---

**Created**: 2025-12-15  
**Status**: Ready to implement  
**Priority**: HIGH - Infrastructure foundation
