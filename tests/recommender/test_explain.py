from unittest.mock import MagicMock, patch

from recommender.explain import explain_recommendation
from recommender.scoring import Criteria, ScoredProduct


def make_criteria():
    return Criteria(category="mikroqarz", amount_som=50_000_000, term_months=12, collateral_ok=False)


def make_ranked():
    return [
        ScoredProduct(
            bank="SQB",
            product_name="SQB Mikroqarz",
            score=0.82,
            rate_min=28.0,
            rate_max=31.0,
            term_min_months=3,
            term_max_months=36,
            amount_max_som=100_000_000,
            requires_collateral=False,
            down_payment_pct=None,
            payment_method="Annuitet, Differensial",
            grace_period_months=None,
            special_terms=None,
        ),
        ScoredProduct(
            bank="NBU",
            product_name="NBU Mikroqarz",
            score=0.71,
            rate_min=30.0,
            rate_max=34.0,
            term_min_months=6,
            term_max_months=24,
            amount_max_som=100_000_000,
            requires_collateral=True,
            down_payment_pct=20.0,
            payment_method="Annuitet, Differensial",
            grace_period_months=6,
            special_terms=None,
        ),
    ]


def test_explain_recommendation_returns_fallback_text_when_no_ranked():
    result = explain_recommendation(make_criteria(), [])
    assert "topilmadi" in result.lower()


def test_explain_recommendation_calls_openai_and_returns_content():
    """"make_ranked()" ikkita mahsulot qaytaradi (SQB + NBU) — explain_recommendation
    faqat birinchisi (SQB) haqida qisqa matn so'raydi, so'ng qolgan banklar sonini
    ("Yana 1 ta bank varianti ham mavjud.") o'zi qo'shib qo'yadi, AI'ning o'zidan
    so'ramaydi (bu qism har doim aniq, hisoblangan raqamga asoslanadi)."""
    fake_response = MagicMock()
    fake_response.choices[0].message.content = "SQB tavsiya etiladi, chunki eng past stavkaga ega."

    with patch("recommender.explain.get_client") as mock_get_client:
        mock_get_client.return_value.chat.completions.create.return_value = fake_response
        result = explain_recommendation(make_criteria(), make_ranked())

    assert result == "SQB tavsiya etiladi, chunki eng past stavkaga ega. Yana 1 ta bank varianti ham mavjud."


def test_explain_recommendation_falls_back_to_score_list_on_api_error():
    with patch("recommender.explain.get_client") as mock_get_client:
        mock_get_client.return_value.chat.completions.create.side_effect = RuntimeError("API xatosi")
        result = explain_recommendation(make_criteria(), make_ranked())

    assert "SQB" in result
    assert "NBU" in result


def test_explain_recommendation_falls_back_to_score_list_when_content_is_none():
    fake_response = MagicMock()
    fake_response.choices[0].message.content = None

    with patch("recommender.explain.get_client") as mock_get_client:
        mock_get_client.return_value.chat.completions.create.return_value = fake_response
        result = explain_recommendation(make_criteria(), make_ranked())

    assert "SQB" in result
    assert "NBU" in result
