from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import select

from db.database import get_engine, get_session_factory, init_db
from db.models import ProductRow
from recommender.explain import explain_recommendation
from recommender.scoring import Criteria, top_recommendations

app = FastAPI(title="Bank Mahsulot Tahlili API")

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
        "scraped_at": row.scraped_at.isoformat(),
    }


@app.get("/products")
def list_products(category: str | None = None, bank: str | None = None):
    with SessionLocal() as session:
        query = select(ProductRow)
        if category:
            query = query.where(ProductRow.category == category)
        if bank:
            query = query.where(ProductRow.bank == bank)
        rows = session.execute(query).scalars().all()
        return [_row_to_dict(row) for row in rows]


@app.post("/recommend")
def recommend(request: RecommendRequest):
    criteria = Criteria(
        category=request.category,
        amount_som=request.amount_som,
        term_months=request.term_months,
        collateral_ok=request.collateral_ok,
    )
    with SessionLocal() as session:
        rows = session.execute(
            select(ProductRow).where(ProductRow.category == request.category)
        ).scalars().all()

    ranked = top_recommendations(criteria, rows)
    explanation = explain_recommendation(criteria, ranked)
    return {
        "recommendations": [
            {"bank": item.bank, "product_name": item.product_name, "score": item.score}
            for item in ranked
        ],
        "explanation": explanation,
    }
