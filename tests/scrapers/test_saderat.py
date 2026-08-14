from pathlib import Path
from unittest.mock import patch

from scrapers.saderat import SaderatBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    SaderatBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "saderat_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    SaderatBankScraper.CATEGORY_URLS["istemol_krediti"]: (FIXTURES_DIR / "saderat_istemol.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_saderat_avtokredit_parses_correctly():
    """Down payment and rate are both stated as the identical "25% dan"
    on this page — not a scraper bug, the page genuinely repeats the same
    figure for both fields. Term/amount use a reversed word order
    ("gacha oylar"/"gacha million so'm") the shared extract_term_months/
    extract_amount_som helpers don't recognize, hence the bespoke regexes.
    Collateral and repayment method come from the "Umumiy shartlar" promo
    table further down the page — that table's own 0% rate belongs to a
    specific UzAuto Motors promo, not this general product, and must NOT
    leak into rate_min/rate_max here."""
    with patch("scrapers.saderat.fetch_html", side_effect=_fake_fetch):
        products = SaderatBankScraper().run()

    product = next(p for p in products if p.category == "avtokredit")
    assert product.bank == "Saderat Bank"
    assert product.rate_min == 25.0
    assert product.rate_max == 25.0
    assert product.term_min_months == 60
    assert product.term_max_months == 60
    assert product.amount_max_som == 600_000_000
    assert product.down_payment_pct == 25.0
    assert product.requires_collateral is True
    assert product.payment_method == "Annuitet, Differensial"
    assert product.grace_period_months is None


def test_saderat_istemol_krediti_parses_correctly():
    """Clean flat "Label: value" layout, no traps. The collateral clause
    lists required documents but never uses the word "garov" — correctly
    resolves to False, not a bug."""
    with patch("scrapers.saderat.fetch_html", side_effect=_fake_fetch):
        products = SaderatBankScraper().run()

    product = next(p for p in products if p.category == "istemol_krediti")
    assert product.product_name == "Iste'mol krediti"
    assert product.rate_min == 28.0
    assert product.rate_max == 28.0
    assert product.term_min_months == 24
    assert product.term_max_months == 24
    assert product.amount_max_som == 100_000_000
    assert product.down_payment_pct is None
    assert product.requires_collateral is False
    assert product.grace_period_months == 0
    assert product.payment_method is None
