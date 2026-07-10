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


def test_sqb_istemol_krediti_ignores_unrelated_page_percentages():
    """The real consumer-credit page has a mortgage cross-sell banner (17%)
    before the rate table and a debt-ratio eligibility note (50%) after it.
    CATEGORY_HEADINGS must scope extraction to just the "Foiz stavkasi"
    table so those unrelated percentages don't pollute rate_min/rate_max."""
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = SQBScraper().run()

    istemol_krediti = next(p for p in products if p.category == "istemol_krediti")
    assert istemol_krediti.rate_min == 21.99
    assert istemol_krediti.rate_max == 25.99
    assert istemol_krediti.term_min_months == 36
    assert istemol_krediti.term_max_months == 60
    assert istemol_krediti.amount_max_som == 200_000_000
    # Collateral requirement lives outside the narrowed rate section, so it
    # must be checked against the full fetched page, not just that section.
    assert istemol_krediti.requires_collateral is True
