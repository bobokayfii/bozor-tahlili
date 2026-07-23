from pathlib import Path
from unittest.mock import patch

from scrapers.xalqbank import XalqBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    XalqBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "xb_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    XalqBankScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (FIXTURES_DIR / "xb_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_xalqbank_avtokredit_parses_correctly():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = XalqBankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.bank == "Xalq Banki"
    assert avtokredit.rate_min == 23.0
    assert avtokredit.rate_max == 23.0
    assert avtokredit.term_min_months == 60
    assert avtokredit.term_max_months == 60
    # Real page text is "600 ООО ООО so'mgacha" — Cyrillic О typo'd in for
    # zeros — normalized to 600 million before parsing.
    assert avtokredit.amount_max_som == 600_000_000
    assert avtokredit.requires_collateral is True
    assert avtokredit.product_name == "Onlayn-Avtokredit"
    assert avtokredit.down_payment_pct == 25.0
    assert avtokredit.grace_period_months == 0
    assert avtokredit.payment_method == "Annuitet"


def test_xalqbank_mikroqarz_onlayn_parses_correctly():
    """The product is literally named "Onlayn mikroqarz" and described as
    fully automated (scoring-based, no documents, delivered via the
    "Xazna" mobile app) — it belongs under mikroqarz_onlayn, not the
    offline mikroqarz category."""
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = XalqBankScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert mikroqarz.bank == "Xalq Banki"
    assert mikroqarz.product_name == "Onlayn mikroqarz"
    assert mikroqarz.rate_min == 24.0
    assert mikroqarz.rate_max == 29.0
    assert mikroqarz.term_min_months == 12
    assert mikroqarz.term_max_months == 48
    assert mikroqarz.amount_max_som == 100_000_000
    assert mikroqarz.down_payment_pct == 0.0
    assert mikroqarz.grace_period_months is None
    assert mikroqarz.payment_method == "Annuitet"
    assert mikroqarz.requires_collateral is True
