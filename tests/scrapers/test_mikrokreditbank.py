from pathlib import Path
from unittest.mock import patch

from scrapers.mikrokreditbank import MikrokreditBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    MikrokreditBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "mk_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    MikrokreditBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "mk_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    MikrokreditBankScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "mk_kredit_karta.html").read_text(
        encoding="utf-8"
    ),
    MikrokreditBankScraper.CATEGORY_URLS["istemol_krediti"]: (FIXTURES_DIR / "mk_istemol_krediti.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_mikrokreditbank_scraper_parses_all_four_categories():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = MikrokreditBankScraper().run()

    assert mock_fetch.call_count == 4
    categories = {p.category for p in products}
    assert categories == {"avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"}
    assert all(p.bank == "Mikrokreditbank" for p in products)


def test_mikrokreditbank_avtokredit_parses_correctly():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = MikrokreditBankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.rate_min == 24.0
    assert avtokredit.rate_max == 24.0
    assert avtokredit.term_min_months == 60
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 824_000_000
    assert avtokredit.requires_collateral is True


def test_mikrokreditbank_mikroqarz_parses_correctly():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = MikrokreditBankScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz")
    assert mikroqarz.rate_min == 24.0
    assert mikroqarz.rate_max == 28.0
    assert mikroqarz.term_min_months == 60
    assert mikroqarz.term_max_months == 60
    assert mikroqarz.amount_max_som == 100_000_000
    assert mikroqarz.requires_collateral is True


def test_mikrokreditbank_kredit_karta_parses_correctly():
    """"Kredit muddati" is stated as a bare "60 oy" (no "gacha" suffix) and
    the amount as a grouped exact sum ("100 000 000 so'mgacha") rather than
    "mln so'm" — both exercise the general fallback parsing added for
    InfinBank, confirming it isn't a one-bank special case."""
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = MikrokreditBankScraper().run()

    kredit_karta = next(p for p in products if p.category == "kredit_karta")
    assert kredit_karta.rate_min == 24.0
    assert kredit_karta.rate_max == 24.0
    assert kredit_karta.term_min_months == 60
    assert kredit_karta.term_max_months == 60
    assert kredit_karta.amount_max_som == 100_000_000


def test_mikrokreditbank_istemol_krediti_parses_correctly():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = MikrokreditBankScraper().run()

    istemol_krediti = next(p for p in products if p.category == "istemol_krediti")
    assert istemol_krediti.rate_min == 28.0
    assert istemol_krediti.rate_max == 28.0
    assert istemol_krediti.term_min_months == 60
    assert istemol_krediti.term_max_months == 60
    assert istemol_krediti.amount_max_som == 150_000_000
    assert istemol_krediti.requires_collateral is True
