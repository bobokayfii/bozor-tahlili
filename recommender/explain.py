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


def explain_recommendation(criteria: Criteria, ranked: list[ScoredProduct]) -> str:
    if not ranked:
        return "Berilgan mezonlarga mos mahsulot topilmadi."

    lines = _format_ranking_lines(ranked)
    top = ranked[0]
    # Frontend "Bozor pulsi" kartochkasi ham xuddi shu ranked[0]'ni ko'rsatadi
    # (ikkalasi bitta manbadan keladi), shuning uchun matn ham ANIQ shu bank
    # haqida bo'lishi kerak — boshqa banklarni alohida-alohida tahlil qilib
    # o'tirish (avvalgi versiyada har biriga bir necha gap bag'ishlangan edi)
    # o'quvchini charchatadi va kartochkadagi bank bilan mos kelmayotgandek
    # tuyulardi. Endi faqat top pick haqida, juda qisqa.
    down_payment_note = f", boshlang'ich badal {top.down_payment_pct}% dan" if top.down_payment_pct is not None else ""
    collateral_note = ", garov talab qilinadi" if top.requires_collateral else ", garovsiz"
    others_count = len(ranked) - 1
    others_note = f" Yana {others_count} ta bank varianti ham mavjud." if others_count > 0 else ""
    prompt = (
        f"Foydalanuvchi {criteria.category} kategoriyasida {criteria.amount_som:,} so'm, "
        f"{criteria.term_months} oy muddatga kredit izlamoqda.\n\n"
        f"Eng mos topilgan bank: {top.bank} — {top.product_name}, "
        f"yillik stavka {top.rate_min}%–{top.rate_max}%, muddat "
        f"{top.term_min_months}–{top.term_max_months} oy, "
        f"maksimal summa {top.amount_max_som:,} so'm{down_payment_note}{collateral_note}.\n\n"
        "Shu ma'lumot asosida, o'zbek tilida, atigi 1-2 ta QISQA gapda "
        "(jami 30-35 so'zdan oshmasin), nega bu variant diqqatga sazovorligini "
        "yoz — faqat shu banknikidan boshqa raqam yoki shart o'ylab topma. "
        "Sarlavha, ro'yxat yoki qo'shimcha izoh qo'shma, faqat oddiy matn."
    )

    try:
        response = get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=90,
            timeout=20,
        )
        content = response.choices[0].message.content
        return (content.strip() + others_note) if content else "\n".join(lines)
    except Exception:
        logger.exception("AI tavsiya tushuntirishini olishda xato yuz berdi")
        return "\n".join(lines)
