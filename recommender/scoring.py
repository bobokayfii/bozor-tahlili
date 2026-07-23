from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Criteria:
    category: str
    amount_som: int
    term_months: int
    collateral_ok: bool


@dataclass
class ScoredProduct:
    bank: str
    product_name: str
    score: float
    rate_min: float
    rate_max: float
    term_min_months: int
    term_max_months: int
    amount_max_som: int
    requires_collateral: bool
    down_payment_pct: float | None
    payment_method: str | None
    grace_period_months: int | None
    special_terms: str | None


class _ScorableProduct(Protocol):
    bank: str
    category: str
    rate_min: float
    rate_max: float
    term_min_months: int
    term_max_months: int
    amount_max_som: int
    requires_collateral: bool
    down_payment_pct: float | None
    payment_method: str | None
    grace_period_months: int | None
    special_terms: str | None


def score_product(criteria: Criteria, product: _ScorableProduct) -> float | None:
    if product.category != criteria.category:
        return None
    if product.amount_max_som < criteria.amount_som:
        return None
    if criteria.term_months < product.term_min_months or criteria.term_months > product.term_max_months:
        return None
    if product.requires_collateral and not criteria.collateral_ok:
        return None

    rate_score = max(0.0, 1 - (product.rate_min / 60))
    collateral_score = 1.0 if not product.requires_collateral else 0.6
    term_span = product.term_max_months - product.term_min_months
    term_score = min(1.0, term_span / 60)
    amount_headroom = min(1.0, product.amount_max_som / max(criteria.amount_som, 1) / 5)

    return round(
        rate_score * 0.40
        + collateral_score * 0.25
        + term_score * 0.20
        + amount_headroom * 0.15,
        4,
    )


def top_recommendations(
    criteria: Criteria, products: list[_ScorableProduct], top_n: int = 3
) -> list[ScoredProduct]:
    scored: list[ScoredProduct] = []
    for product in products:
        score = score_product(criteria, product)
        if score is None:
            continue
        scored.append(
            ScoredProduct(
                bank=product.bank,
                product_name=getattr(product, "product_name", product.bank),
                score=score,
                rate_min=product.rate_min,
                rate_max=product.rate_max,
                term_min_months=product.term_min_months,
                term_max_months=product.term_max_months,
                amount_max_som=product.amount_max_som,
                requires_collateral=product.requires_collateral,
                down_payment_pct=product.down_payment_pct,
                # Ko'pchilik banklar to'lov usulini aniq ko'rsatmasa ham
                # amalda annuitet yoki differensial jadvalidan birini tanlash
                # imkonini beradi (bu loyihada tekshirilgan barcha banklar
                # bo'yicha kuzatilgan konvensiya) — shu sabab noaniq bo'lsa
                # shu ikkalasi ko'rsatiladi, umuman aytilmagan deb qoldirilmaydi.
                payment_method=product.payment_method or "Annuitet, Differensial",
                grace_period_months=product.grace_period_months,
                special_terms=product.special_terms,
            )
        )
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:top_n]
