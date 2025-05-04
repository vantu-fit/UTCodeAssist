import json
import pytest
from flask import url_for

from app import create_app, db
from app.models import User, TodoList, Todo

@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def headers():
    return {"Accept": "application/json", "Content-Type": "application/json"}

@pytest.fixture
def user_data():
    return {
        "username": "utcoassist",
        "email": "utcoassist@example.com",
        "password": "utcoassist123",
    }

def test_main_route(client):
    response = client.get("/api/")
    assert response.status_code == 200
    json_response = response.get_json()
    assert "users" in json_response
    assert "todolists" in json_response

def test_not_found(client):
    response = client.get("/api/not/found")
    assert response.status_code == 404
    json_response = response.get_json()
    assert json_response["error"] == "Not found"
