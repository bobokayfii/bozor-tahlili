from datetime import datetime, timedelta, timezone

import jwt

from auth.security import create_access_token, decode_access_token, hash_password, verify_password


def test_hash_password_returns_a_different_string_than_the_input():
    hashed = hash_password("mySecret123")
    assert hashed != "mySecret123"


def test_verify_password_returns_true_for_the_correct_password():
    hashed = hash_password("mySecret123")
    assert verify_password("mySecret123", hashed) is True


def test_verify_password_returns_false_for_the_wrong_password():
    hashed = hash_password("mySecret123")
    assert verify_password("wrongPassword", hashed) is False


def test_create_and_decode_access_token_round_trips_the_payload():
    token = create_access_token(user_id=1, username="admin", role="admin")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["user_id"] == 1
    assert payload["username"] == "admin"
    assert payload["role"] == "admin"


def test_decode_access_token_returns_none_for_a_garbage_token():
    assert decode_access_token("not-a-real-token") is None


def test_decode_access_token_returns_none_for_an_expired_token():
    import os

    expired_payload = {
        "user_id": 1,
        "username": "admin",
        "role": "admin",
        "exp": datetime.now(timezone.utc) - timedelta(days=1),
    }
    expired_token = jwt.encode(expired_payload, os.environ["AUTH_SECRET_KEY"], algorithm="HS256")
    assert decode_access_token(expired_token) is None
