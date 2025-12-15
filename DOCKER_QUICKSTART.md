# Docker Quick Start Guide
## Bitcoin Intelligence Platform

### 🚀 Prerequisites

```bash
# Check Docker installation
docker --version
docker-compose --version

# If not installed on Linux:
sudo apt update
sudo apt install docker.io docker-compose
sudo usermod -aG docker $USER
newgrp docker
```

---

## �� Quick Start

```bash
# Build and start
docker-compose build
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Test services
curl http://localhost:8000/api/v1/health
curl http://localhost:3000/api/health
```

---

## 🔧 Common Commands

```bash
# Stop services
docker-compose down

# Restart
docker-compose restart

# Update data
docker-compose exec backend python src/services/auto_update_data.py

# Shell access
docker-compose exec backend bash

# View logs
docker-compose logs -f backend
```

---

## �� Full Documentation

See [DOCKER_ROADMAP.md](DOCKER_ROADMAP.md) for complete setup guide.
