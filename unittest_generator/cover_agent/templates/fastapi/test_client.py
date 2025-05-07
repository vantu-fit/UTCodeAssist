import pytest
from fastapi.testclient import TestClient
from main import app  # Adjust import based on your app structure

client = TestClient(app)

def test_client_initialization():
    """Test that the test client can be created successfully"""
    assert client is not None

def test_app_startup():
    """Test that the FastAPI app starts up correctly"""
    response = client.get("/docs")
    assert response.status_code == 200