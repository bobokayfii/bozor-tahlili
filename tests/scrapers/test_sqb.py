from pathlib import Path
from unittest.mock import patch

from scrapers.sqb import SQBScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    SQBScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "sqb_avtokredit.html").read_text(encoding="utf-8"),
    SQBScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "sqb_mikroqarz.html").read_text(encoding="utf-8"),
    SQBScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "sqb_kredit_karta.html").read_text(encoding="utf-8"),
    SQBScraper.CATEGORY_URLS["istemol_krediti"]: (FIXTURES_DIR / "sqb_istemol_krediti.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_sqb_scraper_parses_all_four_categories():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = SQBScraper().run()

    assert mock_fetch.call_count == 4
    categories = {p.category for p in products}
    assert categories == {"avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"}
    assert all(p.bank == "SQB" for p in products)
