import pytest
from flask import url_for
from app import create_app, db
from app.models import User, TodoList, Todo

@pytest.fixture
def client():
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()

def test_home_page(client):
    with client.application.test_request_context():
        url = url_for("main.index")
    response = client.get(url)
    assert response.status_code == 200
    assert b"Todolist" in response.data or b"Dead simple Todolists." in response.data

def test_register_page(client):
    with client.application.test_request_context():
        url = url_for("auth.register")
    response = client.get(url)
    assert response.status_code == 200
    assert b"Register" in response.data

def test_login_page(client):
    with client.application.test_request_context():
        url = url_for("auth.login")
    response = client.get(url)
    assert response.status_code == 200
    assert b"Login" in response.data

def test_register_and_login(client):
    username = "bob"
    email = "bob@example.com"
    password = "secret123"

    with client.application.test_request_context():
        register_url = url_for("auth.register")
        login_url = url_for("auth.login")

    # Register
    response = client.post(
        register_url,
        data={
            "username": username,
            "email": email,
            "password": password,
            "password_confirmation": password,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Login" in response.data

    # Login
    @pytest.fixture
    def client():
        app = create_app("testing")
        app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

        with app.test_client() as client:
            with app.app_context():
                db.create_all()
            yield client
            with app.app_context():
                db.session.remove()
                db.drop_all()

    def test_home_page(client):
        with client.application.test_request_context():
            url = url_for("main.index")
        response = client.get(url)
        assert response.status_code == 200
        assert b"Todolist" in response.data or b"Dead simple Todolists." in response.data

    def test_register_page(client):
        with client.application.test_request_context():
            url = url_for("auth.register")
        response = client.get(url)
        assert response.status_code == 200
        assert b"Register" in response.data

    def test_login_page(client):
        with client.application.test_request_context():
            url = url_for("auth.login")
        response = client.get(url)
        assert response.status_code == 200
        assert b"Login" in response.data

    def test_register_and_login(client):
        username = "bob"
        email = "bob@example.com"
        password = "secret123"

        with client.application.test_request_context():
            register_url = url_for("auth.register")
            login_url = url_for("auth.login")

        # Register
        response = client.post(
            register_url,
            data={
                "username": username,
                "email": email,
                "password": password,
                "password_confirmation": password,
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Login" in response.data

        # Login
        response = client.post(
            login_url,
            data={
                "email_or_username": email,
                "password": password,
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"logout" in response.data or b"Overview" in response.data


    def test_invalid_login(client):
        with client.application.test_request_context():
            login_url = url_for("auth.login")
        response = client.post(
            login_url,
            data={
                "email_or_username": "notexist@example.com",
                "password": "wrongpass",
            },
            follow_redirects=True,
        )
        assert b"Unable to login" in response.data or b"Login" in response.data

    def test_register_duplicate_username(client):
        username = "dupe"
        email1 = "dupe1@example.com"
        email2 = "dupe2@example.com"
        password = "testpass"
        with client.application.test_request_context():
            register_url = url_for("auth.register")

        # First registration
        client.post(
            register_url,
            data={
                "username": username,
                "email": email1,
                "password": password,
                "password_confirmation": password,
            },
            follow_redirects=True,
        )
        # Second registration with same username
        response = client.post(
            register_url,
            data={
                "username": username,
                "email": email2,
                "password": password,
                "password_confirmation": password,
            },
            follow_redirects=True,
        )
        assert b"Username already in use" in response.data

    def test_register_duplicate_email(client):
        username1 = "user1"
        username2 = "user2"
        email = "dupe@example.com"
        password = "testpass"
        with client.application.test_request_context():
            register_url = url_for("auth.register")

        # First registration
        client.post(
            register_url,
            data={
                "username": username1,
                "email": email,
                "password": password,
                "password_confirmation": password,
            },
            follow_redirects=True,
        )
        # Second registration with same email
        response = client.post(
            register_url,
            data={
                "username": username2,
                "email": email,
                "password": password,
                "password_confirmation": password,
            },
            follow_redirects=True,
        )
        assert b"Email already registered" in response.data

    def test_404_page(client):
        response = client.get("/not-a-real-page", follow_redirects=True)
        assert response.status_code == 404 or b"Not Found" in response.data