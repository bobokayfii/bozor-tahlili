from pathlib import Path

from scrapers.sqb import SQBScraper

FIXTURE = Path(__file__).parent / "fixtures" / "sqb_sample.html"


def test_sqb_scraper_parses_all_four_categories():
    html = FIXTURE.read_text(encoding="utf-8")
    products = SQBScraper().parse(html)

    categories = {p.category for p in products}
    assert categories == {"avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"}
    assert all(p.bank == "SQB" for p in products)
