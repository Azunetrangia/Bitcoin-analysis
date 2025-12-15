# Multi-stage build for Bitcoin Intelligence Platform Backend
# Stage 1: Base image with system dependencies
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Builder - install Python dependencies
FROM base as builder

WORKDIR /app

# Copy requirements first (cache layer)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 3: Runtime
FROM base as runtime

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy installed packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser pyproject.toml .
COPY --chown=appuser:appuser conftest.py .

# Create directories for data and logs
RUN mkdir -p data/hot data/raw data/processed logs && \
    chown -R appuser:appuser data logs

# Set environment variables
ENV PYTHONPATH=/app \
    PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    DATA_HOT_PATH=/app/data/hot \
    DATA_RAW_PATH=/app/data/raw

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "src.api.api_server_parquet:app", "--host", "0.0.0.0", "--port", "8000"]
