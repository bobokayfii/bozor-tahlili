from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from openai import OpenAI

from recommender.scoring import Criteria, ScoredProduct

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def _format_ranking_lines(ranked: list[ScoredProduct]) -> list[str]:
    return [
        f"{i + 1}. {item.bank} — {item.product_name} "
        f"(stavka {item.rate_min}%-{item.rate_max}%, ball: {item.score})"
        for i, item in enumerate(ranked)
    ]


@dataclass
class FeaturedProduct:
    bank: str
    product_name: str
    rate_min: float
    rate_max: float
    term_min_months: int
    term_max_months: int
    amount_max_som: int
    requires_collateral: bool
    down_payment_pct: float | None

    @classmethod
    def from_scored(cls, item: ScoredProduct) -> "FeaturedProduct":
        return cls(
            bank=item.bank,
            product_name=item.product_name,
            rate_min=item.rate_min,
            rate_max=item.rate_max,
            term_min_months=item.term_min_months,
            term_max_months=item.term_max_months,
            amount_max_som=item.amount_max_som,
            requires_collateral=item.requires_collateral,
            down_payment_pct=item.down_payment_pct,
        )


def _build_single_product_prompt(category: str, product: FeaturedProduct) -> str:
    down_payment_note = (
        f", boshlang'ich badal {product.down_payment_pct}% dan" if product.down_payment_pct is not None else ""
    )
    collateral_note = ", garov talab qilinadi" if product.requires_collateral else ", garovsiz"
    return (
        f"Bank: {product.bank} — {product.product_name} ({category} kategoriyasi), "
        f"yillik stavka {product.rate_min}%–{product.rate_max}%, muddat "
        f"{product.term_min_months}–{product.term_max_months} oy, "
        f"maksimal summa {product.amount_max_som:,} so'm{down_payment_note}{collateral_note}.\n\n"
        "Shu ma'lumot asosida, o'zbek tilida, atigi 1-2 ta QISQA gapda "
        "(jami 30-35 so'zdan oshmasin), nega bu variant diqqatga sazovorligini "
        "yoz — faqat shu banknikidan boshqa raqam yoki shart o'ylab topma. "
        "Sarlavha, ro'yxat yoki qo'shimcha izoh qo'shma, faqat oddiy matn."
    )


def _call_model(prompt: str, fallback: str) -> str:
    try:
        response = get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=90,
            timeout=20,
        )
        content = response.choices[0].message.content
        return content.strip() if content else fallback
    except Exception:
        logger.exception("AI tavsiya tushuntirishini olishda xato yuz berdi")
        return fallback


def explain_recommendation(criteria: Criteria, ranked: list[ScoredProduct]) -> str:
    if not ranked:
        return "Berilgan mezonlarga mos mahsulot topilmadi."

    lines = _format_ranking_lines(ranked)
    fallback = "\n".join(lines)
    top = FeaturedProduct.from_scored(ranked[0])
    others_count = len(ranked) - 1
    others_note = f" Yana {others_count} ta bank varianti ham mavjud." if others_count > 0 else ""
    prompt = _build_single_product_prompt(criteria.category, top)

    result = _call_model(prompt, fallback)
    return result + others_note if result != fallback else result


def explain_featured_product(category: str, product: FeaturedProduct, other_bank_count: int) -> str:
    """Frontend "Bozor pulsi" kartochkasi jadvaldagi eng past stavkali
    mahsulotni ko'rsatadi (oddiy, mustaqil hisob-kitob) — bu funksiya esa
    ANIQ shu bank/mahsulot haqida qisqa AI izohi yozadi, hech qanday o'z
    ballash/saralashisiz. Shu sabab kartochka va izoh hech qachon boshqa-
    boshqa bankni ko'rsatib qolmaydi (avval /recommend'ning og'irlikli
    ballash formulasi ba'zan boshqa bankni "eng yaxshi" deb tanlab, jadval
    va kartochka mos kelmasligiga sabab bo'lardi)."""
    others_note = f" Yana {other_bank_count} ta bank varianti ham mavjud." if other_bank_count > 0 else ""
    prompt = _build_single_product_prompt(category, product)
    fallback = f"{product.bank} — {product.product_name}."

    result = _call_model(prompt, fallback)
    return result + others_note if result != fallback else result
