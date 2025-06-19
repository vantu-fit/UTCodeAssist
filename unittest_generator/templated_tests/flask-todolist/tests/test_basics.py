import pytest
from flask import current_app
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

def test_app_exists(app):
    assert current_app is not None

def test_app_is_testing(app):
    assert app.config["TESTING"]

def test_password_setter():
    u = User(password="correcthorsebatterystaple")
    assert u.password_hash is not None

def test_no_password_getter():
    u = User(password="correcthorsebatterystaple")
    with pytest.raises(AttributeError):
        _ = u.password

def test_password_verification():
    u = User(password="correcthorsebatterystaple")
    assert u.verify_password("correcthorsebatterystaple")
    assert not u.verify_password("incorrecthorsebatterystaple")

def test_password_salts_are_random():
    u1 = User(password="correcthorsebatterystaple")
    u2 = User(password="correcthorsebatterystaple")
    assert u1.password_hash != u2.password_hash

def test_adding_new_user(app):
    user = User(username="adam", email="adam@example.com", password="correcthorsebatterystaple")
    db.session.add(user)
    db.session.commit()
    found = User.query.filter_by(username="adam").first()
    assert found is not None
    assert found.email == "adam@example.com"

def test_adding_new_todo_without_user(app):
    todolist = TodoList(title="shopping list")
    db.session.add(todolist)
    db.session.commit()
    todo = Todo(description="Read a book about TDD", todolist_id=todolist.id)
    db.session.add(todo)
    db.session.commit()
    found = TodoList.query.filter_by(id=todolist.id).first()
    assert found.title == "shopping list"
    # assert found.creator == user.username

def test_blueprints_registration(app):
    with app.app_context():
        assert 'main' in app.blueprints
        assert 'auth' in app.blueprints
        assert 'api' in app.blueprints
        assert 'utils' in app.blueprints
