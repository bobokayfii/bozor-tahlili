from pathlib import Path
from unittest.mock import patch

from scrapers.ofb import OFBScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    OFBScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "ofb_avtokredit.html").read_text(encoding="utf-8"),
    OFBScraper.CATEGORY_URLS["avtokredit_elektro"]: (FIXTURES_DIR / "ofb_avtokredit_elektro.html").read_text(
        encoding="utf-8"
    ),
    OFBScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "ofb_mikroqarzlar.html").read_text(encoding="utf-8"),
    OFBScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (FIXTURES_DIR / "ofb_onlayn_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_ofb_scraper_parses_all_categories():
    """mikroqarz and mikroqarz_onlayn share ONE fetch of the mikroqarzlar
    hub page (mikroqarz_onlayn also fetches its own onlayn-mikroqarz page
    for the term) — so 4 categories produce only 4 total fetch_html calls,
    not 5, confirming the hub page isn't fetched twice."""
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = OFBScraper().run()

    assert mock_fetch.call_count == 4
    categories = {p.category for p in products}
    assert categories == {"avtokredit", "avtokredit_elektro", "mikroqarz", "mikroqarz_onlayn"}
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


def test_ofb_mikroqarz_parses_ishonch_card_from_shared_hub_page():
    """"Ishonch mikroqarz" is the SECOND card on the mikroqarzlar hub page
    (after "Onlayn mikroqarz"). The bare word "Ishonch" also appears much
    earlier on the same page inside an unrelated nav dropdown ("OFB
    Ishonch" — a savings product, "OFB Ishonchli" — a business loan), so a
    naive extract_section(hub_text, "Ishonch", ...) over the full page
    would anchor on the wrong, much earlier occurrence; the real
    implementation first narrows to the text after "Onlayn mikroqarz"
    (unique on the page) before looking for "Ishonch"."""
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch):
        products = OFBScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz")
    assert mikroqarz.product_name == "Ishonch mikroqarz"
    assert mikroqarz.rate_min == 24.0
    assert mikroqarz.rate_max == 24.0
    assert mikroqarz.term_min_months == 36
    assert mikroqarz.term_max_months == 36
    assert mikroqarz.amount_max_som == 100_000_000
    assert mikroqarz.requires_collateral is False
    assert mikroqarz.down_payment_pct is None
    assert mikroqarz.grace_period_months is None
    assert mikroqarz.payment_method is None
    assert mikroqarz.source_url == OFBScraper.CATEGORY_URLS["mikroqarz"]


def test_ofb_mikroqarz_onlayn_combines_hub_amount_rate_with_own_page_term():
    """"Onlayn mikroqarz" is the FIRST card on the shared hub page (amount
    and rate come from there), but the hub page never states its term —
    that's only on the product's own onlayn-mikroqarz page ("Mikroqarz
    muddati: 24 oygacha."). This confirms both sources get combined into
    one product without a second, redundant hub fetch (see
    test_ofb_scraper_parses_all_categories for the call-count check)."""
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch):
        products = OFBScraper().run()

    onlayn = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert onlayn.product_name == "Onlayn mikroqarz"
    assert onlayn.rate_min == 30.0
    assert onlayn.rate_max == 30.0
    assert onlayn.term_min_months == 24
    assert onlayn.term_max_months == 24
    assert onlayn.amount_max_som == 50_000_000
    assert onlayn.requires_collateral is False
    assert onlayn.down_payment_pct is None
    assert onlayn.grace_period_months is None
    assert onlayn.payment_method is None
    assert onlayn.source_url == OFBScraper.CATEGORY_URLS["mikroqarz_onlayn"]
