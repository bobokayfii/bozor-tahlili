from __future__ import annotations

import logging
import os

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


def _format_product_details(item: ScoredProduct) -> str:
    down_payment = f"{item.down_payment_pct}% dan" if item.down_payment_pct is not None else "aytilmagan"
    collateral = "talab qilinadi" if item.requires_collateral else "talab qilinmaydi"
    grace = f"{item.grace_period_months} oy" if item.grace_period_months else "yo'q"
    return (
        f"- Bank: {item.bank}\n"
        f"  Mahsulot: {item.product_name}\n"
        f"  Yillik stavka: {item.rate_min}%–{item.rate_max}%\n"
        f"  Muddat: {item.term_min_months}–{item.term_max_months} oy\n"
        f"  Maksimal summa: {item.amount_max_som:,} so'm\n"
        f"  Boshlang'ich badal: {down_payment}\n"
        f"  Garov: {collateral}\n"
        f"  Imtiyozli davr: {grace}\n"
        f"  To'lov usuli: {item.payment_method}\n"
        f"  Ball: {item.score}"
    )


def explain_recommendation(criteria: Criteria, ranked: list[ScoredProduct]) -> str:
    if not ranked:
        return "Berilgan mezonlarga mos mahsulot topilmadi."

    lines = _format_ranking_lines(ranked)
    details = "\n\n".join(_format_product_details(item) for item in ranked)
    prompt = (
        f"Foydalanuvchi {criteria.category} kategoriyasida {criteria.amount_som:,} so'm, "
        f"{criteria.term_months} oy muddatga kredit izlamoqda.\n\n"
        f"Quyidagi banklar ballash bo'yicha saralangan (faqat shu ro'yxatdagi "
        "raqamlardan foydalan, hech qanday qo'shimcha raqam yoki shart o'ylab topma):\n\n"
        f"{details}\n\n"
        "O'zbek tilida, bog'lanishli 4-6 gapdan iborat, tabiiy oqimli matn "
        "sifatida (band-band ro'yxat emas) qisqa tahlil yoz. Bitta bankni "
        "'eng yaxshisi' yoki 'tavsiya etiladi' deb reklama qilma — buning "
        "o'rniga har bir bankning qaysi jihati (masalan past stavka, uzunroq "
        "muddat, garovsizlik) qaysi ehtiyoj uchun mos kelishini xolis "
        "solishtirib ber, shunda foydalanuvchi o'ziga mosini o'zi tanlay "
        "oladi. Raqamlarni matn ichida tabiiy tarzda eslatib o't, alohida "
        "jadval yoki ro'yxat qilib qo'yma."
    )

    try:
        response = get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            timeout=20,
        )
        return response.choices[0].message.content or "\n".join(lines)
    except Exception:
        logger.exception("AI tavsiya tushuntirishini olishda xato yuz berdi")
        return "\n".join(lines)
