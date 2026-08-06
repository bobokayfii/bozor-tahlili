from pathlib import Path
from unittest.mock import patch

from scrapers.aab import AsiaAllianceBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    AsiaAllianceBankScraper.CATEGORY_URLS["avtokredit_ikkilamchi"]: (
        FIXTURES_DIR / "aab_avtokredit_ikkilamchi.html"
    ).read_text(encoding="utf-8"),
    AsiaAllianceBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "aab_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    AsiaAllianceBankScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (
        FIXTURES_DIR / "aab_mikroqarz_onlayn.html"
    ).read_text(encoding="utf-8"),
    AsiaAllianceBankScraper.CATEGORY_URLS["ipoteka_davlat"]: (FIXTURES_DIR / "aab_ipoteka_davlat.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_aab_avtokredit_ikkilamchi_parses_correctly():
    with patch("scrapers.aab.fetch_html", side_effect=_fake_fetch):
        products = AsiaAllianceBankScraper().run()

    product = next(p for p in products if p.category == "avtokredit_ikkilamchi")
    assert product.bank == "Asia Alliance Bank"
    assert product.product_name == "Avtokredit «Ikkilamchi»"
    assert product.rate_min == 26.0
    assert product.rate_max == 28.0
    assert product.term_min_months == 60
    assert product.term_max_months == 60
    assert product.amount_max_som == 400_000_000
    assert product.down_payment_pct == 25.0
    assert product.requires_collateral is True
    assert product.grace_period_months == 0
    assert product.payment_method == "Annuitet, Differensial"


def test_aab_mikroqarz_parses_correctly():
    """Mikroqarz «Imkon» — processed at a bank branch ("Kreditni
    rasmiylashtirish usuli: Bank ofisi"), not online, so this is the
    offline mikroqarz category, distinct from mikrozaym-online-'s
    mikroqarz_onlayn below. No down-payment field exists on this page at
    all (unsecured-style product), unlike the auto-loan pages."""
    with patch("scrapers.aab.fetch_html", side_effect=_fake_fetch):
        products = AsiaAllianceBankScraper().run()

    product = next(p for p in products if p.category == "mikroqarz")
    assert product.product_name == "Mikroqarz «Imkon»"
    assert product.rate_min == 21.0
    assert product.rate_max == 26.0
    assert product.term_min_months == 60
    assert product.term_max_months == 60
    assert product.amount_max_som == 100_000_000
    assert product.down_payment_pct is None
    assert product.requires_collateral is True
    assert product.grace_period_months == 0


def test_aab_mikroqarz_onlayn_parses_correctly():
    """Mikroqarz «Online» — "Kreditni rasmiylashtirish usuli: Mobil ilova"
    confirms this is the online variant. "Kredit ta'minoti: Ta'minot
    talab etilmaydi" contains no "garov" at all, so the generic
    has_collateral_requirement scoped to just this sentence correctly
    resolves to False without needing an override."""
    with patch("scrapers.aab.fetch_html", side_effect=_fake_fetch):
        products = AsiaAllianceBankScraper().run()

    product = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert product.product_name == "Mikroqarz «Online»"
    assert product.rate_min == 25.0
    assert product.rate_max == 38.0
    assert product.term_min_months == 36
    assert product.term_max_months == 36
    assert product.amount_max_som == 100_000_000
    assert product.requires_collateral is False


def test_aab_ipoteka_davlat_parses_correctly():
    """Ipoteka krediti - Yangi uy — explicitly funded "O'zbekiston
    Respublikasi Iqtisodiyot va moliya vazirligi mablag'lari hisobidan"
    (Ministry of Economy and Finance), the clearest ipoteka_davlat match
    among AAB's mortgage pages. Amount is stated as two regional caps
    ("480 mln so'mgacha" Tashkent / "380 mln so'mgacha" elsewhere) —
    extract_amount_som takes the max of both, 480mln. Down payment is
    worded "15 foizidan" (word "foiz", no % sign) and term is "240
    oygacha" (exceeds extract_term_months' 120-month cap) — both need
    the bespoke handling documented in _build_product_from_template."""
    with patch("scrapers.aab.fetch_html", side_effect=_fake_fetch):
        products = AsiaAllianceBankScraper().run()

    product = next(p for p in products if p.category == "ipoteka_davlat")
    assert product.rate_min == 17.0
    assert product.rate_max == 18.0
    assert product.term_min_months == 240
    assert product.term_max_months == 240
    assert product.amount_max_som == 480_000_000
    assert product.down_payment_pct == 15.0
    assert product.requires_collateral is True
    assert product.grace_period_months == 6
