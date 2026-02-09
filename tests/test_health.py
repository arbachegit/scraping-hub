"""Basic health tests"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "apis" in data
