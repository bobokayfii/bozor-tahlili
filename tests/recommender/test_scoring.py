from dataclasses import dataclass

from recommender.scoring import Criteria, score_product, top_recommendations


@dataclass
class FakeProduct:
    bank: str
    category: str
    rate_min: float
    rate_max: float
    term_min_months: int
    term_max_months: int
    amount_max_som: int
    requires_collateral: bool
    down_payment_pct: float | None = None
    payment_method: str | None = None
    grace_period_months: int | None = None
    special_terms: str | None = None


def test_score_product_returns_none_for_wrong_category():
    criteria = Criteria(category="mikroqarz", amount_som=50_000_000, term_months=12, collateral_ok=False)
    product = FakeProduct("SQB", "avtokredit", 24.0, 27.0, 12, 60, 800_000_000, True)
    assert score_product(criteria, product) is None


def test_score_product_returns_none_when_amount_exceeds_max():
    criteria = Criteria(category="mikroqarz", amount_som=200_000_000, term_months=12, collateral_ok=False)
    product = FakeProduct("SQB", "mikroqarz", 28.0, 31.0, 3, 36, 100_000_000, False)
    assert score_product(criteria, product) is None


def test_score_product_returns_none_when_collateral_required_but_unavailable():
    criteria = Criteria(category="avtokredit", amount_som=100_000_000, term_months=24, collateral_ok=False)
    product = FakeProduct("SQB", "avtokredit", 24.0, 27.0, 12, 60, 800_000_000, True)
    assert score_product(criteria, product) is None


def test_score_product_returns_value_for_matching_product():
    criteria = Criteria(category="mikroqarz", amount_som=50_000_000, term_months=12, collateral_ok=False)
    product = FakeProduct("SQB", "mikroqarz", 28.0, 31.0, 3, 36, 100_000_000, False)
    score = score_product(criteria, product)
    assert score is not None
    assert 0.0 < score <= 1.0


def test_top_recommendations_ranks_lower_rate_higher():
    criteria = Criteria(category="mikroqarz", amount_som=50_000_000, term_months=12, collateral_ok=True)
    cheap = FakeProduct("CheapBank", "mikroqarz", 20.0, 22.0, 3, 36, 100_000_000, False)
    expensive = FakeProduct("ExpensiveBank", "mikroqarz", 40.0, 45.0, 3, 36, 100_000_000, False)

    ranked = top_recommendations(criteria, [expensive, cheap], top_n=2)

    assert [item.bank for item in ranked] == ["CheapBank", "ExpensiveBank"]


def test_top_recommendations_respects_top_n():
    criteria = Criteria(category="mikroqarz", amount_som=50_000_000, term_months=12, collateral_ok=True)
    products = [
        FakeProduct(f"Bank{i}", "mikroqarz", 20.0 + i, 25.0 + i, 3, 36, 100_000_000, False)
        for i in range(5)
    ]
    ranked = top_recommendations(criteria, products, top_n=3)
    assert len(ranked) == 3
