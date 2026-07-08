from __future__ import annotations

import os

from openai import OpenAI

from recommender.scoring import Criteria, ScoredProduct

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
    prompt = (
        f"Foydalanuvchi {criteria.category} kategoriyasida {criteria.amount_som} so'm, "
        f"{criteria.term_months} oy muddatga kredit izlamoqda. "
        "Quyidagi banklar ballash bo'yicha saralangan:\n" + "\n".join(lines) +
        "\nO'zbek tilida, 3-4 gapda, nima uchun birinchi o'rindagi bank tavsiya "
        "etilishini tushuntir."
    )

    try:
        response = get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            timeout=10,
        )
        return response.choices[0].message.content
    except Exception:
        return "\n".join(lines)
