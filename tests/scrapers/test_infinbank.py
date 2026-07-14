from pathlib import Path
from unittest.mock import patch

from scrapers.infinbank import InfinBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    InfinBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "infin_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    InfinBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "infin_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    InfinBankScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "infin_kredit_karta.html").read_text(
        encoding="utf-8"
    ),
    InfinBankScraper.CATEGORY_URLS["istemol_krediti"]: (FIXTURES_DIR / "infin_istemol_krediti.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_infinbank_scraper_fetches_all_four_category_urls():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        InfinBankScraper().run()

    assert mock_fetch.call_count == 4
    mock_fetch.assert_any_call(
        InfinBankScraper.CATEGORY_URLS["avtokredit"], extra_ca_cert="infinbank_intermediate.pem"
    )


def test_infinbank_mikroqarz_parses_correctly():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = InfinBankScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz")
    assert mikroqarz.bank == "InfinBank"
    assert mikroqarz.rate_min == 28.99
    assert mikroqarz.rate_max == 28.99
    assert mikroqarz.term_min_months == 36
    assert mikroqarz.term_max_months == 36
    assert mikroqarz.amount_max_som == 100_000_000
    assert mikroqarz.requires_collateral is True


def test_infinbank_istemol_krediti_parses_correctly():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = InfinBankScraper().run()

    istemol_krediti = next(p for p in products if p.category == "istemol_krediti")
    assert istemol_krediti.rate_min == 37.99
    assert istemol_krediti.rate_max == 37.99
    assert istemol_krediti.term_min_months == 18
    assert istemol_krediti.term_max_months == 18
    # Page states the exact sum ("41 200 000 so'mgacha"), not "mln so'm".
    assert istemol_krediti.amount_max_som == 41_200_000
    assert istemol_krediti.requires_collateral is True


def test_infinbank_avtokredit_yields_no_product_because_amount_is_unstated():
    """The avtokredit page prices loans against the vehicle's actual price
    ("Аvtotransport vositasining qiymatiga qarab") rather than a stated
    ceiling in so'm, across all of its variants. _build_product correctly
    skips a category it cannot find a concrete amount for, rather than
    fabricating one."""
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = InfinBankScraper().run()

    assert not any(p.category == "avtokredit" for p in products)


def test_infinbank_kredit_karta_yields_no_product_because_term_is_unstated():
    """The InfinBLACK tariff table states a clean rate and limit, but its
    "5 yil" limit-validity figure lives in a separate, noisier part of the
    page (an interactive calculator widget whose slider marks and fee
    percentages would contaminate rate extraction if the section were
    widened to include it). No term is extracted from the clean section,
    so _build_product correctly skips this category rather than guessing."""
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = InfinBankScraper().run()

    assert not any(p.category == "kredit_karta" for p in products)
