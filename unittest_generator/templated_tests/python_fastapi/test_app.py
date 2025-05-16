import pytest  
from fastapi.testclient import TestClient  
from app import app  
  
@pytest.fixture  
def client():  
    with TestClient(app) as c:  
        yield c  
from fastapi import HTTPException
from datetime import date
  
def test_placeholder():  
    """Placeholder test to establish file structure"""  
    pass

def test_echo_endpoint(client):
    response = client.get("/echo/Hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello"}


def test_is_palindrome(client):
    response = client.get("/is-palindrome/racecar")
    assert response.status_code == 200
    assert response.json() == {"is_palindrome": True}


def test_sqrt_negative(client):
    response = client.get("/sqrt/-1")
    assert response.status_code == 400
    assert response.json() == {"detail": "Cannot take square root of a negative number"}


def test_square_endpoint(client):
    response = client.get("/square/4")
    assert response.status_code == 200
    assert response.json() == {"result": 16}


def test_divide_by_zero(client):
    response = client.get("/divide/10/0")
    assert response.status_code == 400
    assert response.json() == {"detail": "Cannot divide by zero"}


def test_multiply_endpoint(client):
    response = client.get("/multiply/3/7")
    assert response.status_code == 200
    assert response.json() == {"result": 21}


def test_subtract_endpoint(client):
    response = client.get("/subtract/10/4")
    assert response.status_code == 200
    assert response.json() == {"result": 6}


def test_add_endpoint(client):
    response = client.get("/add/3/5")
    assert response.status_code == 200
    assert response.json() == {"result": 8}


def test_current_date(client):
    response = client.get("/current-date")
    assert response.status_code == 200
    assert response.json() == {"date": date.today().isoformat()}


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI application!"}
