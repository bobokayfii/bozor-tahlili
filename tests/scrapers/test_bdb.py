from pathlib import Path
from unittest.mock import patch

from scrapers.bdb import BDBScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    BDBScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "bdb_avtokredit.html").read_text(encoding="utf-8"),
    BDBScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "bdb_mikroqarz.html").read_text(encoding="utf-8"),
    BDBScraper.CATEGORY_URLS["ipoteka_davlat"]: (FIXTURES_DIR / "bdb_ipoteka.html").read_text(encoding="utf-8"),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_bdb_avtokredit_parses_correctly():
    """"Ta'minot miqdori: Kredit summasining kamida 133.3% miqdorida"
    sits between the down-payment and grace-period lines — rate
    extraction is scoped to "Foiz stavkasi"->"Boshlang'ich badal"
    specifically so this stray collateral-ratio percentage never
    contaminates rate_max. No literal "garov" word appears on this page,
    so collateral is hardcoded True (vehicle-secured auto loan)."""
    with patch("scrapers.bdb.fetch_html", side_effect=_fake_fetch):
        products = BDBScraper().run()

    product = next(p for p in products if p.category == "avtokredit")
    assert product.bank == "BDB"
    assert product.rate_min == 23.0
    assert product.rate_max == 27.0
    assert product.term_min_months == 36
    assert product.term_max_months == 60
    assert product.amount_max_som == 800_000_000
    assert product.down_payment_pct == 25.0
    assert product.requires_collateral is True
    assert product.grace_period_months == 3
    assert product.payment_method == "Differensial"


def test_bdb_mikroqarz_parses_correctly():
    """"Kredit maqsadi" is the only occurrence of that heading on the
    page, so bracketing from there is safe even though "Kredit muddati"/
    "Kredit miqdori" each appear a second time within the bracketed
    block itself, as a term-tiered rate table's column header."""
    with patch("scrapers.bdb.fetch_html", side_effect=_fake_fetch):
        products = BDBScraper().run()

    product = next(p for p in products if p.category == "mikroqarz")
    assert product.rate_min == 25.0
    assert product.rate_max == 30.0
    assert product.term_min_months == 12
    assert product.term_max_months == 48
    assert product.amount_max_som == 100_000_000
    assert product.requires_collateral is True
    assert product.payment_method == "Annuitet, Differensial"


def test_bdb_ipoteka_davlat_parses_correctly():
    """Explicitly funded "Iqtisodiyot va moliya vazirligi mablag'lari
    hisobidan" (Ministry of Economy and Finance) — the clearest
    ipoteka_davlat match found in this batch. Term "20 yilgacha" (240
    months) exceeds extract_term_months' 120-month cap, same fix as
    aab.py's ipoteka_davlat."""
    with patch("scrapers.bdb.fetch_html", side_effect=_fake_fetch):
        products = BDBScraper().run()

    product = next(p for p in products if p.category == "ipoteka_davlat")
    assert product.product_name == "Birlamchi ipoteka"
    assert product.rate_min == 17.0
    assert product.rate_max == 17.0
    assert product.term_min_months == 240
    assert product.term_max_months == 240
    assert product.amount_max_som == 480_000_000
    assert product.down_payment_pct == 15.0
    assert product.requires_collateral is True
    assert product.grace_period_months == 6
    assert product.payment_method == "Annuitet, Differensial"
