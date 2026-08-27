from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import api.main as api_main
from auth.security import hash_password
from db.database import get_engine, get_session_factory, init_db
from db.models import UserRow


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = get_engine(tmp_path / "auth_test.db")
    init_db(engine)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        session.add(UserRow(
            username="admin1",
            password_hash=hash_password("correct-password"),
            role="admin",
            created_at=datetime.now(timezone.utc),
        ))
        session.commit()

    monkeypatch.setattr(api_main, "SessionLocal", session_factory)
    return TestClient(api_main.app)


def test_login_with_correct_credentials_returns_a_token(client):
    response = client.post("/auth/login", json={"username": "admin1", "password": "correct-password"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin1"
    assert data["role"] == "admin"
    assert data["access_token"]


def test_login_with_wrong_password_returns_401(client):
    response = client.post("/auth/login", json={"username": "admin1", "password": "wrong-password"})
    assert response.status_code == 401


def test_login_with_unknown_username_returns_401(client):
    response = client.post("/auth/login", json={"username": "nobody", "password": "whatever"})
    assert response.status_code == 401


def test_me_returns_the_authenticated_user(client):
    login_response = client.post("/auth/login", json={"username": "admin1", "password": "correct-password"})
    token = login_response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"username": "admin1", "role": "admin"}


def test_me_without_a_token_returns_401(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_bootstrap_creates_an_admin_when_the_users_table_is_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "bootstrap-admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "bootstrap-password")
    engine = get_engine(tmp_path / "bootstrap_test.db")
    init_db(engine)
    session_factory = get_session_factory(engine)
    monkeypatch.setattr(api_main, "SessionLocal", session_factory)

    api_main._bootstrap_admin_if_needed()

    with session_factory() as session:
        user = session.execute(select(UserRow).where(UserRow.username == "bootstrap-admin")).scalar_one_or_none()
    assert user is not None
    assert user.role == "admin"


def test_bootstrap_does_nothing_when_env_vars_are_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    engine = get_engine(tmp_path / "bootstrap_test2.db")
    init_db(engine)
    session_factory = get_session_factory(engine)
    monkeypatch.setattr(api_main, "SessionLocal", session_factory)

    api_main._bootstrap_admin_if_needed()

    with session_factory() as session:
        assert session.execute(select(UserRow)).first() is None


def test_bootstrap_does_nothing_when_only_username_is_set(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "bootstrap-admin")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    engine = get_engine(tmp_path / "bootstrap_test3.db")
    init_db(engine)
    session_factory = get_session_factory(engine)
    monkeypatch.setattr(api_main, "SessionLocal", session_factory)

    api_main._bootstrap_admin_if_needed()

    with session_factory() as session:
        assert session.execute(select(UserRow)).first() is None


def test_bootstrap_does_nothing_when_only_password_is_set(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.setenv("ADMIN_PASSWORD", "bootstrap-password")
    engine = get_engine(tmp_path / "bootstrap_test4.db")
    init_db(engine)
    session_factory = get_session_factory(engine)
    monkeypatch.setattr(api_main, "SessionLocal", session_factory)

    api_main._bootstrap_admin_if_needed()

    with session_factory() as session:
        assert session.execute(select(UserRow)).first() is None


def test_bootstrap_does_not_create_a_second_admin_when_the_users_table_is_not_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "bootstrap-admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "bootstrap-password")
    engine = get_engine(tmp_path / "bootstrap_test5.db")
    init_db(engine)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        session.add(UserRow(
            username="existing-admin",
            password_hash=hash_password("existing-password"),
            role="admin",
            created_at=datetime.now(timezone.utc),
        ))
        session.commit()

    monkeypatch.setattr(api_main, "SessionLocal", session_factory)

    api_main._bootstrap_admin_if_needed()

    with session_factory() as session:
        users = session.execute(select(UserRow)).scalars().all()
    assert len(users) == 1
    assert users[0].username == "existing-admin"
