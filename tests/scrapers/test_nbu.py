from pathlib import Path
from unittest.mock import patch

from scrapers.nbu import NBUScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    NBUScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "nbu_avtokredit.html").read_text(encoding="utf-8"),
    NBUScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "nbu_mikroqarz.html").read_text(encoding="utf-8"),
    NBUScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "nbu_kredit_karta.html").read_text(encoding="utf-8"),
    NBUScraper.CATEGORY_URLS["istemol_krediti"]: (FIXTURES_DIR / "nbu_istemol_krediti.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_nbu_scraper_parses_all_four_categories():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = NBUScraper().run()

    assert mock_fetch.call_count == 4
    categories = {p.category for p in products}
    assert categories == {"avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"}
    assert all(p.bank == "NBU" for p in products)
