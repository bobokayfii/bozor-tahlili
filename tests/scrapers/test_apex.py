from pathlib import Path
from unittest.mock import patch

from scrapers.apex import ApexBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    ApexBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "apex_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    ApexBankScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (FIXTURES_DIR / "apex_mikroqarz_onlayn.html").read_text(
        encoding="utf-8"
    ),
    ApexBankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (FIXTURES_DIR / "apex_ipoteka.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_apex_mikroqarz_parses_correctly():
    """Offline microloan — every field label on this page appears 2-3
    times (hero card, calculator widget, real detail block); the scraper
    must land on the detail block's values, not the calculator's bare
    range-boundary numbers. Collateral is one of three accepted options
    (insurance, property pledge, or cash deposit) and the word "garov"
    genuinely appears in the detail block, so True is correct even though
    collateral isn't strictly mandatory for every borrower."""
    with patch("scrapers.apex.fetch_html", side_effect=_fake_fetch):
        products = ApexBankScraper().run()

    product = next(p for p in products if p.category == "mikroqarz")
    assert product.bank == "Apex Bank"
    assert product.rate_min == 22.0
    assert product.rate_max == 35.0
    assert product.term_min_months == 6
    assert product.term_max_months == 36
    assert product.amount_max_som == 100_000_000
    assert product.requires_collateral is True
    assert product.grace_period_months == 0
    assert product.payment_method == "Annuitet, Differensial"


def test_apex_mikroqarz_onlayn_parses_correctly():
    """Online microloan — same amount/rate/term shape as the offline
    variant, but repayment is Annuitet-only ("So'ndirish usuli", not
    "Qaytarish usuli") and there is no collateral at all (only an
    insurance policy is required, "garov" never appears on this page)."""
    with patch("scrapers.apex.fetch_html", side_effect=_fake_fetch):
        products = ApexBankScraper().run()

    product = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert product.rate_min == 22.0
    assert product.rate_max == 35.0
    assert product.term_min_months == 6
    assert product.term_max_months == 36
    assert product.amount_max_som == 100_000_000
    assert product.requires_collateral is False
    assert product.grace_period_months == 0
    assert product.payment_method == "Annuitet"


def test_apex_ipoteka_tijorat_parses_correctly():
    """Ipoteka Comfort — term is stated as "6 dan 120 oygacha" (missing
    the "oy" unit after the first number), which the shared
    extract_term_months cannot parse as a range; a bespoke regex is
    required or term_min would silently equal term_max (120)."""
    with patch("scrapers.apex.fetch_html", side_effect=_fake_fetch):
        products = ApexBankScraper().run()

    product = next(p for p in products if p.category == "ipoteka_tijorat")
    assert product.product_name == "Ipoteka Comfort"
    assert product.rate_min == 25.0
    assert product.rate_max == 25.0
    assert product.term_min_months == 6
    assert product.term_max_months == 120
    assert product.amount_max_som == 1_500_000_000
    assert product.down_payment_pct == 25.0
    assert product.requires_collateral is True
    assert product.grace_period_months == 0
    assert product.payment_method is None
