from pathlib import Path
from unittest.mock import patch

from scrapers.ipoteka import IpotekaBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    IpotekaBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "ipoteka_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    IpotekaBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "ipoteka_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    IpotekaBankScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "ipoteka_kredit_karta.html").read_text(
        encoding="utf-8"
    ),
    IpotekaBankScraper.CATEGORY_URLS["istemol_krediti"]: (FIXTURES_DIR / "ipoteka_istemol_krediti.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_ipoteka_scraper_parses_all_four_categories():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = IpotekaBankScraper().run()

    assert mock_fetch.call_count == 4
    categories = {p.category for p in products}
    assert categories == {"avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"}
    assert all(p.bank == "Ipoteka Bank" for p in products)
