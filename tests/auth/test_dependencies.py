import pytest
from fastapi import HTTPException

from auth.dependencies import get_current_user, require_admin
from auth.security import create_access_token


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
