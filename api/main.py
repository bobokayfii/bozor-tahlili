from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from auth.dependencies import AuthenticatedUser, configure_session_factory, get_current_user, require_admin
from auth.security import create_access_token, hash_password, verify_password
from categories import CATEGORIES
from db.database import get_engine, get_session_factory, init_db
from db.models import ProductRow, ScrapeRunRow, UserRow
from export_excel import build_all_categories_workbook, build_category_workbook
from recommender.explain import FeaturedProduct, explain_featured_product, explain_recommendation
from recommender.scoring import Criteria, top_recommendations
from scrapers.orchestrator import run_all_scrapers
from scrapers.registry import ALL_SCRAPERS
from unavailable_products import get_unavailable_banks

logger = logging.getLogger(__name__)

_engine = get_engine()
init_db(_engine)
SessionLocal = get_session_factory(_engine)
configure_session_factory(SessionLocal)

if not os.environ.get("AUTH_SECRET_KEY"):
    raise RuntimeError("AUTH_SECRET_KEY environment o'zgaruvchisi talab qilinadi (JWT token imzolash uchun)")

# /auth/login'da mavjud bo'lmagan username uchun ham shu hash bilan bcrypt
# ishga tushiriladi (pastga qarang) — aks holda "user topilmadi" javobi
# "parol noto'g'ri" javobidan sezilarli tezroq qaytadi, bu esa vaqt
# farqidan (timing) haqiqiy username'larni aniqlash imkonini beradi.
_DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-constant-time-login")

# Oddiy in-memory login rate-limiter — IP+username juftligi bo'yicha oyna
# ichida urinishlar sonini cheklaydi (bcrypt brute-force'ga qarshi). Redis
# yoki tashqi do'kon shart emas: bitta uvicorn worker ichida ishlagani
# uchun (Railway'da ham shunday — _scrape_in_progress bayrog'idagi bilan
# bir xil soddalik) shu yetarli.
_login_attempts: dict[str, list[float]] = defaultdict(list)
_LOGIN_MAX_ATTEMPTS = 10
_LOGIN_WINDOW_SECONDS = 300.0


def _check_login_rate_limit(key: str) -> None:
    now = time.monotonic()
    attempts = _login_attempts[key]
    attempts[:] = [attempt for attempt in attempts if now - attempt < _LOGIN_WINDOW_SECONDS]
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Juda ko'p urinish. Birozdan so'ng qayta urinib ko'ring.")
    attempts.append(now)


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
            logger.warning(
                "Admin akkaunt topilmadi, ADMIN_USERNAME/ADMIN_PASSWORD env o'zgaruvchilarni sozlang"
            )
            return
        session.add(UserRow(
            username=admin_username,
            password_hash=hash_password(admin_password),
            role="admin",
            created_at=datetime.now(timezone.utc),
        ))
        session.commit()


# Netlify'dagi frontend production domeni ALLOWED_ORIGINS orqali qo'shiladi
# (vergul bilan ajratilgan, masalan "https://my-site.netlify.app"). Localhost
# har qanday portda (Vite tasodifiy port tanlashi mumkin) doim ruxsat etiladi.
_extra_origins = [origin.strip() for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",") if origin.strip()]


# Bitta uvicorn worker ichida (davriy jadval ham, qo'lda "Yangilash"
# tugmasi ham) run_all_scrapers() bir vaqtning o'zida IKKI marta ishga
# tushmasligi uchun sodda in-memory bayroq bilan himoyalangan — ikkalasi
# bir xil SQLite faylga yozgani uchun bir-birining ustidan yozib
# yubormasligi kerak. Bitta process ichida ishlagani uchun (Railway'da ham
# shunday) bu yetarli, ko'p processli/ko'p worker holatida esa (masalan,
# gunicorn bir nechta worker bilan) tashqi lock (Redis va h.k.) kerak bo'lardi.
_scrape_state_lock = threading.Lock()
_scrape_in_progress = False


def _mark_scrape_finished() -> None:
    global _scrape_in_progress
    with _scrape_state_lock:
        _scrape_in_progress = False


def _scheduled_scrape_job() -> None:
    global _scrape_in_progress
    with _scrape_state_lock:
        if _scrape_in_progress:
            # Qo'lda ishga tushirilgan yangilash hali tugallanmagan —
            # davriy sikl bu safar chetlab o'tiladi, keyingi sikli kutadi.
            return
        _scrape_in_progress = True
    try:
        with SessionLocal() as session:
            run_all_scrapers(session)
    finally:
        _mark_scrape_finished()


def _run_manual_scrape() -> None:
    try:
        with SessionLocal() as session:
            run_all_scrapers(session)
    finally:
        _mark_scrape_finished()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _bootstrap_admin_if_needed()
    # BackgroundScheduler alohida process talab qilmaydi — shu bitta
    # uvicorn worker ichida fon oqimida ishlaydi, shuning uchun Railway'da
    # bitta "web" xizmati ham API'ni, ham davriy scraping'ni bajaradi (SQLite
    # fayliga faqat bitta process yozadi — ikkinchi xizmat/volume kerak emas).
    interval_hours = int(os.environ.get("SCRAPE_INTERVAL_HOURS", "24"))
    scheduler = BackgroundScheduler()
    # next_run_time=hozir bo'lmasa, APScheduler'ning "interval" trigger'i
    # birinchi ishga tushishni to'liq bir interval (standart 24 soat)
    # kutib turadi — bu esa yangi deploy qilingan (bo'sh SQLite bilan)
    # xizmatni bir kun davomida ma'lumotsiz qoldiradi. Shuning uchun
    # birinchi scraping deploy bo'lgan zahoti (fon oqimida, app javob
    # berishiga xalaqit bermay) ishga tushadi.
    scheduler.add_job(_scheduled_scrape_job, "interval", hours=interval_hours, next_run_time=datetime.now())
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Bank Mahsulot Tahlili API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Vite tanlaydigan port band portlar sababli sessiyadan-sessiyaga
    # o'zgarishi mumkin (5173, 5174, 5175, ...), shuning uchun aniq bitta
    # portni qattiq yozish o'rniga har qanday localhost portiga ruxsat
    # beriladi. Production frontend domeni ALLOWED_ORIGINS env var orqali
    # qo'shiladi.
    allow_origin_regex=r"http://localhost:\d+",
    allow_origins=_extra_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    username: str
    role: str


@app.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest, http_request: Request):
    client_host = http_request.client.host if http_request.client else "unknown"
    _check_login_rate_limit(f"{client_host}:{request.username}")
    with SessionLocal() as session:
        user = session.execute(select(UserRow).where(UserRow.username == request.username)).scalar_one_or_none()
    if user is None:
        # Still runs bcrypt against a fixed hash so a nonexistent username
        # doesn't return measurably faster than a wrong password for a real
        # one - otherwise the response time alone lets an attacker enumerate
        # valid usernames before starting the actual brute-force.
        verify_password(request.password, _DUMMY_PASSWORD_HASH)
        raise HTTPException(status_code=401, detail="Login yoki parol noto'g'ri")
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Login yoki parol noto'g'ri")
    token = create_access_token(user_id=user.id, username=user.username, role=user.role, token_version=user.token_version)
    return LoginResponse(access_token=token, username=user.username, role=user.role)


@app.get("/auth/me")
def get_me(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role}


class RecommendRequest(BaseModel):
    category: str
    amount_som: int = Field(ge=0)
    term_months: int = Field(ge=0)
    collateral_ok: bool


class ExplainProductRequest(BaseModel):
    category: str
    # Matches ProductRow's own column limits (db/models.py) - this endpoint
    # accepts these as free-form request fields rather than reading them
    # back from a product row, so nothing else bounds how much of this
    # authenticated-but-untrusted text reaches the LLM prompt otherwise.
    bank: str = Field(max_length=100)
    product_name: str = Field(max_length=200)
    rate_min: float = Field(ge=0)
    rate_max: float = Field(ge=0)
    term_min_months: int = Field(ge=0)
    term_max_months: int = Field(ge=0)
    amount_max_som: int = Field(ge=0)
    requires_collateral: bool
    down_payment_pct: float | None = Field(default=None, ge=0)
    language: str = "uz"


def _utc_isoformat(value: datetime) -> str:
    """Every stored timestamp is written as UTC (datetime.now(timezone.utc)),
    but SQLite's DateTime column strips tzinfo on read, so a naive
    isoformat() carries no "Z"/offset marker. Every browser's Date() parser
    then reads a marker-less string as LOCAL time instead of UTC, silently
    showing the wrong wall-clock time to anyone outside UTC+0. Re-attaching
    the UTC tag before serializing fixes that at the source."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _row_to_dict(row: ProductRow) -> dict:
    return {
        "bank": row.bank,
        "category": row.category,
        "product_name": row.product_name,
        "rate_min": row.rate_min,
        "rate_max": row.rate_max,
        "term_min_months": row.term_min_months,
        "term_max_months": row.term_max_months,
        "amount_max_som": row.amount_max_som,
        "requires_collateral": row.requires_collateral,
        "down_payment_pct": row.down_payment_pct,
        "grace_period_months": row.grace_period_months,
        "payment_method": row.payment_method,
        "special_terms": row.special_terms,
        "scraped_at": _utc_isoformat(row.scraped_at),
    }


def _latest_per_bank_category_query():
    """ProductRow append-only jadval bo'lgani uchun har bir scrape ishga
    tushirilganda (bank, category) juftligi uchun yangi qator qo'shiladi.
    Bu subquery har bir (bank, category) juftligi uchun eng so'nggi
    scraped_at qiymatini topadi va ProductRow'ga qaytarib bog'laydi, shunda
    faqat eng so'nggi mos mahsulotlar tanlanadi (eski tarixiy qatorlar
    filtrlanadi)."""
    latest = (
        select(
            ProductRow.bank,
            ProductRow.category,
            func.max(ProductRow.scraped_at).label("scraped_at"),
        )
        .group_by(ProductRow.bank, ProductRow.category)
        .subquery()
    )
    return select(ProductRow).join(
        latest,
        (ProductRow.bank == latest.c.bank)
        & (ProductRow.category == latest.c.category)
        & (ProductRow.scraped_at == latest.c.scraped_at),
    )


@app.get("/products")
def list_products(category: str | None = None, bank: str | None = None, _: AuthenticatedUser = Depends(get_current_user)):
    with SessionLocal() as session:
        query = _latest_per_bank_category_query()
        if category:
            query = query.where(ProductRow.category == category)
        if bank:
            query = query.where(ProductRow.bank == bank)
        rows = session.execute(query).scalars().all()
        return [_row_to_dict(row) for row in rows]


@app.get("/categories")
def list_categories(_: AuthenticatedUser = Depends(get_current_user)):
    return [{"key": c.key, "label": c.label_uz, "schema": c.schema} for c in CATEGORIES]


@app.get("/unavailable-banks")
def list_unavailable_banks(category: str, _: AuthenticatedUser = Depends(get_current_user)):
    return [{"bank": item.bank, "reason": item.reason} for item in get_unavailable_banks(category)]


@app.post("/recommend")
def recommend(request: RecommendRequest, _: AuthenticatedUser = Depends(get_current_user)):
    criteria = Criteria(
        category=request.category,
        amount_som=request.amount_som,
        term_months=request.term_months,
        collateral_ok=request.collateral_ok,
    )
    with SessionLocal() as session:
        query = _latest_per_bank_category_query().where(ProductRow.category == request.category)
        rows = session.execute(query).scalars().all()

    ranked = top_recommendations(criteria, rows)
    explanation = explain_recommendation(criteria, ranked)
    return {
        "recommendations": [
            {
                "bank": item.bank,
                "product_name": item.product_name,
                "score": item.score,
                "rate_min": item.rate_min,
                "rate_max": item.rate_max,
                "term_min_months": item.term_min_months,
                "term_max_months": item.term_max_months,
                "amount_max_som": item.amount_max_som,
                "requires_collateral": item.requires_collateral,
                "down_payment_pct": item.down_payment_pct,
                "payment_method": item.payment_method,
                "grace_period_months": item.grace_period_months,
            }
            for item in ranked
        ],
        "explanation": explanation,
    }


@app.post("/explain-product")
def explain_product(request: ExplainProductRequest, _: AuthenticatedUser = Depends(get_current_user)):
    """Frontend "Bozor pulsi" kartochkasi jadvaldagi eng past stavkali
    mahsulotni (mustaqil, oddiy hisob-kitob bilan) tanlaydi — bu endpoint
    esa /recommend'dagi kabi o'z ballash/saralashini ishlatmasdan, ANIQ
    shu bank/mahsulot haqida qisqa AI izohi qaytaradi. Shu sabab kartochka
    va izoh hech qachon boshqa-boshqa bankni ko'rsatib qolmaydi."""
    with SessionLocal() as session:
        query = _latest_per_bank_category_query().where(ProductRow.category == request.category)
        rows = session.execute(query).scalars().all()
    other_bank_count = len({row.bank for row in rows if row.bank != request.bank})

    product = FeaturedProduct(
        bank=request.bank,
        product_name=request.product_name,
        rate_min=request.rate_min,
        rate_max=request.rate_max,
        term_min_months=request.term_min_months,
        term_max_months=request.term_max_months,
        amount_max_som=request.amount_max_som,
        requires_collateral=request.requires_collateral,
        down_payment_pct=request.down_payment_pct,
    )
    explanation = explain_featured_product(request.category, product, other_bank_count, request.language)
    return {"explanation": explanation}


@app.get("/export-excel")
def export_excel(category: str, language: str = "uz", _: AuthenticatedUser = Depends(get_current_user)):
    """Joriy ochiq kategoriyani frontenddagi jadval bilan bir xil tartib
    va ustunlarda (rate_min bo'yicha saralangan) chiroyli formatlangan
    .xlsx faylga eksport qiladi — faqat shu kategoriya, butun sayt emas."""
    category_obj = next((c for c in CATEGORIES if c.key == category), None)
    if category_obj is None:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")

    with SessionLocal() as session:
        query = _latest_per_bank_category_query().where(ProductRow.category == category)
        rows = session.execute(query).scalars().all()

    unavailable_banks = get_unavailable_banks(category)
    content = build_category_workbook(
        category_key=category,
        sheet_title=category_obj.label_uz,
        products=list(rows),
        unavailable_banks=unavailable_banks,
        schema=category_obj.schema,
        lang=language,
    )

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{category}.xlsx"'},
    )


@app.get("/export-excel-all")
def export_excel_all(language: str = "uz", _: AuthenticatedUser = Depends(get_current_user)):
    """Barcha kategoriyalarni BITTA .xlsx faylida, har biri o'z nomi bilan
    alohida varaqda (sheet) eksport qiladi — hisobot uchun to'liq
    ma'lumotlar to'plami."""
    with SessionLocal() as session:
        products_by_category: dict[str, list[ProductRow]] = {}
        for category in CATEGORIES:
            query = _latest_per_bank_category_query().where(ProductRow.category == category.key)
            rows = session.execute(query).scalars().all()
            products_by_category[category.key] = list(rows)

    unavailable_by_category = {category.key: get_unavailable_banks(category.key) for category in CATEGORIES}

    content = build_all_categories_workbook(
        categories=[(c.key, c.label_uz, c.schema) for c in CATEGORIES],
        products_by_category=products_by_category,
        unavailable_by_category=unavailable_by_category,
        lang=language,
    )

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="bozor-tahlili-barcha-kategoriyalar.xlsx"'},
    )


@app.post("/trigger-scrape")
def trigger_scrape(_: AuthenticatedUser = Depends(require_admin)):
    """Buyurtmachi so'ragan "qo'lda yangilash" tugmasi uchun: barcha
    banklarni HOZIR qayta scrape qilishni boshlaydi. HTTP so'rovni
    bloklamaslik uchun run_all_scrapers alohida oqimda (thread) ishga
    tushiriladi — javob darhol qaytadi, scrape esa fonda davom etadi.
    Davriy sikl bilan bir vaqtda ikkalasi ham ishlab, bir xil SQLite
    faylga bir-birining ustidan yozib yubormasligi uchun
    _scrape_in_progress bayrog'i orqali himoyalangan: agar allaqachon
    biror scrape ketayotgan bo'lsa, 409 qaytariladi."""
    global _scrape_in_progress
    with _scrape_state_lock:
        if _scrape_in_progress:
            raise HTTPException(status_code=409, detail="Yangilash allaqachon ishlamoqda")
        _scrape_in_progress = True

    threading.Thread(target=_run_manual_scrape, daemon=True).start()
    return {"status": "started"}


class CreateUserRequest(BaseModel):
    username: str
    password: str = Field(min_length=8)
    role: Literal["admin", "user"]


class UpdateUserRequest(BaseModel):
    username: str | None = None
    password: str | None = Field(default=None, min_length=8)
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
            UserResponse(id=row.id, username=row.username, role=row.role, created_at=_utc_isoformat(row.created_at))
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
            created_at=_utc_isoformat(new_user.created_at),
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
            user.token_version += 1
        if request.role is not None and request.role != user.role:
            user.role = request.role
            user.token_version += 1
        session.commit()
        session.refresh(user)
        return UserResponse(id=user.id, username=user.username, role=user.role, created_at=_utc_isoformat(user.created_at))


class ScrapeRunResponse(BaseModel):
    bank: str
    status: str
    started_at: str | None
    finished_at: str | None
    error_message: str | None
    products_found: int


# ScrapeRunRow biror bank uchun mos qator yozmagan bo'lishi mumkin — hech
# qachon ishlamagan yoki avval registry.py'dan olib tashlangan (keyin qayta
# qo'shilgan) bank. Bunday holatlar ham "never_run" sifatida ko'rinsin,
# aks holda operator o'sha bankning umuman tekshirilmaganini bilmay qoladi.
_SCRAPE_STATUS_SORT_ORDER = {"failed": 0, "running": 1, "no_products": 2, "never_run": 3, "success": 4}


@app.get("/admin/scrape-runs", response_model=list[ScrapeRunResponse])
def list_scrape_runs(_: AuthenticatedUser = Depends(require_admin)):
    with SessionLocal() as session:
        latest_started_at = (
            select(ScrapeRunRow.bank, func.max(ScrapeRunRow.started_at).label("started_at"))
            .group_by(ScrapeRunRow.bank)
            .subquery()
        )
        rows = (
            session.execute(
                select(ScrapeRunRow).join(
                    latest_started_at,
                    (ScrapeRunRow.bank == latest_started_at.c.bank)
                    & (ScrapeRunRow.started_at == latest_started_at.c.started_at),
                )
            )
            .scalars()
            .all()
        )
        latest_by_bank = {row.bank: row for row in rows}

    results = []
    for scraper_cls in ALL_SCRAPERS:
        bank = scraper_cls.bank_name
        run = latest_by_bank.get(bank)
        if run is None:
            results.append(ScrapeRunResponse(
                bank=bank, status="never_run", started_at=None, finished_at=None,
                error_message=None, products_found=0,
            ))
        else:
            # A run that raised nothing but still found zero products is a
            # real, actionable problem the "success" label hides: a bank
            # switching to a JS-rendered page or turning on a Cloudflare
            # bot-challenge produces exactly this (confirmed live for
            # Asakabank/AgroBank/Kapitalbank) - no exception, just nothing
            # parseable, so it looked identical to a healthy bank at a
            # glance until this override.
            status = "no_products" if run.status == "success" and run.products_found == 0 else run.status
            results.append(ScrapeRunResponse(
                bank=bank,
                status=status,
                started_at=_utc_isoformat(run.started_at),
                finished_at=_utc_isoformat(run.finished_at) if run.finished_at is not None else None,
                error_message=run.error_message,
                products_found=run.products_found,
            ))

    results.sort(key=lambda r: (_SCRAPE_STATUS_SORT_ORDER.get(r.status, 99), r.bank))
    return results
