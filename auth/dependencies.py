from __future__ import annotations

from typing import Callable

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.security import decode_access_token
from db.models import UserRow


class AuthenticatedUser(BaseModel):
    id: int
    username: str
    role: str


# Set once at startup (api/main.py, right after SessionLocal is built) so
# get_current_user can look up the current token_version without importing
# api.main directly, which would be circular (api.main imports this module
# for its route dependencies). Mirrors how api/main.py itself keeps
# SessionLocal as a plain module-level global rather than routing every
# request through a FastAPI Depends(get_db) - single-worker deployment,
# same simplicity tradeoff already made there.
_session_factory: Callable[[], Session] | None = None


def configure_session_factory(factory: Callable[[], Session]) -> None:
    global _session_factory
    _session_factory = factory


def get_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Tizimga kirish talab qilinadi")
    token = authorization.removeprefix("Bearer ")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Sessiya yaroqsiz yoki muddati tugagan")

    # Without this DB check, a token keeps its role/username claims for its
    # full 30-day lifetime even after an admin demotes the account or resets
    # its password - the exact "revoke a compromised account" action the
    # admin panel exists for would silently not take effect. token_version
    # is bumped on every role/password change (api/main.py, update_user).
    if _session_factory is not None:
        with _session_factory() as session:
            user = session.get(UserRow, payload["user_id"])
            if user is None or user.token_version != payload.get("token_version", 0):
                raise HTTPException(status_code=401, detail="Sessiya yaroqsiz yoki muddati tugagan")

    return AuthenticatedUser(id=payload["user_id"], username=payload["username"], role=payload["role"])


def require_admin(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Faqat administrator uchun")
    return user
