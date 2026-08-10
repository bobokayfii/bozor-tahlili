from pathlib import Path
from unittest.mock import patch

from scrapers.ofb import OFBScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    OFBScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "ofb_avtokredit.html").read_text(encoding="utf-8"),
    OFBScraper.CATEGORY_URLS["avtokredit_elektro"]: (FIXTURES_DIR / "ofb_avtokredit_elektro.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_ofb_scraper_parses_both_categories():
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = OFBScraper().run()

    assert mock_fetch.call_count == 2
    categories = {p.category for p in products}
    assert categories == {"avtokredit", "avtokredit_elektro"}
    assert all(p.bank == "OFB" for p in products)


def test_ofb_avtokredit_ignores_down_payment_share_percentages():
    """The real "Foiz stavkasi qancha?" table has two kinds of percentage
    per row — the down-payment SHARE (25/30/40/50%) and the actual annual
    rate that share unlocks (24,5/23,9/22,9/21,9%). A naive
    extract_percentages over that block would blend both sets together
    and push rate_max up to a bogus 50%; only the number after "dan —"
    should be picked up."""
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch):
        products = OFBScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.product_name == "Oson avtokredit"
    assert avtokredit.rate_min == 21.9
    assert avtokredit.rate_max == 24.5
    assert avtokredit.term_min_months == 60
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 800_000_000
    assert avtokredit.down_payment_pct == 25.0
    assert avtokredit.requires_collateral is True
    assert avtokredit.grace_period_months is None
    assert avtokredit.payment_method is None


def test_ofb_avtokredit_elektro_parses_dual_term_and_no_yillik_rate_table():
    """"Avtokredit BYD" shares the exact same FAQ template as "Oson
    avtokredit" but with different numbers: the term is stated as "36
    yoki 60 oyga" (two explicit options, no "oygacha" suffix, so the
    generic extract_term_months regex doesn't match it) and the rate
    table omits the word "yillik" entirely (unlike the plain avtokredit
    page) — both quirks are handled by dedicated regexes."""
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch):
        products = OFBScraper().run()

    elektro = next(p for p in products if p.category == "avtokredit_elektro")
    assert elektro.product_name == "Avtokredit BYD"
    assert elektro.rate_min == 18.9
    assert elektro.rate_max == 21.5
    assert elektro.term_min_months == 36
    assert elektro.term_max_months == 60
    assert elektro.amount_max_som == 800_000_000
    assert elektro.down_payment_pct == 25.0
    assert elektro.requires_collateral is True
    assert elektro.grace_period_months is None
    assert elektro.payment_method is None
