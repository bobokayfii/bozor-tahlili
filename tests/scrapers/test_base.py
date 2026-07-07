from unittest.mock import patch

from scrapers.base import Product, TextSectionScraper

SAMPLE_HTML = """
<html><body>
<h2>Avtokredit</h2>
<p>Yillik foiz stavkasi: 24.9% dan 27,9% gacha. Muddati: 12 oydan 60 oygacha.
Kredit miqdori: 800 mln.so'mgacha.
Kredit kafolati: Sotib olingan avtomobil garov sifatida olinadi.</p>
<h2>Mikroqarz</h2>
<p>Yillik foiz stavkasi: 28% dan 31% gacha. Muddati: 3 oydan 36 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Mavjud emas.</p>
</body></html>
"""


class FakeBankScraper(TextSectionScraper):
    bank_name = "FakeBank"
    url = "https://fakebank.uz/kredit"
    CATEGORY_HEADINGS = {
        "avtokredit": ("Avtokredit", "Mikroqarz"),
        "mikroqarz": ("Mikroqarz", None),
    }


def test_parse_returns_one_product_per_category():
    scraper = FakeBankScraper()
    products = scraper.parse(SAMPLE_HTML)

    assert len(products) == 2
    categories = {p.category for p in products}
    assert categories == {"avtokredit", "mikroqarz"}


def test_parse_extracts_correct_fields_for_avtokredit():
    scraper = FakeBankScraper()
    products = scraper.parse(SAMPLE_HTML)
    avtokredit = next(p for p in products if p.category == "avtokredit")

    assert isinstance(avtokredit, Product)
    assert avtokredit.bank == "FakeBank"
    assert avtokredit.rate_min == 24.9
    assert avtokredit.rate_max == 27.9
    assert avtokredit.term_min_months == 12
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 800_000_000
    assert avtokredit.requires_collateral is True


def test_parse_marks_mikroqarz_as_collateral_free():
    scraper = FakeBankScraper()
    products = scraper.parse(SAMPLE_HTML)
    mikroqarz = next(p for p in products if p.category == "mikroqarz")

    assert mikroqarz.requires_collateral is False


def test_run_calls_fetch_html_then_parse():
    scraper = FakeBankScraper()
    with patch("scrapers.base.fetch_html", return_value=SAMPLE_HTML) as mock_fetch:
        products = scraper.run()

    mock_fetch.assert_called_once_with("https://fakebank.uz/kredit")
    assert len(products) == 2


def test_parse_skips_category_when_fields_missing():
    class IncompleteScraper(TextSectionScraper):
        bank_name = "IncompleteBank"
        url = "https://incomplete.uz"
        CATEGORY_HEADINGS = {"kredit_karta": ("Kredit karta", None)}

    products = IncompleteScraper().parse("<html><body><p>Hech qanday mos ma'lumot yo'q</p></body></html>")
    assert products == []
