from pathlib import Path
from unittest.mock import patch

from scrapers.anorbank import AnorbankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    AnorbankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "anorbank_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    AnorbankScraper.CATEGORY_URLS["avtokredit_brend_birlamchi"]: (
        FIXTURES_DIR / "anorbank_avtokredit4.html"
    ).read_text(encoding="utf-8"),
    AnorbankScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (FIXTURES_DIR / "anorbank_mikrozaym.html").read_text(
        encoding="utf-8"
    ),
    AnorbankScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "anorbank_kredit_karta.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_anorbank_avtokredit_parses_correctly():
    """Автокредит 3.0 — the base auto-loan product, with a stated down
    payment (40%) and a single flat rate (33%), unlike the 4.0 promo
    variant which is 0%."""
    with patch("scrapers.anorbank.fetch_html", side_effect=_fake_fetch):
        products = AnorbankScraper().run()

    product = next(p for p in products if p.category == "avtokredit")
    assert product.bank == "Anorbank"
    assert product.product_name == "Автокредит 3.0"
    assert product.rate_min == 33.0
    assert product.rate_max == 33.0
    assert product.term_min_months == 60
    assert product.term_max_months == 60
    assert product.amount_max_som == 400_000_000
    assert product.down_payment_pct == 40.0
    assert product.requires_collateral is True
    assert product.grace_period_months is None


def test_anorbank_avtokredit_ikkilamchi_matches_generic_avtokredit():
    """Автокредит 3.0's page explicitly notes that its rate/term fields
    also apply to secondary-market purchases ("Ikkilamchi bozordan
    Avtokredit tanlash jarayonida...") — one product covers both markets,
    so the same page/values are also mapped to avtokredit_ikkilamchi."""
    with patch("scrapers.anorbank.fetch_html", side_effect=_fake_fetch):
        products = AnorbankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    ikkilamchi = next(p for p in products if p.category == "avtokredit_ikkilamchi")
    assert ikkilamchi.product_name == avtokredit.product_name
    assert ikkilamchi.rate_min == avtokredit.rate_min
    assert ikkilamchi.rate_max == avtokredit.rate_max
    assert ikkilamchi.term_min_months == avtokredit.term_min_months
    assert ikkilamchi.term_max_months == avtokredit.term_max_months
    assert ikkilamchi.amount_max_som == avtokredit.amount_max_som
    assert ikkilamchi.requires_collateral is True


def test_anorbank_avtokredit_brend_birlamchi_parses_correctly():
    """Автокредит 4.0 — UzAuto Motors (Onix/Tracker/Damas) promo, 0% flat
    rate. The 0% is the page's own single stated figure (not a range), so
    rate_min and rate_max are both 0.0."""
    with patch("scrapers.anorbank.fetch_html", side_effect=_fake_fetch):
        products = AnorbankScraper().run()

    product = next(p for p in products if p.category == "avtokredit_brend_birlamchi")
    assert product.product_name == "Автокредит 4.0"
    assert product.rate_min == 0.0
    assert product.rate_max == 0.0
    assert product.term_min_months == 60
    assert product.term_max_months == 60
    assert product.amount_max_som == 500_000_000
    assert product.down_payment_pct == 25.0
    assert product.requires_collateral is True


def test_anorbank_mikrozaym_onlayn_parses_correctly():
    """Удобный микрозайм — unsecured, no down payment, no repayment-method
    selector on the page (confirmed by direct inspection: no "Annuitet"/
    "Differensial" text anywhere on this page, unlike the two auto-loan
    pages which have a payment-method calculator widget)."""
    with patch("scrapers.anorbank.fetch_html", side_effect=_fake_fetch):
        products = AnorbankScraper().run()

    product = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert product.product_name == "Удобный микрозайм"
    assert product.rate_min == 27.0
    assert product.rate_max == 49.0
    assert product.term_min_months == 36
    assert product.term_max_months == 36
    assert product.amount_max_som == 100_000_000
    assert product.down_payment_pct is None
    assert product.requires_collateral is False
    assert product.payment_method is None


def test_anorbank_kredit_karta_parses_correctly():
    """"ANOR nasiya muddatli to'lov kartasi" — hamkorlar tarmog'ida
    foydalanilganda komissiya 0% (haqiqiy foiz stavkasi yo'q, boshqa
    kartaga o'tkazmalar uchun muddatga bog'liq komissiya bor, lekin bu
    "foiz stavkasi" emas). Karta 48 oy amal qiladi, shartnoma muddati 36
    oy — ikkalasi ham sahifada aniq yozilgan."""
    with patch("scrapers.anorbank.fetch_html", side_effect=_fake_fetch):
        products = AnorbankScraper().run()

    product = next(p for p in products if p.category == "kredit_karta")
    assert product.product_name == "ANOR nasiya muddatli to'lov kartasi"
    assert product.rate_min == 0.0
    assert product.rate_max == 0.0
    assert product.term_min_months == 36
    assert product.term_max_months == 48
    assert product.amount_max_som == 50_000_000
    assert product.down_payment_pct is None
    assert product.requires_collateral is False
    assert product.payment_method == "Differensial"
