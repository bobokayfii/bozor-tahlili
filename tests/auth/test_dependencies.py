from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auth import dependencies as auth_dependencies
from auth.dependencies import get_current_user, require_admin
from auth.security import create_access_token
from db.models import Base, UserRow


@pytest.fixture(autouse=True)
def seeded_session_factory():
    # get_current_user looks up the user's current token_version via
    # auth.dependencies' module-level session factory (see its docstring).
    # Without pointing this at an isolated, known-seeded DB, these tests
    # would silently depend on whatever real data/bank_products.db happens
    # to contain on the machine running them - the exact trap this fixture
    # exists to close: a fresh checkout has no such rows and every test
    # here would 401 instead of exercising the behavior it names.
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        session.add(UserRow(
            id=1, username="admin", password_hash="x", role="admin",
            created_at=datetime.now(timezone.utc), token_version=0,
        ))
        session.add(UserRow(
            id=2, username="jane", password_hash="x", role="user",
            created_at=datetime.now(timezone.utc), token_version=0,
        ))
        session.commit()

    previous = auth_dependencies._session_factory
    auth_dependencies.configure_session_factory(factory)
    yield
    auth_dependencies._session_factory = previous


def test_get_current_user_returns_the_user_for_a_valid_token():
    token = create_access_token(user_id=1, username="admin", role="admin")
    user = get_current_user(authorization=f"Bearer {token}")
    assert user.id == 1
    assert user.username == "admin"
    assert user.role == "admin"


def test_get_current_user_raises_401_when_no_header_is_given():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization=None)
    assert exc_info.value.status_code == 401


def test_get_current_user_raises_401_for_a_malformed_header():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization="not-a-bearer-token")
    assert exc_info.value.status_code == 401


def test_get_current_user_raises_401_for_an_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization="Bearer garbage")
    assert exc_info.value.status_code == 401


def test_get_current_user_raises_401_when_token_version_no_longer_matches():
    # Simulates an admin resetting this account's password/role after the
    # token was issued - the token's stale claims must stop working well
    # before its 30-day expiry, which is the whole point of token_version.
    token = create_access_token(user_id=1, username="admin", role="admin", token_version=0)
    with auth_dependencies._session_factory() as session:
        user = session.get(UserRow, 1)
        user.token_version = 1
        session.commit()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401


def test_get_current_user_raises_401_when_the_user_no_longer_exists():
    token = create_access_token(user_id=999, username="ghost", role="admin")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401


def test_require_admin_returns_the_user_when_role_is_admin():
    token = create_access_token(user_id=1, username="admin", role="admin")
    user = get_current_user(authorization=f"Bearer {token}")
    assert require_admin(user=user).id == 1


def test_require_admin_raises_403_when_role_is_user():
    token = create_access_token(user_id=2, username="jane", role="user")
    user = get_current_user(authorization=f"Bearer {token}")
    with pytest.raises(HTTPException) as exc_info:
        require_admin(user=user)
    assert exc_info.value.status_code == 403
