"""
Basic smoke tests for FastAPI application.

Tests API startup, health checks, and basic endpoint structure.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Bitcoin Market Intelligence API"
    assert data["version"] == "1.0.0"
    assert "docs" in data or "documentation" in data


def test_openapi_docs_available(client):
    """Test that OpenAPI docs are accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/openapi.json")
    assert response.status_code == 200


# ============================================================================
# ROUTER STRUCTURE
# ============================================================================

def test_market_data_router_registered(client):
    """Test market data endpoints are registered."""
    # Get OpenAPI schema
    response = client.get("/openapi.json")
    schema = response.json()
    
    # Check paths exist
    assert "/api/v1/market-data/" in schema["paths"]
    assert "/api/v1/market-data/latest" in schema["paths"]
    assert "/api/v1/market-data/download" in schema["paths"]


def test_analysis_router_registered(client):
    """Test analysis endpoints are registered."""
    response = client.get("/openapi.json")
    schema = response.json()
    
    # Check paths exist
    assert "/api/v1/analysis/indicators" in schema["paths"]
    assert "/api/v1/analysis/regimes" in schema["paths"]
    assert "/api/v1/analysis/risk-metrics" in schema["paths"]


def test_scheduler_router_registered(client):
    """Test scheduler endpoints are registered."""
    response = client.get("/openapi.json")
    schema = response.json()
    
    # Check paths exist
    assert "/api/v1/scheduler/status" in schema["paths"]
    assert "/api/v1/scheduler/start" in schema["paths"]
    assert "/api/v1/scheduler/stop" in schema["paths"]


# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

def test_cors_headers_present(client):
    """Test CORS headers are set."""
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000"}
    )
    
    assert "access-control-allow-origin" in response.headers


# ============================================================================
# ERROR HANDLING
# ============================================================================

def test_404_error_handling(client):
    """Test 404 error handling."""
    response = client.get("/nonexistent-endpoint")
    
    assert response.status_code == 404


def test_invalid_method_handling(client):
    """Test invalid HTTP method handling."""
    response = client.delete("/health")
    
    assert response.status_code == 405  # Method Not Allowed
