from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from auth.security import decode_access_token


class AuthenticatedUser(BaseModel):
    id: int
    username: str
    role: str


def get_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Tizimga kirish talab qilinadi")
    token = authorization.removeprefix("Bearer ")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Sessiya yaroqsiz yoki muddati tugagan")
    return AuthenticatedUser(id=payload["user_id"], username=payload["username"], role=payload["role"])


def require_admin(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Faqat administrator uchun")
    return user
