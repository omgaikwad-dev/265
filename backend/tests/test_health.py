import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    """Verify root endpoint returns project metadata and health links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "FDRSetu"
    assert data["status"] == "online"
    assert "/api/v1/health" in data["health"]

def test_health_endpoint():
    """Verify health check endpoint returns 200 and checks db & storage."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "FDRSetu"
    assert "status" in data
    assert "database" in data
    assert "storage" in data
    assert data["database"]["verified"] is True
    assert data["storage"]["status"] == "ready"
