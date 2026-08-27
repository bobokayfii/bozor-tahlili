# Auth (login/parol) va Admin Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Butun saytni login/parol bilan yopish, ikkita rolni (`admin`, `user`) joriy qilish va admin uchun foydalanuvchilarni boshqarish (qo'shish/ro'yxat/tahrirlash) panelini qo'shish.

**Architecture:** Backend — yangi `UserRow` jadval, `bcrypt` bilan parol hash, `PyJWT` bilan 30 kunlik bearer token, barcha mavjud endpointlar `Depends(get_current_user)` bilan himoyalanadi, admin-only endpointlar `Depends(require_admin)` bilan. Frontend — router kutubxonasisiz, mavjud state-based navigatsiya uslubida: token `localStorage`da, `AuthContext` orqali sessiya boshqariladi, `App.tsx` `'login' → asosiy ilova → admin panel` ko'rinishlarini almashtiradi.

**Tech Stack:** FastAPI, SQLAlchemy, PyJWT, bcrypt, pytest (backend); React 19, Vite, vitest + React Testing Library (frontend).

**Spec:** [docs/superpowers/specs/2026-08-27-auth-va-admin-panel-design.md](../specs/2026-08-27-auth-va-admin-panel-design.md)

## Global Constraints

- Sessiya muddati: 30 kun (JWT `exp`).
- Token `localStorage`da `bozor-tahlili-token` kaliti bilan saqlanadi (foydalanuvchi bilan kelishilgan tanlov — httpOnly cookie emas).
- Role qiymatlari faqat `"admin"` yoki `"user"` (kichik harf, string).
- `AUTH_SECRET_KEY` environment o'zgaruvchisi majburiy — bo'lmasa backend ishga tushmaydi (startup'da `RuntimeError`).
- Yangi backend bog'liqliklar: `PyJWT`, `bcrypt` — `passlib` ISHLATILMAYDI.
- Barcha mavjud API endpointlar (istisnosiz) autentifikatsiya talab qiladi; faqat `/auth/login` ochiq.
- Admin o'z `id`sini `role="user"`ga o'zgartira olmaydi (400 xato).
- Ko'lamdan tashqarida: user o'chirish, o'z parolini o'zi almashtirish, "parolni unutdim". Bularni qo'shmang.
- Frontend'ga router kutubxonasi qo'shilmaydi — mavjud state-based navigatsiya uslubiga rioya qilinadi.
- Har bir yangi UI matni `frontend/src/lib/i18n.ts`da HAM `uz`, HAM `ru` uchun qo'shiladi.

---

## Task 1: `UserRow` modeli va parol/JWT xavfsizlik utilitalari

**Files:**
- Modify: `db/models.py`
- Create: `auth/__init__.py`
- Create: `auth/security.py`
- Modify: `requirements.txt`
- Modify: `conftest.py`
- Create: `tests/auth/__init__.py`
- Create: `tests/auth/test_security.py`

**Interfaces:**
- Produces: `UserRow` (ORM model: `id`, `username`, `password_hash`, `role`, `created_at`), `hash_password(password: str) -> str`, `verify_password(password: str, password_hash: str) -> bool`, `create_access_token(user_id: int, username: str, role: str) -> str`, `decode_access_token(token: str) -> dict | None`

- [ ] **Step 1: `UserRow` modelini qo'shish**

`db/models.py` faylining oxiriga (mavjud `ScrapeRunRow` klassidan keyin) qo'shing:

```python
class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime)
```

(Yangi import kerak emas — `String`, `DateTime`, `Mapped`, `mapped_column` faylda allaqachon import qilingan.)

- [ ] **Step 2: `requirements.txt`ga yangi bog'liqliklarni qo'shish**

`requirements.txt` oxiriga qo'shing:

```
PyJWT==2.9.0
bcrypt==4.2.0
```

O'rnatish:

```bash
.venv/Scripts/pip install PyJWT==2.9.0 bcrypt==4.2.0
```

- [ ] **Step 3: `conftest.py`ga test uchun `AUTH_SECRET_KEY` default qiymatini qo'shish**

Testlar `api.main`ni import qilganda (keyingi tasklarda) modul darajasida `AUTH_SECRET_KEY` talab qilinadi — shu sabab butun test sessiyasi uchun bitta default qiymat conftest'da, har qanday test modulidan OLDIN o'rnatiladi. `conftest.py` faylining eng boshiga (boshqa importlardan oldin) qo'shing:

```python
import os

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-for-pytest")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base
```

(Qolgan fayl o'zgarishsiz qoladi.)

- [ ] **Step 4: `auth/__init__.py` va `tests/auth/__init__.py`ni yaratish**

Ikkalasi ham bo'sh fayl (mavjud `api/__init__.py`, `tests/api/__init__.py` namunasiga mos).

- [ ] **Step 5: Muvaffaqiyatsiz testni yozish**

`tests/auth/test_security.py`:

```python
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
```

- [ ] **Step 6: Testni ishga tushirib, muvaffaqiyatsiz bo'lishini tekshirish**

Run: `.venv/Scripts/python.exe -m pytest tests/auth/test_security.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.security'`

- [ ] **Step 7: `auth/security.py`ni yozish**

```python
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


def create_access_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS),
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
```

- [ ] **Step 8: Testlarni qayta ishga tushirib, o'tishini tekshirish**

Run: `.venv/Scripts/python.exe -m pytest tests/auth/test_security.py -v`
Expected: PASS (6 testlar)

- [ ] **Step 9: Commit**

```bash
git add db/models.py requirements.txt conftest.py auth/__init__.py auth/security.py tests/auth/__init__.py tests/auth/test_security.py
git commit -m "feat: add UserRow model and password/JWT security utilities"
```

---

## Task 2: Auth dependencies (`get_current_user`, `require_admin`)

**Files:**
- Create: `auth/dependencies.py`
- Create: `tests/auth/test_dependencies.py`

**Interfaces:**
- Consumes: `auth.security.decode_access_token` (Task 1)
- Produces: `AuthenticatedUser` (pydantic model: `id: int`, `username: str`, `role: str`), `get_current_user(authorization: str | None) -> AuthenticatedUser` (FastAPI dependency, raises `HTTPException(401)`), `require_admin(user: AuthenticatedUser) -> AuthenticatedUser` (raises `HTTPException(403)` agar admin bo'lmasa)

- [ ] **Step 1: Muvaffaqiyatsiz testni yozish**

`tests/auth/test_dependencies.py`:

```python
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
```

- [ ] **Step 2: Testni ishga tushirib, muvaffaqiyatsiz bo'lishini tekshirish**

Run: `.venv/Scripts/python.exe -m pytest tests/auth/test_dependencies.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.dependencies'`

- [ ] **Step 3: `auth/dependencies.py`ni yozish**

```python
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
```

- [ ] **Step 4: Testlarni qayta ishga tushirib, o'tishini tekshirish**

Run: `.venv/Scripts/python.exe -m pytest tests/auth/test_dependencies.py -v`
Expected: PASS (6 testlar)

- [ ] **Step 5: Commit**

```bash
git add auth/dependencies.py tests/auth/test_dependencies.py
git commit -m "feat: add get_current_user and require_admin FastAPI dependencies"
```

---

## Task 3: `POST /auth/login`, `GET /auth/me` va birinchi admin bootstrap

**Files:**
- Modify: `api/main.py`
- Create: `tests/api/test_auth.py`
- Modify: `.env.example`
- Modify: `README.md`

**Interfaces:**
- Consumes: `auth.dependencies.AuthenticatedUser`, `get_current_user` (Task 2); `auth.security.create_access_token`, `hash_password`, `verify_password` (Task 1); `db.models.UserRow` (Task 1)
- Produces: `POST /auth/login` → `{access_token, username, role}` yoki `401`; `GET /auth/me` → `{username, role}`; `api.main._bootstrap_admin_if_needed()` funksiyasi

- [ ] **Step 1: Import blokini yangilash**

`api/main.py`ning boshidagi import blokini (1—13-qatorlar) quyidagiga almashtiring:

```python
from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select

from auth.dependencies import AuthenticatedUser, get_current_user
from auth.security import create_access_token, hash_password, verify_password
```

Va bir necha qator pastdagi (hozirgi `from db.database import ...` / `from db.models import ProductRow` qatorlari):

```python
from db.database import get_engine, get_session_factory, init_db
from db.models import ProductRow, UserRow
```

- [ ] **Step 2: `AUTH_SECRET_KEY` majburiyligini va bootstrap funksiyasini qo'shish**

`SessionLocal = get_session_factory(_engine)` qatoridan keyin (va scheduler bilan bog'liq `threading.Lock()` bloklaridan oldin) qo'shing:

```python
if not os.environ.get("AUTH_SECRET_KEY"):
    raise RuntimeError("AUTH_SECRET_KEY environment o'zgaruvchisi talab qilinadi (JWT token imzolash uchun)")


def _bootstrap_admin_if_needed() -> None:
    """Users jadvali bo'sh bo'lsa (birinchi marta ishga tushirilganda) va
    ADMIN_USERNAME/ADMIN_PASSWORD env o'zgaruvchilar berilgan bo'lsa,
    tizimga kirish uchun birinchi admin akkauntni avtomatik yaratadi."""
    with SessionLocal() as session:
        if session.execute(select(UserRow)).first() is not None:
            return
        admin_username = os.environ.get("ADMIN_USERNAME")
        admin_password = os.environ.get("ADMIN_PASSWORD")
        if not admin_username or not admin_password:
            return
        session.add(UserRow(
            username=admin_username,
            password_hash=hash_password(admin_password),
            role="admin",
            created_at=datetime.now(timezone.utc),
        ))
        session.commit()
```

- [ ] **Step 3: Bootstrap'ni `lifespan`ga ulash**

`lifespan` funksiyasi ichida (`interval_hours = ...` qatoridan oldin) birinchi qator sifatida qo'shing:

```python
@asynccontextmanager
async def lifespan(_: FastAPI):
    _bootstrap_admin_if_needed()
    # Bu yerdan pastda mavjud scheduler kodi o'zgarishsiz qoladi
    interval_hours = int(os.environ.get("SCRAPE_INTERVAL_HOURS", "24"))
    ...
```

- [ ] **Step 4: Login va me endpointlarini qo'shish**

CORS middleware blokidan keyin, `class RecommendRequest(BaseModel):` dan oldin qo'shing:

```python
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    username: str
    role: str


@app.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    with SessionLocal() as session:
        user = session.execute(select(UserRow).where(UserRow.username == request.username)).scalar_one_or_none()
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Login yoki parol noto'g'ri")
    token = create_access_token(user_id=user.id, username=user.username, role=user.role)
    return LoginResponse(access_token=token, username=user.username, role=user.role)


@app.get("/auth/me")
def get_me(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role}
```

- [ ] **Step 5: `.env.example`ni yangilash**

`.env.example`ga (`SCRAPE_INTERVAL_HOURS` qatoridan keyin) qo'shing:

```
# JWT tokenlarni imzolash uchun maxfiy kalit — majburiy, bo'lmasa backend
# ishga tushmaydi. Uzun, tasodifiy satr bo'lishi kerak (masalan:
# `python -c "import secrets; print(secrets.token_hex(32))"`).
AUTH_SECRET_KEY=

# Birinchi admin akkaunt — faqat "users" jadvali bo'sh bo'lganda (birinchi
# marta ishga tushirilganda) ishlatiladi. Keyinchalik admin panel orqali
# boshqa userlar qo'shiladi, bu ikkalasini o'chirib qo'yish mumkin.
ADMIN_USERNAME=
ADMIN_PASSWORD=
```

- [ ] **Step 6: README'ga lokal ishga tushirish uchun eslatma qo'shish**

`README.md`dagi `OPENAI_API_KEY`ni sozlash bo'limidan keyin, xuddi shunday formatda `AUTH_SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`ni PowerShell/cmd/bash misollari bilan qo'shing (mavjud `OPENAI_API_KEY` bo'limidagi uch operatsion tizim uchun ko'rsatilgan format naqshiga mos).

- [ ] **Step 7: Muvaffaqiyatsiz testni yozish**

`tests/api/test_auth.py`:

```python
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
```

- [ ] **Step 8: Testni ishga tushirib, muvaffaqiyatsiz bo'lishini tekshirish**

Run: `.venv/Scripts/python.exe -m pytest tests/api/test_auth.py -v`
Expected: FAIL — `AttributeError` yoki `404` (`/auth/login` hali mavjud emas)

- [ ] **Step 9: Testlarni qayta ishga tushirib, o'tishini tekshirish**

Run: `.venv/Scripts/python.exe -m pytest tests/api/test_auth.py -v`
Expected: PASS (7 testlar)

- [ ] **Step 10: To'liq backend test to'plamini ishga tushirish (regressiya tekshiruvi)**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: `tests/api/test_main.py`dagi mavjud testlar hali PASS (bu endpointlar hali himoyalanmagan — Task 4da o'zgaradi), yangi `tests/auth/` va `tests/api/test_auth.py` testlari PASS.

- [ ] **Step 11: Commit**

```bash
git add api/main.py .env.example README.md tests/api/test_auth.py
git commit -m "feat: add login/me endpoints and first-admin bootstrap"
```

---

## Task 4: Mavjud endpointlarni himoyalash + test fixture'ni yangilash

**Files:**
- Modify: `api/main.py`
- Create: `tests/api/conftest.py`
- Modify: `tests/api/test_main.py`

**Interfaces:**
- Consumes: `auth.dependencies.AuthenticatedUser`, `get_current_user` (Task 2); `auth.security.create_access_token`, `hash_password` (Task 1)
- Produces: barcha mavjud endpointlar endi `401` qaytaradi tokensiz; `tests/api/conftest.py`dagi umumiy `client` fixture (autentifikatsiyalangan, `id=1`/`username="test-admin"`/`role="admin"`)

- [ ] **Step 1: Har bir mavjud endpoint imzosiga himoya parametrini qo'shish**

`api/main.py`da quyidagi 8 ta endpoint funksiyasi imzosiga `_: AuthenticatedUser = Depends(get_current_user)` parametrini qo'shing (funksiya tanasi o'zgarmaydi):

```python
@app.get("/products")
def list_products(category: str | None = None, bank: str | None = None, _: AuthenticatedUser = Depends(get_current_user)):
```

```python
@app.get("/categories")
def list_categories(_: AuthenticatedUser = Depends(get_current_user)):
```

```python
@app.get("/unavailable-banks")
def list_unavailable_banks(category: str, _: AuthenticatedUser = Depends(get_current_user)):
```

```python
@app.post("/recommend")
def recommend(request: RecommendRequest, _: AuthenticatedUser = Depends(get_current_user)):
```

```python
@app.post("/explain-product")
def explain_product(request: ExplainProductRequest, _: AuthenticatedUser = Depends(get_current_user)):
```

```python
@app.get("/export-excel")
def export_excel(category: str, language: str = "uz", _: AuthenticatedUser = Depends(get_current_user)):
```

```python
@app.get("/export-excel-all")
def export_excel_all(language: str = "uz", _: AuthenticatedUser = Depends(get_current_user)):
```

```python
@app.post("/trigger-scrape")
def trigger_scrape(_: AuthenticatedUser = Depends(get_current_user)):
```

- [ ] **Step 2: `tests/api/conftest.py`ni yaratish — umumiy autentifikatsiyalangan `client` fixture**

`tests/api/test_main.py`dagi mavjud `client` fixture'ni shu yangi faylga ko'chiring va autentifikatsiya bilan boyiting:

```python
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from auth.security import create_access_token, hash_password
from db.database import get_engine, get_session_factory, init_db
from db.models import ProductRow, UserRow


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = get_engine(tmp_path / "api_test.db")
    init_db(engine)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        session.add(ProductRow(
            bank="SQB", category="mikroqarz", product_name="SQB Mikroqarz",
            rate_min=28.0, rate_max=31.0, term_min_months=3, term_max_months=36,
            amount_max_som=100_000_000, requires_collateral=False,
            down_payment_pct=None, source_url="https://sqb.uz",
            scraped_at=datetime.now(timezone.utc),
        ))
        session.add(UserRow(
            id=1,
            username="test-admin",
            password_hash=hash_password("test-password"),
            role="admin",
            created_at=datetime.now(timezone.utc),
        ))
        session.commit()

    monkeypatch.setattr(api_main, "SessionLocal", session_factory)
    test_client = TestClient(api_main.app)
    token = create_access_token(user_id=1, username="test-admin", role="admin")
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    return test_client
```

- [ ] **Step 3: `tests/api/test_main.py`dan eski fixture va endi keraksiz importlarni olib tashlash**

Faylning boshidagi import blokini va fixture'ni (1—31-qatorlar) quyidagiga almashtiring:

```python
import threading
from datetime import datetime, timezone
from io import BytesIO

from openpyxl import load_workbook

import api.main as api_main
from db.models import ProductRow
```

(`import pytest`, `from fastapi.testclient import TestClient`, `from db.database import get_engine, get_session_factory, init_db` va eski `@pytest.fixture def client(...)` bloki olib tashlanadi — fixture endi `conftest.py`dan avtomatik keladi, faylning qolgan qismi — barcha testlar — o'zgarishsiz qoladi.)

- [ ] **Step 4: To'liq backend test to'plamini ishga tushirish**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: Barcha testlar (Task 1—3'dagilar + `tests/api/test_main.py`dagi ~30 ta mavjud test) PASS. Mavjud testlar o'zgarmagan bo'lsa-da, endi fixture avtomatik autentifikatsiya headerini qo'shgani uchun o'tadi.

- [ ] **Step 5: Himoyani tekshiruvchi qo'shimcha test yozish**

`tests/api/test_main.py` oxiriga qo'shing:

```python
def test_products_without_a_token_returns_401():
    from fastapi.testclient import TestClient

    unauthenticated_client = TestClient(api_main.app)
    response = unauthenticated_client.get("/products", params={"category": "mikroqarz"})
    assert response.status_code == 401
```

Run: `.venv/Scripts/python.exe -m pytest tests/api/test_main.py::test_products_without_a_token_returns_401 -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add api/main.py tests/api/conftest.py tests/api/test_main.py
git commit -m "feat: require authentication on every existing API endpoint"
```

---

## Task 5: Admin foydalanuvchilarni boshqarish endpointlari

**Files:**
- Modify: `api/main.py`
- Create: `tests/api/test_admin_users.py`

**Interfaces:**
- Consumes: `tests/api/conftest.py`'s `client` fixture (Task 4, `id=1`/`username="test-admin"`/`role="admin"`); `auth.dependencies.require_admin` (Task 2)
- Produces: `GET /admin/users`, `POST /admin/users`, `PATCH /admin/users/{id}`

- [ ] **Step 1: `Literal` importini qo'shish**

`api/main.py`ning import blokiga (`from datetime import datetime, timezone` qatoridan keyin) qo'shing:

```python
from typing import Literal
```

- [ ] **Step 2: Muvaffaqiyatsiz testlarni yozish**

`tests/api/test_admin_users.py`:

```python
from auth.security import create_access_token, verify_password
from db.models import UserRow

import api.main as api_main


def test_list_users_returns_the_seeded_admin(client):
    response = client.get("/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["username"] == "test-admin"
    assert data[0]["role"] == "admin"


def test_create_user_adds_a_new_user_that_then_appears_in_the_list(client):
    response = client.post("/admin/users", json={
        "username": "jane", "password": "jane-password", "role": "user",
    })
    assert response.status_code == 201
    assert response.json()["username"] == "jane"

    list_response = client.get("/admin/users")
    usernames = {u["username"] for u in list_response.json()}
    assert "jane" in usernames


def test_create_user_with_a_taken_username_returns_409(client):
    response = client.post("/admin/users", json={
        "username": "test-admin", "password": "whatever", "role": "user",
    })
    assert response.status_code == 409


def test_create_user_as_a_non_admin_returns_403(client):
    non_admin_token = create_access_token(user_id=99, username="regular", role="user")
    response = client.post(
        "/admin/users",
        json={"username": "new-user", "password": "pw", "role": "user"},
        headers={"Authorization": f"Bearer {non_admin_token}"},
    )
    assert response.status_code == 403


def test_update_user_changes_the_role(client):
    create_response = client.post("/admin/users", json={
        "username": "jane", "password": "jane-password", "role": "user",
    })
    user_id = create_response.json()["id"]

    response = client.patch(f"/admin/users/{user_id}", json={"role": "admin"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_update_user_without_a_password_keeps_the_old_password(client):
    create_response = client.post("/admin/users", json={
        "username": "jane", "password": "original-password", "role": "user",
    })
    user_id = create_response.json()["id"]

    response = client.patch(f"/admin/users/{user_id}", json={"username": "jane"})
    assert response.status_code == 200

    with api_main.SessionLocal() as session:
        user = session.get(UserRow, user_id)
        assert verify_password("original-password", user.password_hash) is True


def test_update_user_with_a_taken_username_returns_409(client):
    client.post("/admin/users", json={"username": "jane", "password": "pw", "role": "user"})
    create_response = client.post("/admin/users", json={"username": "bob", "password": "pw", "role": "user"})
    bob_id = create_response.json()["id"]

    response = client.patch(f"/admin/users/{bob_id}", json={"username": "jane"})
    assert response.status_code == 409


def test_admin_cannot_demote_themselves(client):
    response = client.patch("/admin/users/1", json={"role": "user"})
    assert response.status_code == 400
```

- [ ] **Step 3: Testni ishga tushirib, muvaffaqiyatsiz bo'lishini tekshirish**

Run: `.venv/Scripts/python.exe -m pytest tests/api/test_admin_users.py -v`
Expected: FAIL — `404` (`/admin/users` hali mavjud emas)

- [ ] **Step 4: Admin endpointlarini `api/main.py`ning oxiriga qo'shish**

```python
class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: Literal["admin", "user"]


class UpdateUserRequest(BaseModel):
    username: str | None = None
    password: str | None = None
    role: Literal["admin", "user"] | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: str


@app.get("/admin/users", response_model=list[UserResponse])
def list_users(_: AuthenticatedUser = Depends(require_admin)):
    with SessionLocal() as session:
        rows = session.execute(select(UserRow).order_by(UserRow.id)).scalars().all()
        return [
            UserResponse(id=row.id, username=row.username, role=row.role, created_at=row.created_at.isoformat())
            for row in rows
        ]


@app.post("/admin/users", response_model=UserResponse, status_code=201)
def create_user(request: CreateUserRequest, _: AuthenticatedUser = Depends(require_admin)):
    with SessionLocal() as session:
        existing = session.execute(select(UserRow).where(UserRow.username == request.username)).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Bu login band")
        new_user = UserRow(
            username=request.username,
            password_hash=hash_password(request.password),
            role=request.role,
            created_at=datetime.now(timezone.utc),
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return UserResponse(
            id=new_user.id, username=new_user.username, role=new_user.role,
            created_at=new_user.created_at.isoformat(),
        )


@app.patch("/admin/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, request: UpdateUserRequest, current_user: AuthenticatedUser = Depends(require_admin)):
    if user_id == current_user.id and request.role == "user":
        raise HTTPException(status_code=400, detail="O'z rolingizni o'zgartira olmaysiz")
    with SessionLocal() as session:
        user = session.get(UserRow, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
        if request.username is not None and request.username != user.username:
            existing = session.execute(
                select(UserRow).where(UserRow.username == request.username)
            ).scalar_one_or_none()
            if existing is not None:
                raise HTTPException(status_code=409, detail="Bu login band")
            user.username = request.username
        if request.password:
            user.password_hash = hash_password(request.password)
        if request.role is not None:
            user.role = request.role
        session.commit()
        session.refresh(user)
        return UserResponse(id=user.id, username=user.username, role=user.role, created_at=user.created_at.isoformat())
```

Va `require_admin`ni import blokiga qo'shing (`from auth.dependencies import AuthenticatedUser, get_current_user` qatorini yangilang):

```python
from auth.dependencies import AuthenticatedUser, get_current_user, require_admin
```

- [ ] **Step 5: Testlarni qayta ishga tushirib, o'tishini tekshirish**

Run: `.venv/Scripts/python.exe -m pytest tests/api/test_admin_users.py -v`
Expected: PASS (8 testlar)

- [ ] **Step 6: To'liq backend test to'plamini ishga tushirish**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: Barcha testlar PASS.

- [ ] **Step 7: Commit**

```bash
git add api/main.py tests/api/test_admin_users.py
git commit -m "feat: add admin user-management endpoints (list/create/update)"
```

---

## Task 6: Frontend — `lib/types.ts` va `lib/api.ts` auth/admin qatlami

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/api.test.ts`

**Interfaces:**
- Produces: `AuthUser`, `UserRole`, `LoginResponse`, `AdminUser`, `CreateUserRequest`, `UpdateUserRequest` (types); `getToken`, `setToken`, `clearToken`, `setUnauthorizedHandler`, `login`, `fetchCurrentUser`, `fetchUsers`, `createUser`, `updateUser`, `downloadFile` (functions); barcha mavjud `fetch*`/`trigger*` funksiyalar endi `Authorization` headerini avtomatik qo'shadi.

- [ ] **Step 1: `lib/types.ts`ga yangi tiplarni qo'shish**

Fayl oxiriga qo'shing:

```typescript
export type UserRole = 'admin' | 'user'

export interface AuthUser {
  username: string
  role: UserRole
}

export interface LoginResponse {
  access_token: string
  username: string
  role: UserRole
}

export interface AdminUser {
  id: number
  username: string
  role: UserRole
  created_at: string
}

export interface CreateUserRequest {
  username: string
  password: string
  role: UserRole
}

export interface UpdateUserRequest {
  username?: string
  password?: string
  role?: UserRole
}
```

- [ ] **Step 2: `lib/api.ts`ni to'liq yangilash**

Faylni quyidagi to'liq mazmun bilan almashtiring (mavjud funksiyalar saqlanadi, `apiFetch` orqali autentifikatsiya qo'shiladi, yangi funksiyalar qo'shiladi):

```typescript
import type {
  AdminUser,
  AuthUser,
  Category,
  CreateUserRequest,
  ExplainProductRequest,
  ExplainProductResponse,
  LoginResponse,
  Product,
  RecommendRequest,
  RecommendResponse,
  UnavailableBank,
  UpdateUserRequest,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const TOKEN_STORAGE_KEY = 'bozor-tahlili-token'

let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler
}

export function getToken(): string | null {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY)
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// Login'dan boshqa BARCHA so'rovlar shu orqali o'tadi — Authorization
// header'ni avtomatik qo'shadi va 401 kelsa (token yaroqsiz/muddati
// tugagan) tokenni tozalab, AuthContext'ga xabar beradi.
async function apiFetch(input: string | URL, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(input, {
    ...init,
    headers: { ...authHeaders(), ...init.headers },
  })
  if (response.status === 401) {
    clearToken()
    onUnauthorized?.()
  }
  return response
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!response.ok) {
    throw new Error("Login yoki parol noto'g'ri")
  }
  return response.json()
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const response = await apiFetch(`${API_BASE_URL}/auth/me`)
  if (!response.ok) {
    throw new Error(`Sessiyani tekshirib bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchUsers(): Promise<AdminUser[]> {
  const response = await apiFetch(`${API_BASE_URL}/admin/users`)
  if (!response.ok) {
    throw new Error(`Userlarni yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function createUser(request: CreateUserRequest): Promise<AdminUser> {
  const response = await apiFetch(`${API_BASE_URL}/admin/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (response.status === 409) {
    throw new Error('USERNAME_TAKEN')
  }
  if (!response.ok) {
    throw new Error(`Userni qo'shib bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function updateUser(id: number, request: UpdateUserRequest): Promise<AdminUser> {
  const response = await apiFetch(`${API_BASE_URL}/admin/users/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (response.status === 409) {
    throw new Error('USERNAME_TAKEN')
  }
  if (response.status === 400) {
    throw new Error('SELF_DEMOTE')
  }
  if (!response.ok) {
    throw new Error(`Userni yangilab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchCategories(): Promise<Category[]> {
  const response = await apiFetch(`${API_BASE_URL}/categories`)
  if (!response.ok) {
    throw new Error(`Kategoriyalarni yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchProducts(category: string): Promise<Product[]> {
  const url = new URL(`${API_BASE_URL}/products`)
  url.searchParams.set('category', category)
  const response = await apiFetch(url)
  if (!response.ok) {
    throw new Error(`Mahsulotlarni yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchUnavailableBanks(category: string): Promise<UnavailableBank[]> {
  const url = new URL(`${API_BASE_URL}/unavailable-banks`)
  url.searchParams.set('category', category)
  const response = await apiFetch(url)
  if (!response.ok) {
    throw new Error(`Mavjud bo'lmagan banklar ro'yxatini yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchRecommendation(request: RecommendRequest): Promise<RecommendResponse> {
  const response = await apiFetch(`${API_BASE_URL}/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    throw new Error(`AI tavsiyasini olib bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export function getExportExcelUrl(category: string, language: string): string {
  const url = new URL(`${API_BASE_URL}/export-excel`)
  url.searchParams.set('category', category)
  url.searchParams.set('language', language)
  return url.toString()
}

export function getExportAllExcelUrl(language: string): string {
  const url = new URL(`${API_BASE_URL}/export-excel-all`)
  url.searchParams.set('language', language)
  return url.toString()
}

// Export endpointlari endi autentifikatsiya talab qilgani uchun oddiy
// <a href> yetarli emas (brauzer navigatsiyasi Authorization header
// yubormaydi) — shu sabab fetch orqali blob sifatida yuklab olinadi va
// vaqtinchalik <a download> orqali saqlashga uzatiladi.
export async function downloadFile(url: string, filename: string): Promise<void> {
  const response = await apiFetch(url)
  if (!response.ok) {
    throw new Error(`Faylni yuklab olib bo'lmadi: ${response.status}`)
  }
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(objectUrl)
}

export type TriggerScrapeStatus = 'started' | 'already_running' | 'error'

export async function triggerScrapeRefresh(): Promise<TriggerScrapeStatus> {
  const response = await apiFetch(`${API_BASE_URL}/trigger-scrape`, { method: 'POST' })
  if (response.status === 409) return 'already_running'
  if (!response.ok) return 'error'
  return 'started'
}

export async function fetchProductExplanation(request: ExplainProductRequest): Promise<ExplainProductResponse> {
  const response = await apiFetch(`${API_BASE_URL}/explain-product`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    throw new Error(`AI izohini olib bo'lmadi: ${response.status}`)
  }
  return response.json()
}
```

- [ ] **Step 3: `api.test.ts`ga yangi testlarni qo'shish**

Fayl boshidagi `describe('api client', ...)` blokiga (mavjud testlardan keyin, yopilish qavsidan oldin) qo'shing. Avval faylning `import`larini yangilang:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  clearToken,
  createUser,
  downloadFile,
  fetchCategories,
  fetchCurrentUser,
  fetchProductExplanation,
  fetchProducts,
  fetchRecommendation,
  fetchUnavailableBanks,
  fetchUsers,
  getExportExcelUrl,
  getToken,
  login,
  setToken,
  setUnauthorizedHandler,
  updateUser,
} from './api'
```

Mavjud `beforeEach(() => { vi.restoreAllMocks() })`ni quyidagiga almashtiring:

```typescript
beforeEach(() => {
  vi.restoreAllMocks()
  window.localStorage.clear()
  setUnauthorizedHandler(null)
})
```

Faylning oxiriga (yopilish qavsidan oldin) qo'shing:

```typescript
  it('setToken/getToken/clearToken round-trip through localStorage', () => {
    expect(getToken()).toBeNull()
    setToken('abc123')
    expect(getToken()).toBe('abc123')
    clearToken()
    expect(getToken()).toBeNull()
  })

  it('fetchProducts sends the stored token as a Bearer header', async () => {
    setToken('my-token')
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] })
    vi.stubGlobal('fetch', fetchMock)

    await fetchProducts('mikroqarz')

    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers.Authorization).toBe('Bearer my-token')
  })

  it('clears the token and calls the unauthorized handler on a 401 response', async () => {
    setToken('stale-token')
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))

    await fetchProducts('mikroqarz').catch(() => {})

    expect(getToken()).toBeNull()
    expect(handler).toHaveBeenCalledOnce()
  })

  it('login posts credentials without requiring an existing token', async () => {
    const mockResponse = { access_token: 'new-token', username: 'admin', role: 'admin' }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => mockResponse })
    vi.stubGlobal('fetch', fetchMock)

    const result = await login('admin', 'secret')

    expect(result).toEqual(mockResponse)
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/auth/login')
    expect(JSON.parse(options.body)).toEqual({ username: 'admin', password: 'secret' })
  })

  it('login throws on a failed response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))
    await expect(login('admin', 'wrong')).rejects.toThrow("Login yoki parol noto'g'ri")
  })

  it('fetchCurrentUser returns the parsed user on success', async () => {
    const mockUser = { username: 'admin', role: 'admin' }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => mockUser }))
    const result = await fetchCurrentUser()
    expect(result).toEqual(mockUser)
  })

  it('fetchUsers returns the parsed list on success', async () => {
    const mockUsers = [{ id: 1, username: 'admin', role: 'admin', created_at: '2026-01-01T00:00:00Z' }]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => mockUsers }))
    const result = await fetchUsers()
    expect(result).toEqual(mockUsers)
  })

  it('createUser throws USERNAME_TAKEN on a 409 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 409 }))
    await expect(createUser({ username: 'jane', password: 'pw', role: 'user' })).rejects.toThrow('USERNAME_TAKEN')
  })

  it('updateUser throws SELF_DEMOTE on a 400 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 400 }))
    await expect(updateUser(1, { role: 'user' })).rejects.toThrow('SELF_DEMOTE')
  })

  it('downloadFile throws when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
    await expect(downloadFile('http://localhost:8000/export-excel', 'f.xlsx')).rejects.toThrow(
      "Faylni yuklab olib bo'lmadi: 500",
    )
  })
```

- [ ] **Step 4: Testlarni ishga tushirish**

Run: `npx vitest run src/lib/api.test.ts`
Expected: Barcha testlar (mavjud + yangi) PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/lib/api.test.ts
git commit -m "feat: add token storage, authenticated fetch wrapper, and auth/admin API calls"
```

---

## Task 7: `lib/AuthContext.tsx`

**Files:**
- Create: `frontend/src/lib/AuthContext.tsx`
- Create: `frontend/src/lib/AuthContext.test.tsx`

**Interfaces:**
- Consumes: `lib/api.ts`'s `login`, `fetchCurrentUser`, `getToken`, `setToken`, `clearToken`, `setUnauthorizedHandler` (Task 6); `lib/types.ts`'s `AuthUser` (Task 6)
- Produces: `AuthProvider` (component), `useAuth(): { user: AuthUser | null; isLoading: boolean; login(username, password): Promise<void>; logout(): void }`

- [ ] **Step 1: Muvaffaqiyatsiz testni yozish**

`frontend/src/lib/AuthContext.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AuthProvider, useAuth } from './AuthContext'
import * as api from './api'

vi.mock('./api', () => ({
  login: vi.fn(),
  fetchCurrentUser: vi.fn(),
  getToken: vi.fn(),
  setToken: vi.fn(),
  clearToken: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
}))

const mockedApi = vi.mocked(api)

function TestConsumer() {
  const { user, isLoading, login, logout } = useAuth()
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="user">{user ? `${user.username}:${user.role}` : 'none'}</span>
      <button onClick={() => login('admin', 'secret')}>do-login</button>
      <button onClick={logout}>do-logout</button>
    </div>
  )
}

function renderWithAuth() {
  return render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>,
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('starts with no user and isLoading=false when there is no stored token', async () => {
    mockedApi.getToken.mockReturnValue(null)
    renderWithAuth()

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('user')).toHaveTextContent('none')
  })

  it('restores the session from /auth/me when a token is already stored', async () => {
    mockedApi.getToken.mockReturnValue('stored-token')
    mockedApi.fetchCurrentUser.mockResolvedValue({ username: 'admin', role: 'admin' })
    renderWithAuth()

    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('admin:admin'))
  })

  it('clears the token and stays logged out when /auth/me fails', async () => {
    mockedApi.getToken.mockReturnValue('stale-token')
    mockedApi.fetchCurrentUser.mockRejectedValue(new Error('unauthorized'))
    renderWithAuth()

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('user')).toHaveTextContent('none')
    expect(mockedApi.clearToken).toHaveBeenCalled()
  })

  it('login stores the token and sets the user', async () => {
    mockedApi.getToken.mockReturnValue(null)
    mockedApi.login.mockResolvedValue({ access_token: 'new-token', username: 'admin', role: 'admin' })
    renderWithAuth()
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))

    await userEvent.click(screen.getByText('do-login'))

    expect(mockedApi.setToken).toHaveBeenCalledWith('new-token')
    expect(screen.getByTestId('user')).toHaveTextContent('admin:admin')
  })

  it('logout clears the token and the user', async () => {
    mockedApi.getToken.mockReturnValue('stored-token')
    mockedApi.fetchCurrentUser.mockResolvedValue({ username: 'admin', role: 'admin' })
    renderWithAuth()
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('admin:admin'))

    await userEvent.click(screen.getByText('do-logout'))

    expect(mockedApi.clearToken).toHaveBeenCalled()
    expect(screen.getByTestId('user')).toHaveTextContent('none')
  })
})
```

- [ ] **Step 2: Testni ishga tushirib, muvaffaqiyatsiz bo'lishini tekshirish**

Run: `npx vitest run src/lib/AuthContext.test.tsx`
Expected: FAIL — `Failed to resolve import "./AuthContext"`

- [ ] **Step 3: `lib/AuthContext.tsx`ni yozish**

```tsx
import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import {
  clearToken,
  fetchCurrentUser,
  getToken,
  login as loginRequest,
  setToken,
  setUnauthorizedHandler,
} from './api'
import type { AuthUser } from './types'

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null))
    return () => setUnauthorizedHandler(null)
  }, [])

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setIsLoading(false)
      return
    }
    fetchCurrentUser()
      .then(setUser)
      .catch(() => {
        clearToken()
        setUser(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  async function login(username: string, password: string) {
    const response = await loginRequest(username, password)
    setToken(response.access_token)
    setUser({ username: response.username, role: response.role })
  }

  function logout() {
    clearToken()
    setUser(null)
  }

  const value: AuthContextValue = { user, isLoading, login, logout }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
```

- [ ] **Step 4: Testlarni qayta ishga tushirib, o'tishini tekshirish**

Run: `npx vitest run src/lib/AuthContext.test.tsx`
Expected: PASS (5 testlar)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/AuthContext.tsx frontend/src/lib/AuthContext.test.tsx
git commit -m "feat: add AuthContext for session state management"
```

---

## Task 8: `ExportMenu.tsx`ni autentifikatsiyalangan yuklab olishga o'tkazish

**Files:**
- Modify: `frontend/src/components/ExportMenu.tsx`
- Modify: `frontend/src/components/ExportMenu.test.tsx`
- Modify: `frontend/src/styles/tokens.css`

**Interfaces:**
- Consumes: `lib/api.ts`'s `downloadFile` (Task 6)

**Nima uchun kerak:** `/export-excel` va `/export-excel-all` endi (Task 4) autentifikatsiya talab qiladi, lekin oddiy `<a href>` brauzer navigatsiyasi `Authorization` header yubormaydi — shu sabab bu ikki havola `fetch`+blob orqali yuklab olishga o'tkaziladi.

- [ ] **Step 1: `.export-menu-item` CSS klassini `<button>` uchun ham ishlaydigan qilish**

`frontend/src/styles/tokens.css`dagi `.export-menu-item` qoidasini toping va quyidagicha kengaytiring:

```css
.export-menu-item {
  padding: 9px 12px;
  border-radius: 8px;
  color: var(--ink);
  font-size: 13px;
  text-decoration: none;
  cursor: pointer;
  border: none;
  background: transparent;
  font-family: var(--font);
  width: 100%;
  text-align: left;
}
```

- [ ] **Step 2: `ExportMenu.tsx`ni yangilash**

Faylni to'liq quyidagicha almashtiring:

```tsx
import { useEffect, useRef, useState } from 'react'
import { downloadFile, getExportAllExcelUrl, getExportExcelUrl } from '../lib/api'
import { useLanguage } from '../lib/LanguageContext'
import { DownloadIcon } from './icons'

interface ExportMenuProps {
  category: string | null
}

export function ExportMenu({ category }: ExportMenuProps) {
  const { lang, t } = useLanguage()
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  if (!category) return null

  async function handleExportCurrent() {
    setIsOpen(false)
    await downloadFile(getExportExcelUrl(category as string, lang), `${category}.xlsx`)
  }

  async function handleExportAll() {
    setIsOpen(false)
    await downloadFile(getExportAllExcelUrl(lang), 'bozor-tahlili-barcha-kategoriyalar.xlsx')
  }

  return (
    <div className="export-menu" ref={containerRef}>
      <button type="button" className="export-btn" onClick={() => setIsOpen((prev) => !prev)}>
        <DownloadIcon />
        {t('exportButton')}
        <span className={isOpen ? 'export-btn-caret export-btn-caret-open' : 'export-btn-caret'} aria-hidden="true">
          ▾
        </span>
      </button>
      {isOpen && (
        <div className="export-menu-panel" role="menu">
          <button type="button" className="export-menu-item" role="menuitem" onClick={handleExportCurrent}>
            {t('exportCurrentPage')}
          </button>
          <button type="button" className="export-menu-item" role="menuitem" onClick={handleExportAll}>
            {t('exportAllCategories')}
          </button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: `ExportMenu.test.tsx`ni yangilash**

Faylni to'liq quyidagicha almashtiring:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { ExportMenu } from './ExportMenu'
import { LanguageProvider } from '../lib/LanguageContext'
import { downloadFile } from '../lib/api'

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual<typeof import('../lib/api')>('../lib/api')
  return { ...actual, downloadFile: vi.fn() }
})

const mockedDownloadFile = vi.mocked(downloadFile)

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('ExportMenu', () => {
  it('renders nothing when there is no active category', () => {
    renderWithLanguage(<ExportMenu category={null} />)
    expect(screen.queryByText("Excel'ga yuklash")).not.toBeInTheDocument()
  })

  it('shows the toggle button but keeps the menu closed until clicked', () => {
    renderWithLanguage(<ExportMenu category="avtokredit" />)
    expect(screen.getByText("Excel'ga yuklash")).toBeInTheDocument()
    expect(screen.queryByText('Joriy sahifani yuklash')).not.toBeInTheDocument()
  })

  it('downloads the current category as an authenticated file when clicked', async () => {
    renderWithLanguage(<ExportMenu category="avtokredit" />)

    await userEvent.click(screen.getByText("Excel'ga yuklash"))
    await userEvent.click(screen.getByText('Joriy sahifani yuklash'))

    expect(mockedDownloadFile).toHaveBeenCalledWith(
      'http://localhost:8000/export-excel?category=avtokredit&language=uz',
      'avtokredit.xlsx',
    )
  })

  it('downloads all categories as an authenticated file when clicked', async () => {
    renderWithLanguage(<ExportMenu category="avtokredit" />)

    await userEvent.click(screen.getByText("Excel'ga yuklash"))
    await userEvent.click(screen.getByText('Barcha kategoriyalarni yuklash'))

    expect(mockedDownloadFile).toHaveBeenCalledWith(
      'http://localhost:8000/export-excel-all?language=uz',
      'bozor-tahlili-barcha-kategoriyalar.xlsx',
    )
  })

  it('closes the menu when a click lands outside it', async () => {
    renderWithLanguage(
      <div>
        <ExportMenu category="avtokredit" />
        <button type="button">outside</button>
      </div>,
    )

    await userEvent.click(screen.getByText("Excel'ga yuklash"))
    expect(screen.getByText('Joriy sahifani yuklash')).toBeInTheDocument()

    await userEvent.click(screen.getByText('outside'))
    expect(screen.queryByText('Joriy sahifani yuklash')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 4: Testlarni ishga tushirish**

Run: `npx vitest run src/components/ExportMenu.test.tsx`
Expected: PASS (5 testlar)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ExportMenu.tsx frontend/src/components/ExportMenu.test.tsx frontend/src/styles/tokens.css
git commit -m "fix: switch Excel export to authenticated blob download"
```

---

## Task 9: `LoginPage.tsx` va i18n matnlari

**Files:**
- Create: `frontend/src/components/LoginPage.tsx`
- Create: `frontend/src/components/LoginPage.test.tsx`
- Modify: `frontend/src/lib/i18n.ts`
- Modify: `frontend/src/lib/bankLogos.ts`
- Modify: `frontend/src/styles/tokens.css`

**Interfaces:**
- Consumes: `lib/AuthContext.tsx`'s `useAuth` (Task 7); `lib/bankLogos.ts`'s `BANK_LOGO_LIST` (yangi, shu taskda qo'shiladi)
- Produces: `LoginPage` component; `UI_TEXT`ga auth+admin uchun yangi kalitlar (keyingi Task 10—12 ham shu kalitlardan foydalanadi)

- [ ] **Step 1: `lib/i18n.ts`ga yangi kalitlarni qo'shish**

`UI_TEXT.uz` obyektining oxiriga (`closeLabel` qatoridan keyin, yopilish qavsidan oldin) qo'shing:

```typescript
    dashboardButton: 'Dashboard',
    logoutButton: 'Chiqish',
    authTitle: 'Tizimga kirish',
    authSubtitle: 'Davom etish uchun login va parolingizni kiriting',
    authUsernameLabel: 'Login',
    authPasswordLabel: 'Parol',
    authSubmitButton: 'Kirish',
    authError: "Login yoki parol noto'g'ri",
    authTagline: 'Raqobatchi banklar tahlili — bitta oynada',
    adminPanelTitle: 'Foydalanuvchilarni boshqarish',
    adminBackButton: 'Bosh sahifaga qaytish',
    adminAddUserButton: "Yangi user qo'shish",
    adminUsernameLabel: 'Login',
    adminRoleLabel: 'Rol',
    adminColCreatedAt: "Qo'shilgan sana",
    adminEditButton: 'Tahrirlash',
    adminEditUserTitle: 'Userni tahrirlash',
    adminAddUserTitle: 'Yangi user',
    adminPasswordLabel: 'Parol',
    adminPasswordLabelOptional: 'Yangi parol (ixtiyoriy)',
    adminPasswordPlaceholder: "O'zgartirmaslik uchun bo'sh qoldiring",
    adminRoleUser: 'Foydalanuvchi',
    adminRoleAdmin: 'Administrator',
    adminSaveButton: 'Saqlash',
    adminUsernameTaken: 'Bu login band',
    adminSelfDemote: "O'z rolingizni o'zgartira olmaysiz",
    adminSaveFailed: "Saqlab bo'lmadi. Qayta urinib ko'ring.",
    adminLoadFailed: "Userlarni yuklab bo'lmadi",
```

`UI_TEXT.ru` obyektining oxiriga (`closeLabel` qatoridan keyin) qo'shing:

```typescript
    dashboardButton: 'Дашборд',
    logoutButton: 'Выйти',
    authTitle: 'Вход в систему',
    authSubtitle: 'Введите логин и пароль, чтобы продолжить',
    authUsernameLabel: 'Логин',
    authPasswordLabel: 'Пароль',
    authSubmitButton: 'Войти',
    authError: 'Неверный логин или пароль',
    authTagline: 'Анализ банков-конкурентов — в одном окне',
    adminPanelTitle: 'Управление пользователями',
    adminBackButton: 'Вернуться на главную',
    adminAddUserButton: 'Добавить пользователя',
    adminUsernameLabel: 'Логин',
    adminRoleLabel: 'Роль',
    adminColCreatedAt: 'Дата добавления',
    adminEditButton: 'Редактировать',
    adminEditUserTitle: 'Редактирование пользователя',
    adminAddUserTitle: 'Новый пользователь',
    adminPasswordLabel: 'Пароль',
    adminPasswordLabelOptional: 'Новый пароль (необязательно)',
    adminPasswordPlaceholder: 'Оставьте пустым, чтобы не менять',
    adminRoleUser: 'Пользователь',
    adminRoleAdmin: 'Администратор',
    adminSaveButton: 'Сохранить',
    adminUsernameTaken: 'Этот логин уже занят',
    adminSelfDemote: 'Вы не можете изменить свою роль',
    adminSaveFailed: 'Не удалось сохранить. Попробуйте ещё раз.',
    adminLoadFailed: 'Не удалось загрузить пользователей',
```

- [ ] **Step 2: `lib/bankLogos.ts`ga `BANK_LOGO_LIST`ni qo'shish**

Fayl oxiriga (`getBankLogo` funksiyasidan keyin) qo'shing:

```typescript
export const BANK_LOGO_LIST: { key: string; src: string }[] = Object.entries(BANK_LOGOS).map(([key, src]) => ({
  key,
  src,
}))
```

- [ ] **Step 3: Auth sahifasi uchun CSS qo'shish**

`frontend/src/styles/tokens.css` oxiriga qo'shing:

```css
/* ---------- Auth / Login ---------- */

.auth-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  color: var(--ink-soft);
  font-size: 14px;
}

.auth-page {
  display: flex;
  min-height: 100vh;
  background: var(--paper);
}

.auth-showcase {
  flex: 1 1 55%;
  background: var(--house);
  color: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 48px;
  overflow: hidden;
}

.auth-showcase-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.auth-showcase-logo-icon {
  height: 36px;
  width: auto;
}

.auth-showcase-wordmark {
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.auth-showcase-tagline {
  max-width: 420px;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.35;
  margin: 0;
}

.auth-showcase-logos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
  gap: 12px;
  max-width: 520px;
}

.auth-showcase-logo-chip {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 56px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  padding: 10px;
  animation: auth-chip-in 480ms cubic-bezier(0.16, 1, 0.3, 1) backwards;
}

.auth-showcase-logo-chip img {
  max-height: 100%;
  max-width: 100%;
  object-fit: contain;
  filter: brightness(0) invert(1);
  opacity: 0.85;
}

@keyframes auth-chip-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .auth-showcase-logo-chip {
    animation: none;
  }
}

.auth-form-panel {
  flex: 1 1 45%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.auth-form-card {
  width: 100%;
  max-width: 360px;
}

.auth-form-card h1 {
  font-size: 22px;
  font-weight: 800;
  color: var(--ink);
  margin: 0 0 6px;
}

.auth-form-subtitle {
  font-size: 14px;
  color: var(--ink-soft);
  margin: 0 0 28px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.form-field label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

.form-field input,
.form-field select {
  padding: 11px 14px;
  border-radius: 8px;
  border: 1px solid var(--line-strong);
  font-size: 14px;
  font-family: var(--font);
  color: var(--ink);
  background: var(--paper);
}

.form-field input:focus-visible,
.form-field select:focus-visible {
  outline: 2px solid var(--house);
  outline-offset: 1px;
  border-color: var(--house);
}

.form-error {
  margin: 0 0 16px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--signal-soft);
  color: var(--negative);
  font-size: 13px;
}

.auth-form-submit {
  width: 100%;
  padding: 12px;
  border-radius: 999px;
  border: none;
  background: var(--house);
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.auth-form-submit:hover:not(:disabled) {
  background: #012544;
}

.auth-form-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 860px) {
  .auth-showcase {
    display: none;
  }
  .auth-form-panel {
    flex: 1 1 100%;
  }
}
```

- [ ] **Step 4: Muvaffaqiyatsiz testni yozish**

`frontend/src/components/LoginPage.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { LoginPage } from './LoginPage'
import { LanguageProvider } from '../lib/LanguageContext'
import { useAuth } from '../lib/AuthContext'

vi.mock('../lib/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockedUseAuth = vi.mocked(useAuth)

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('LoginPage', () => {
  it('calls login with the entered credentials on submit', async () => {
    const mockLogin = vi.fn().mockResolvedValue(undefined)
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login: mockLogin, logout: vi.fn() })
    renderWithLanguage(<LoginPage />)

    await userEvent.type(screen.getByLabelText('Login'), 'admin')
    await userEvent.type(screen.getByLabelText('Parol'), 'secret123')
    await userEvent.click(screen.getByRole('button', { name: 'Kirish' }))

    expect(mockLogin).toHaveBeenCalledWith('admin', 'secret123')
  })

  it('shows an error message when login fails', async () => {
    const mockLogin = vi.fn().mockRejectedValue(new Error("Login yoki parol noto'g'ri"))
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login: mockLogin, logout: vi.fn() })
    renderWithLanguage(<LoginPage />)

    await userEvent.type(screen.getByLabelText('Login'), 'admin')
    await userEvent.type(screen.getByLabelText('Parol'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: 'Kirish' }))

    expect(await screen.findByText("Login yoki parol noto'g'ri")).toBeInTheDocument()
  })
})
```

- [ ] **Step 5: Testni ishga tushirib, muvaffaqiyatsiz bo'lishini tekshirish**

Run: `npx vitest run src/components/LoginPage.test.tsx`
Expected: FAIL — `Failed to resolve import "./LoginPage"`

- [ ] **Step 6: `LoginPage.tsx`ni yozish**

```tsx
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../lib/AuthContext'
import { useLanguage } from '../lib/LanguageContext'
import { BANK_LOGO_LIST } from '../lib/bankLogos'
import logoIcon from '../assets/logo-icon.png'

export function LoginPage() {
  const { login } = useAuth()
  const { t } = useLanguage()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)
    try {
      await login(username, password)
    } catch {
      setError(t('authError'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-showcase">
        <div className="auth-showcase-brand">
          <img src={logoIcon} alt="" className="auth-showcase-logo-icon" />
          <span className="auth-showcase-wordmark">{t('brandName')}</span>
        </div>
        <p className="auth-showcase-tagline">{t('authTagline')}</p>
        <div className="auth-showcase-logos">
          {BANK_LOGO_LIST.map(({ key, src }, index) => (
            <div key={key} className="auth-showcase-logo-chip" style={{ animationDelay: `${index * 40}ms` }}>
              <img src={src} alt="" />
            </div>
          ))}
        </div>
      </div>
      <div className="auth-form-panel">
        <div className="auth-form-card">
          <h1>{t('authTitle')}</h1>
          <p className="auth-form-subtitle">{t('authSubtitle')}</p>
          <form onSubmit={handleSubmit}>
            <div className="form-field">
              <label htmlFor="login-username">{t('authUsernameLabel')}</label>
              <input
                id="login-username"
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div className="form-field">
              <label htmlFor="login-password">{t('authPasswordLabel')}</label>
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            {error && <p className="form-error">{error}</p>}
            <button type="submit" className="auth-form-submit" disabled={isSubmitting}>
              {t('authSubmitButton')}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Testlarni qayta ishga tushirib, o'tishini tekshirish**

Run: `npx vitest run src/components/LoginPage.test.tsx`
Expected: PASS (2 testlar)

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/LoginPage.tsx frontend/src/components/LoginPage.test.tsx frontend/src/lib/i18n.ts frontend/src/lib/bankLogos.ts frontend/src/styles/tokens.css
git commit -m "feat: add LoginPage with bank-logo showcase"
```

---

## Task 10: `UserFormModal.tsx`

**Files:**
- Create: `frontend/src/components/UserFormModal.tsx`
- Create: `frontend/src/components/UserFormModal.test.tsx`

**Interfaces:**
- Consumes: `lib/api.ts`'s `createUser`, `updateUser` (Task 6); `lib/types.ts`'s `AdminUser`, `UserRole` (Task 6); `lib/i18n.ts` kalitlar (Task 9); mavjud `.modal-overlay`/`.modal-card`/`.modal-title`/`.modal-actions`/`.modal-btn*` CSS (`RefreshDataButton.tsx`da ishlatilgan)
- Produces: `UserFormModal({ user, onClose, onSaved })` — `user === null` bo'lsa "qo'shish" rejimi, aks holda "tahrirlash"

- [ ] **Step 1: Muvaffaqiyatsiz testni yozish**

`frontend/src/components/UserFormModal.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { UserFormModal } from './UserFormModal'
import { LanguageProvider } from '../lib/LanguageContext'
import { createUser, updateUser } from '../lib/api'

vi.mock('../lib/api', () => ({
  createUser: vi.fn(),
  updateUser: vi.fn(),
}))

const mockedCreateUser = vi.mocked(createUser)
const mockedUpdateUser = vi.mocked(updateUser)

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('UserFormModal', () => {
  it('creates a new user with the entered fields', async () => {
    const savedUser = { id: 2, username: 'jane', role: 'user' as const, created_at: '2026-01-01T00:00:00Z' }
    mockedCreateUser.mockResolvedValue(savedUser)
    const onSaved = vi.fn()
    renderWithLanguage(<UserFormModal user={null} onClose={vi.fn()} onSaved={onSaved} />)

    await userEvent.type(screen.getByLabelText('Login'), 'jane')
    await userEvent.type(screen.getByLabelText('Parol'), 'jane-password')
    await userEvent.click(screen.getByRole('button', { name: 'Saqlash' }))

    expect(mockedCreateUser).toHaveBeenCalledWith({ username: 'jane', password: 'jane-password', role: 'user' })
    expect(onSaved).toHaveBeenCalledWith(savedUser)
  })

  it('updates an existing user, omitting the password when left blank', async () => {
    const existingUser = { id: 5, username: 'bob', role: 'user' as const, created_at: '2026-01-01T00:00:00Z' }
    const savedUser = { ...existingUser, role: 'admin' as const }
    mockedUpdateUser.mockResolvedValue(savedUser)
    const onSaved = vi.fn()
    renderWithLanguage(<UserFormModal user={existingUser} onClose={vi.fn()} onSaved={onSaved} />)

    await userEvent.selectOptions(screen.getByLabelText('Rol'), 'admin')
    await userEvent.click(screen.getByRole('button', { name: 'Saqlash' }))

    expect(mockedUpdateUser).toHaveBeenCalledWith(5, { username: 'bob', role: 'admin' })
    expect(onSaved).toHaveBeenCalledWith(savedUser)
  })

  it('shows a "username taken" error when the API rejects with a conflict', async () => {
    mockedCreateUser.mockRejectedValue(new Error('USERNAME_TAKEN'))
    renderWithLanguage(<UserFormModal user={null} onClose={vi.fn()} onSaved={vi.fn()} />)

    await userEvent.type(screen.getByLabelText('Login'), 'jane')
    await userEvent.type(screen.getByLabelText('Parol'), 'pw')
    await userEvent.click(screen.getByRole('button', { name: 'Saqlash' }))

    expect(await screen.findByText('Bu login band')).toBeInTheDocument()
  })

  it('closes when the overlay is clicked', async () => {
    const onClose = vi.fn()
    renderWithLanguage(<UserFormModal user={null} onClose={onClose} onSaved={vi.fn()} />)

    await userEvent.click(screen.getByRole('dialog').parentElement as HTMLElement)

    expect(onClose).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Testni ishga tushirib, muvaffaqiyatsiz bo'lishini tekshirish**

Run: `npx vitest run src/components/UserFormModal.test.tsx`
Expected: FAIL — `Failed to resolve import "./UserFormModal"`

- [ ] **Step 3: `UserFormModal.tsx`ni yozish**

```tsx
import { useState } from 'react'
import type { FormEvent } from 'react'
import { createUser, updateUser } from '../lib/api'
import { useLanguage } from '../lib/LanguageContext'
import type { AdminUser, UserRole } from '../lib/types'

interface UserFormModalProps {
  user: AdminUser | null
  onClose: () => void
  onSaved: (user: AdminUser) => void
}

export function UserFormModal({ user, onClose, onSaved }: UserFormModalProps) {
  const { t } = useLanguage()
  const isEditing = user !== null
  const [username, setUsername] = useState(user?.username ?? '')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>(user?.role ?? 'user')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)
    try {
      const saved =
        isEditing && user
          ? await updateUser(user.id, { username, role, ...(password ? { password } : {}) })
          : await createUser({ username, password, role })
      onSaved(saved)
    } catch (err) {
      if (err instanceof Error && err.message === 'USERNAME_TAKEN') {
        setError(t('adminUsernameTaken'))
      } else if (err instanceof Error && err.message === 'SELF_DEMOTE') {
        setError(t('adminSelfDemote'))
      } else {
        setError(t('adminSaveFailed'))
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="user-form-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="user-form-title" className="modal-title">
          {isEditing ? t('adminEditUserTitle') : t('adminAddUserTitle')}
        </h2>
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="user-form-username">{t('adminUsernameLabel')}</label>
            <input
              id="user-form-username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </div>
          <div className="form-field">
            <label htmlFor="user-form-password">
              {isEditing ? t('adminPasswordLabelOptional') : t('adminPasswordLabel')}
            </label>
            <input
              id="user-form-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={isEditing ? t('adminPasswordPlaceholder') : undefined}
              required={!isEditing}
            />
          </div>
          <div className="form-field">
            <label htmlFor="user-form-role">{t('adminRoleLabel')}</label>
            <select id="user-form-role" value={role} onChange={(event) => setRole(event.target.value as UserRole)}>
              <option value="user">{t('adminRoleUser')}</option>
              <option value="admin">{t('adminRoleAdmin')}</option>
            </select>
          </div>
          {error && <p className="form-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="modal-btn modal-btn-secondary" onClick={onClose}>
              {t('refreshConfirmCancel')}
            </button>
            <button type="submit" className="modal-btn modal-btn-primary" disabled={isSubmitting}>
              {t('adminSaveButton')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Testlarni qayta ishga tushirib, o'tishini tekshirish**

Run: `npx vitest run src/components/UserFormModal.test.tsx`
Expected: PASS (4 testlar)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/UserFormModal.tsx frontend/src/components/UserFormModal.test.tsx
git commit -m "feat: add UserFormModal for adding and editing users"
```

---

## Task 11: `AdminPanel.tsx`

**Files:**
- Create: `frontend/src/components/AdminPanel.tsx`
- Create: `frontend/src/components/AdminPanel.test.tsx`
- Modify: `frontend/src/styles/tokens.css`

**Interfaces:**
- Consumes: `lib/api.ts`'s `fetchUsers` (Task 6); `components/UserFormModal.tsx` (Task 10); `lib/i18n.ts` kalitlar (Task 9)
- Produces: `AdminPanel({ onBack })`

- [ ] **Step 1: Admin panel uchun CSS qo'shish**

`frontend/src/styles/tokens.css` oxiriga qo'shing:

```css
.admin-panel {
  padding: 32px;
  max-width: 960px;
  margin: 0 auto;
}

.admin-panel-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  margin-bottom: 20px;
}

.admin-panel-back:hover {
  color: var(--house);
}

.admin-panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.admin-panel-title-row h1 {
  font-size: 22px;
  font-weight: 800;
  margin: 0;
  color: var(--ink);
}

.admin-add-btn {
  padding: 9px 18px;
  border-radius: 999px;
  border: none;
  background: var(--house);
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.admin-add-btn:hover {
  background: #012544;
}

.admin-users-table {
  width: 100%;
  border-collapse: collapse;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}

.admin-users-table th,
.admin-users-table td {
  text-align: left;
  padding: 12px 16px;
  font-size: 13px;
  border-bottom: 1px solid var(--line);
}

.admin-users-table th {
  background: var(--paper-sunk);
  color: var(--ink-soft);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-size: 11px;
}

.admin-role-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.admin-role-badge-admin {
  background: var(--house-soft);
  color: var(--house);
}

.admin-role-badge-user {
  background: var(--paper-sunk);
  color: var(--ink-soft);
}

.admin-edit-btn {
  padding: 5px 14px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  background: var(--paper);
  color: var(--ink);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.admin-edit-btn:hover {
  border-color: var(--house);
  color: var(--house);
}
```

- [ ] **Step 2: Muvaffaqiyatsiz testni yozish**

`frontend/src/components/AdminPanel.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { AdminPanel } from './AdminPanel'
import { LanguageProvider } from '../lib/LanguageContext'
import { fetchUsers } from '../lib/api'

vi.mock('../lib/api', () => ({
  fetchUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
}))

const mockedFetchUsers = vi.mocked(fetchUsers)

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('AdminPanel', () => {
  it('lists the users returned by the API', async () => {
    mockedFetchUsers.mockResolvedValue([
      { id: 1, username: 'admin1', role: 'admin', created_at: '2026-01-01T00:00:00Z' },
      { id: 2, username: 'jane', role: 'user', created_at: '2026-02-01T00:00:00Z' },
    ])
    renderWithLanguage(<AdminPanel onBack={vi.fn()} />)

    expect(await screen.findByText('admin1')).toBeInTheDocument()
    expect(screen.getByText('jane')).toBeInTheDocument()
  })

  it('calls onBack when the back button is clicked', async () => {
    mockedFetchUsers.mockResolvedValue([])
    const onBack = vi.fn()
    renderWithLanguage(<AdminPanel onBack={onBack} />)

    await userEvent.click(screen.getByText(/Bosh sahifaga qaytish/))
    expect(onBack).toHaveBeenCalled()
  })

  it('opens the add-user modal when the add button is clicked', async () => {
    mockedFetchUsers.mockResolvedValue([])
    renderWithLanguage(<AdminPanel onBack={vi.fn()} />)

    await userEvent.click(await screen.findByText("Yangi user qo'shish"))

    expect(screen.getByText('Yangi user')).toBeInTheDocument()
  })

  it('opens the edit modal pre-filled for an existing user', async () => {
    mockedFetchUsers.mockResolvedValue([
      { id: 3, username: 'bob', role: 'user', created_at: '2026-01-01T00:00:00Z' },
    ])
    renderWithLanguage(<AdminPanel onBack={vi.fn()} />)

    await userEvent.click(await screen.findByText('Tahrirlash'))

    expect(screen.getByText('Userni tahrirlash')).toBeInTheDocument()
    expect(screen.getByLabelText('Login')).toHaveValue('bob')
  })
})
```

- [ ] **Step 3: Testni ishga tushirib, muvaffaqiyatsiz bo'lishini tekshirish**

Run: `npx vitest run src/components/AdminPanel.test.tsx`
Expected: FAIL — `Failed to resolve import "./AdminPanel"`

- [ ] **Step 4: `AdminPanel.tsx`ni yozish**

```tsx
import { useEffect, useState } from 'react'
import { fetchUsers } from '../lib/api'
import { useLanguage } from '../lib/LanguageContext'
import { UserFormModal } from './UserFormModal'
import type { AdminUser } from '../lib/types'

interface AdminPanelProps {
  onBack: () => void
}

export function AdminPanel({ onBack }: AdminPanelProps) {
  const { lang, t } = useLanguage()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingUser, setEditingUser] = useState<AdminUser | 'new' | null>(null)

  useEffect(() => {
    loadUsers()
  }, [])

  async function loadUsers() {
    setIsLoading(true)
    try {
      const data = await fetchUsers()
      setUsers(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('adminLoadFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  function handleSaved(saved: AdminUser) {
    setUsers((prev) => {
      const exists = prev.some((u) => u.id === saved.id)
      return exists ? prev.map((u) => (u.id === saved.id ? saved : u)) : [...prev, saved]
    })
    setEditingUser(null)
  }

  function formatCreatedAt(iso: string): string {
    const locale = lang === 'ru' ? 'ru-RU' : 'uz-UZ'
    return new Date(iso).toLocaleDateString(locale, { day: '2-digit', month: '2-digit', year: 'numeric' })
  }

  return (
    <div className="admin-panel">
      <button type="button" className="admin-panel-back" onClick={onBack}>
        ← {t('adminBackButton')}
      </button>
      <div className="admin-panel-title-row">
        <h1>{t('adminPanelTitle')}</h1>
        <button type="button" className="admin-add-btn" onClick={() => setEditingUser('new')}>
          {t('adminAddUserButton')}
        </button>
      </div>

      {error && <p className="error-state">{error}</p>}

      {!isLoading && (
        <table className="admin-users-table">
          <thead>
            <tr>
              <th>{t('adminUsernameLabel')}</th>
              <th>{t('adminRoleLabel')}</th>
              <th>{t('adminColCreatedAt')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.username}</td>
                <td>
                  <span className={`admin-role-badge admin-role-badge-${user.role}`}>
                    {user.role === 'admin' ? t('adminRoleAdmin') : t('adminRoleUser')}
                  </span>
                </td>
                <td>{formatCreatedAt(user.created_at)}</td>
                <td>
                  <button type="button" className="admin-edit-btn" onClick={() => setEditingUser(user)}>
                    {t('adminEditButton')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {editingUser && (
        <UserFormModal
          user={editingUser === 'new' ? null : editingUser}
          onClose={() => setEditingUser(null)}
          onSaved={handleSaved}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 5: Testlarni qayta ishga tushirib, o'tishini tekshirish**

Run: `npx vitest run src/components/AdminPanel.test.tsx`
Expected: PASS (4 testlar)

- [ ] **Step 6: Butun frontend test to'plamini ishga tushirish**

Run: `npx vitest run`
Expected: Barcha testlar PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/AdminPanel.tsx frontend/src/components/AdminPanel.test.tsx frontend/src/styles/tokens.css
git commit -m "feat: add AdminPanel for listing, adding, and editing users"
```

---

## Task 12: Auth'ni `main.tsx`/`App.tsx`ga ulash

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/icons.tsx`
- Modify: `frontend/src/styles/tokens.css`
- Create: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: `lib/AuthContext.tsx`'s `AuthProvider`, `useAuth` (Task 7); `components/LoginPage.tsx` (Task 9); `components/AdminPanel.tsx` (Task 11)
- Produces: to'liq gate qilingan `App` — `user == null` bo'lsa `LoginPage`, `view === 'admin'` bo'lsa `AdminPanel`, aks holda mavjud ilova + header'da username/dashboard/logout

- [ ] **Step 1: `icons.tsx`ga yangi ikonalarni qo'shish**

`frontend/src/components/icons.tsx` oxiriga qo'shing:

```tsx
export function LogoutIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M6 2H3.5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1H6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10.5 11 14 8l-3.5-3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 8H6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

export function DashboardIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.4" />
      <rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.4" />
      <rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.4" />
      <rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  )
}
```

- [ ] **Step 2: Header uchun CSS qo'shish**

`frontend/src/styles/tokens.css` oxiriga qo'shing:

```css
.app-topbar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 10px;
  border-left: 1px solid var(--line);
}

.app-topbar-username {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-soft);
}

.dashboard-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: 999px;
  border: 1px solid var(--house);
  background: var(--house);
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.dashboard-btn:hover {
  background: #012544;
}

.logout-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  background: var(--paper);
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.logout-btn:hover {
  border-color: var(--negative);
  color: var(--negative);
}
```

- [ ] **Step 3: `main.tsx`ga `AuthProvider`ni ulash**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { LanguageProvider } from './lib/LanguageContext'
import { AuthProvider } from './lib/AuthContext'
import './styles/tokens.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LanguageProvider>
      <AuthProvider>
        <App />
      </AuthProvider>
    </LanguageProvider>
  </StrictMode>,
)
```

- [ ] **Step 4: `App.tsx`ni yangilash**

Import blokini yangilang (fayl boshiga qo'shing):

```tsx
import { useAuth } from './lib/AuthContext'
import { LoginPage } from './components/LoginPage'
import { AdminPanel } from './components/AdminPanel'
import { DashboardIcon, LogoutIcon } from './components/icons'
```

`export function App() {` funksiyasining boshiga (`const { lang, t } = useLanguage()` qatoridan OLDIN) qo'shing:

```tsx
  const { user, isLoading: isAuthLoading, logout } = useAuth()
  const [view, setView] = useState<'app' | 'admin'>('app')
```

Mavjud ikkita `useEffect`ni auth-ogohlantiruvchi qilib yangilang — birinchisi:

```tsx
  useEffect(() => {
    if (!user) return
    fetchCategories()
      .then((data) => {
        setCategories(data)
        if (data.length > 0) {
          setActiveCategory(data[0].key)
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Kategoriyalarni yuklab bo'lmadi")
      })
  }, [user])
```

ikkinchisi:

```tsx
  useEffect(() => {
    if (!user || !activeCategory) return
    let ignore = false

    async function loadProducts() {
      setIsLoading(true)
      try {
        const [data, unavailable] = await Promise.all([
          fetchProducts(activeCategory as string),
          fetchUnavailableBanks(activeCategory as string),
        ])
        if (ignore) return
        setProducts(data)
        setUnavailableBanks(unavailable)
        setError(null)
      } catch (err) {
        if (!ignore) setError(err instanceof Error ? err.message : "Mahsulotlarni yuklab bo'lmadi")
      } finally {
        if (!ignore) setIsLoading(false)
      }
    }

    loadProducts()
    return () => {
      ignore = true
    }
  }, [user, activeCategory])
```

`return (` qatoridan OLDIN (barcha hook va hisoblangan qiymatlardan keyin) qo'shing:

```tsx
  if (isAuthLoading) {
    return <div className="auth-loading">{t('loadingLabel')}</div>
  }

  if (!user) {
    return <LoginPage />
  }

  if (view === 'admin' && user.role === 'admin') {
    return <AdminPanel onBack={() => setView('app')} />
  }
```

Header ichidagi `<div className="app-topbar-actions">` blokini yangilang:

```tsx
        <div className="app-topbar-actions">
          <RefreshDataButton />
          <ExportMenu category={activeCategory} />
          <LanguageDropdown />
          <div className="app-topbar-user">
            {user.role === 'admin' && (
              <button type="button" className="dashboard-btn" onClick={() => setView('admin')}>
                <DashboardIcon />
                {t('dashboardButton')}
              </button>
            )}
            <span className="app-topbar-username">{user.username}</span>
            <button type="button" className="logout-btn" onClick={logout}>
              <LogoutIcon />
              {t('logoutButton')}
            </button>
          </div>
        </div>
```

- [ ] **Step 5: Muvaffaqiyatsiz testni yozish**

`frontend/src/App.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { App } from './App'
import { LanguageProvider } from './lib/LanguageContext'
import { useAuth } from './lib/AuthContext'

vi.mock('./lib/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('./lib/api', () => ({
  fetchCategories: vi.fn().mockResolvedValue([]),
  fetchProducts: vi.fn().mockResolvedValue([]),
  fetchUnavailableBanks: vi.fn().mockResolvedValue([]),
}))

const mockedUseAuth = vi.mocked(useAuth)

function renderApp() {
  return render(
    <LanguageProvider>
      <App />
    </LanguageProvider>,
  )
}

describe('App auth gating', () => {
  it('shows the login page when there is no authenticated user', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login: vi.fn(), logout: vi.fn() })
    renderApp()
    expect(screen.getByRole('button', { name: 'Kirish' })).toBeInTheDocument()
  })

  it('does not show the Dashboard button for a regular user', () => {
    mockedUseAuth.mockReturnValue({
      user: { username: 'jane', role: 'user' },
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderApp()
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
  })

  it('shows the Dashboard button for an admin user', () => {
    mockedUseAuth.mockReturnValue({
      user: { username: 'admin', role: 'admin' },
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderApp()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })
})
```

- [ ] **Step 6: Testni ishga tushirib, muvaffaqiyatsiz bo'lishini tekshirish**

Run: `npx vitest run src/App.test.tsx`
Expected: FAIL (App hali auth bilan integratsiya qilinmagan — `useAuth`ni import qilmaydi)

- [ ] **Step 7: Testlarni qayta ishga tushirib, o'tishini tekshirish**

Run: `npx vitest run src/App.test.tsx`
Expected: PASS (3 testlar)

- [ ] **Step 8: Butun frontend test to'plamini ishga tushirish**

Run: `npx vitest run`
Expected: Barcha testlar PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/main.tsx frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/components/icons.tsx frontend/src/styles/tokens.css
git commit -m "feat: gate the app behind login and add admin dashboard entry point"
```

---

## Task 13: Qo'lda tekshirish (manual end-to-end verification)

**Files:** yo'q (kod o'zgarmaydi — faqat tasdiqlash)

- [ ] **Step 1: Backend'ni AUTH env o'zgaruvchilari bilan ishga tushirish**

```bash
AUTH_SECRET_KEY="local-dev-secret" ADMIN_USERNAME="admin" ADMIN_PASSWORD="admin12345" .venv/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Expected: Server xatosiz ishga tushadi, `data/bank_products.db`da `users` jadvalida `admin` foydalanuvchi paydo bo'ladi.

- [ ] **Step 2: Frontend'ni ishga tushirish**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Brauzerda quyidagilarni qo'lda tekshirish**

1. Sahifani ochganda darhol login formasi ko'rinadi (jadval/sidebar ko'rinmaydi).
2. Noto'g'ri login/parol bilan xato xabari chiqadi.
3. `admin`/`admin12345` bilan kirilganda asosiy ilova ochiladi, header'da "Dashboard" tugmasi va username ko'rinadi.
4. "Dashboard" bosilganda admin panel ochiladi, seed qilingan `admin` useri ro'yxatda ko'rinadi.
5. "Yangi user qo'shish" orqali `role=user` bilan yangi user yaratiladi.
6. Yangi userni "Tahrirlash" orqali `role=admin`ga o'zgartirib ko'rish — muvaffaqiyatli bo'lishi kerak.
7. `admin` (id=1) qatorida "Tahrirlash" → rolni "Foydalanuvchi"ga o'zgartirishga urinish — xato xabari chiqishi kerak ("O'z rolingizni o'zgartira olmaysiz").
8. "Chiqish" bosib, yangi yaratilgan `role=user` hisobi bilan qayta kirish — "Dashboard" tugmasi header'da KO'RINMASLIGI kerak.
9. Excel eksport (joriy sahifa va barcha kategoriyalar) — fayl muvaffaqiyatli yuklab olinishi kerak (avvalgidek ishlashi, endi autentifikatsiyalangan holda).
10. Sahifani yangilash (F5) — sessiya saqlanib qolishi, qayta login so'ralmasligi kerak (token `localStorage`da).

- [ ] **Step 4: Muammo topilsa, tegishli taskka qaytib tuzatish**

Har qanday nomuvofiqlik shu qo'lda tekshiruv bosqichida ushlanishi kerak — avtomatik testlar buni to'liq qamrab olmaydi (real brauzer, real ikkita server).
