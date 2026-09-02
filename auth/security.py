from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

ALGORITHM = "HS256"
TOKEN_TTL_DAYS = 30


def _get_secret_key() -> str:
    secret = os.environ.get("AUTH_SECRET_KEY")
    if not secret:
        raise RuntimeError("AUTH_SECRET_KEY environment o'zgaruvchisi talab qilinadi")
    return secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: int, username: str, role: str, token_version: int = 0) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "token_version": token_version,
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS),
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
