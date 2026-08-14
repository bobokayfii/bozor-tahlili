from pathlib import Path
from unittest.mock import patch

from scrapers.garant import GarantBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    GarantBankScraper.CATEGORY_URLS["avtokredit_brend_birlamchi"]: (
        FIXTURES_DIR / "garant_avtokredit.html"
    ).read_text(encoding="utf-8"),
    GarantBankScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (FIXTURES_DIR / "garant_mikrozajm.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_garant_avtokredit_brend_birlamchi_parses_correctly():
    """Avtokredit «Yengil» — UzAuto Motors (Tracker/Damas/Onix) promo,
    0% flat rate, single repayment method (Annuitet only, no
    Differensial offered — the page states "Foiz hisoblash: Annuitet
    shaklda" with no mention of a differentiated option)."""
    with patch("scrapers.garant.fetch_html", side_effect=_fake_fetch):
        products = GarantBankScraper().run()

    product = next(p for p in products if p.category == "avtokredit_brend_birlamchi")
    assert product.bank == "Garant bank"
    assert product.product_name == "Avtokredit «Yengil»"
    assert product.rate_min == 0.0
    assert product.rate_max == 0.0
    assert product.term_min_months == 60
    assert product.term_max_months == 60
    assert product.amount_max_som == 600_000_000
    assert product.requires_collateral is True
    assert product.grace_period_months == 0
    assert product.payment_method == "Annuitet"


def test_garant_mikroqarz_onlayn_parses_correctly():
    """Mikrozayim onlayn — mobile-app microloan, rate tiered 28%-42% by
    term (6 to 48 months). No "garov" appears anywhere on this page
    (confirmed directly), so full-page collateral detection correctly
    resolves to False without needing a narrower scope."""
    with patch("scrapers.garant.fetch_html", side_effect=_fake_fetch):
        products = GarantBankScraper().run()

    product = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert product.product_name == "Mikrozayim onlayn"
    assert product.rate_min == 28.0
    assert product.rate_max == 42.0
    assert product.term_min_months == 48
    assert product.term_max_months == 48
    assert product.amount_max_som == 100_000_000
    assert product.requires_collateral is False
    assert product.grace_period_months == 0
    assert product.payment_method == "Annuitet"
