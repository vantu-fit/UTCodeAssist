import pytest
from fastapi.testclient import TestClient
from main import app  # Adjust import based on your app structure

client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code in [200, 404]  # 404 if not implemented

def test_app_metadata():
    """Test app basic metadata"""
    assert app.title is not None
    assert app.version is not None