"""Basic health tests"""

from api.main import app
from tests.compat_client import AppClient as TestClient

client = TestClient(app)


def test_health():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "apis" in data
