from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select

from categories import CATEGORIES
from db.database import get_engine, get_session_factory, init_db
from db.models import ProductRow
from export_excel import build_all_categories_workbook, build_category_workbook
from recommender.explain import FeaturedProduct, explain_featured_product, explain_recommendation
from recommender.scoring import Criteria, top_recommendations
from scrapers.orchestrator import run_all_scrapers
from unavailable_products import get_unavailable_banks

_engine = get_engine()
init_db(_engine)
SessionLocal = get_session_factory(_engine)

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
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class RecommendRequest(BaseModel):
    category: str
    amount_som: int
    term_months: int
    collateral_ok: bool


class ExplainProductRequest(BaseModel):
    category: str
    bank: str
    product_name: str
    rate_min: float
    rate_max: float
    term_min_months: int
    term_max_months: int
    amount_max_som: int
    requires_collateral: bool
    down_payment_pct: float | None = None
    language: str = "uz"


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
        "scraped_at": row.scraped_at.isoformat(),
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
def list_products(category: str | None = None, bank: str | None = None):
    with SessionLocal() as session:
        query = _latest_per_bank_category_query()
        if category:
            query = query.where(ProductRow.category == category)
        if bank:
            query = query.where(ProductRow.bank == bank)
        rows = session.execute(query).scalars().all()
        return [_row_to_dict(row) for row in rows]


@app.get("/categories")
def list_categories():
    return [{"key": c.key, "label": c.label_uz, "schema": c.schema} for c in CATEGORIES]


@app.get("/unavailable-banks")
def list_unavailable_banks(category: str):
    return [{"bank": item.bank, "reason": item.reason} for item in get_unavailable_banks(category)]


@app.post("/recommend")
def recommend(request: RecommendRequest):
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
def explain_product(request: ExplainProductRequest):
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
def export_excel(category: str, language: str = "uz"):
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
def export_excel_all(language: str = "uz"):
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
def trigger_scrape():
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
