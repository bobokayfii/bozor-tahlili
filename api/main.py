from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, select

from categories import CATEGORIES
from db.database import get_engine, get_session_factory, init_db
from db.models import ProductRow
from recommender.explain import explain_recommendation
from recommender.scoring import Criteria, top_recommendations

app = FastAPI(title="Bank Mahsulot Tahlili API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_engine = get_engine()
init_db(_engine)
SessionLocal = get_session_factory(_engine)


class RecommendRequest(BaseModel):
    category: str
    amount_som: int
    term_months: int
    collateral_ok: bool


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
            {"bank": item.bank, "product_name": item.product_name, "score": item.score}
            for item in ranked
        ],
        "explanation": explanation,
    }
