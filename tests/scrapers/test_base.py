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


def test_force_collateral_overrides_text_detection():
    """Some products (e.g. auto loans) are always collateralized by the
    purchased vehicle by convention, even when the page never says "garov"
    explicitly. FORCE_COLLATERAL lets a scraper assert that fact directly
    instead of relying on unreliable text detection."""

    class ForcedCollateralScraper(TextSectionScraper):
        bank_name = "FakeBank"
        url = "https://fakebank.uz/kredit"
        CATEGORY_HEADINGS = {
            "avtokredit": ("Avtokredit", "Mikroqarz"),
            "mikroqarz": ("Mikroqarz", None),
        }
        FORCE_COLLATERAL = {"avtokredit": True}

    products = ForcedCollateralScraper().parse(SAMPLE_HTML)
    avtokredit = next(p for p in products if p.category == "avtokredit")
    mikroqarz = next(p for p in products if p.category == "mikroqarz")

    assert avtokredit.requires_collateral is True
    # mikroqarz has no FORCE_COLLATERAL entry, so text detection still applies.
    assert mikroqarz.requires_collateral is False


def test_run_calls_fetch_html_then_parse():
    scraper = FakeBankScraper()
    with patch("scrapers.base.fetch_html", return_value=SAMPLE_HTML) as mock_fetch:
        products = scraper.run()

    mock_fetch.assert_called_once_with("https://fakebank.uz/kredit", extra_ca_cert=None)
    assert len(products) == 2


def test_parse_skips_category_when_fields_missing():
    class IncompleteScraper(TextSectionScraper):
        bank_name = "IncompleteBank"
        url = "https://incomplete.uz"
        CATEGORY_HEADINGS = {"kredit_karta": ("Kredit karta", None)}

    products = IncompleteScraper().parse("<html><body><p>Hech qanday mos ma'lumot yo'q</p></body></html>")
    assert products == []


AVTOKREDIT_PAGE_HTML = """
<html><body>
<p>Noise before heading: 99% dan 99% gacha shouldn't be picked up.</p>
<h2>Avtokredit garovi</h2>
<p>Yillik foiz stavkasi: 20% dan 22% gacha. Muddati: 6 oydan 48 oygacha.
Kredit miqdori: 500 mln.so'mgacha. Kredit kafolati: garov talab qilinadi.</p>
</body></html>
"""

MIKROQARZ_PAGE_HTML = """
<html><body>
<p>Yillik foiz stavkasi: 30% dan 33% gacha. Muddati: 3 oydan 24 oygacha.
Kredit miqdori: 50 mln.so'mgacha. Kredit kafolati: Mavjud emas.</p>
</body></html>
"""


class MultiPageScraper(TextSectionScraper):
    bank_name = "MultiBank"
    url = "https://multibank.uz"
    CATEGORY_HEADINGS = {"avtokredit": ("Avtokredit garovi", None)}
    CATEGORY_URLS = {
        "avtokredit": "https://multibank.uz/avtokredit",
        "mikroqarz": "https://multibank.uz/mikroqarz",
    }


def test_run_fetches_each_category_url_when_category_urls_set():
    page_by_url = {
        "https://multibank.uz/avtokredit": AVTOKREDIT_PAGE_HTML,
        "https://multibank.uz/mikroqarz": MIKROQARZ_PAGE_HTML,
    }

    def fake_fetch(url, *args, **kwargs):
        return page_by_url[url]

    with patch("scrapers.base.fetch_html", side_effect=fake_fetch) as mock_fetch:
        products = MultiPageScraper().run()

    assert mock_fetch.call_count == 2
    mock_fetch.assert_any_call("https://multibank.uz/avtokredit", extra_ca_cert=None)
    mock_fetch.assert_any_call("https://multibank.uz/mikroqarz", extra_ca_cert=None)

    assert len(products) == 2
    avtokredit = next(p for p in products if p.category == "avtokredit")
    mikroqarz = next(p for p in products if p.category == "mikroqarz")

    # avtokredit uses CATEGORY_HEADINGS to narrow the section, so the noise
    # percentage before the heading must not leak into the extracted rates.
    assert avtokredit.rate_min == 20
    assert avtokredit.rate_max == 22
    assert avtokredit.requires_collateral is True
    assert avtokredit.source_url == "https://multibank.uz/avtokredit"

    # mikroqarz has no CATEGORY_HEADINGS entry, so the whole fetched page
    # text is treated as the section.
    assert mikroqarz.rate_min == 30
    assert mikroqarz.rate_max == 33
    assert mikroqarz.requires_collateral is False
    assert mikroqarz.source_url == "https://multibank.uz/mikroqarz"


def test_run_uses_single_fetch_path_when_category_urls_is_none():
    assert TextSectionScraper.CATEGORY_URLS is None
