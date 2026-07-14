from pathlib import Path
from unittest.mock import patch

from scrapers.ipakyuli import IpakYuliBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    IpakYuliBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "ipak_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    IpakYuliBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "ipak_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    IpakYuliBankScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "ipak_kredit_karta.html").read_text(
        encoding="utf-8"
    ),
    IpakYuliBankScraper.CATEGORY_URLS["istemol_krediti"]: (FIXTURES_DIR / "ipak_istemol_krediti.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_ipakyuli_avtokredit_parses_correctly():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = IpakYuliBankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.bank == "Ipak Yo'li Bank"
    assert avtokredit.rate_min == 20.9
    assert avtokredit.rate_max == 20.9
    assert avtokredit.term_min_months == 60
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 800_000_000
    assert avtokredit.requires_collateral is True


def test_ipakyuli_mikroqarz_parses_correctly():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = IpakYuliBankScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz")
    assert mikroqarz.rate_min == 25.9
    assert mikroqarz.rate_max == 25.9
    assert mikroqarz.term_min_months == 12
    assert mikroqarz.term_max_months == 12
    assert mikroqarz.amount_max_som == 100_000_000
    # "Kafillik asosidagi mikroqarz" explicitly does not require property
    # collateral (guarantor/insurance-policy based instead).
    assert mikroqarz.requires_collateral is False


def test_ipakyuli_kredit_karta_and_istemol_krediti_yield_no_product():
    """kredit_karta ("Imkoniyatlar" card) is an interest-free-period +
    cashback product with no stated APR, and istemol_krediti's page states
    no concrete amount or rate at all ("dastur shartlariga bog'liq").
    Neither page gives _build_product enough to work with, so both are
    correctly skipped rather than filled in with guesses."""
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = IpakYuliBankScraper().run()

    categories = {p.category for p in products}
    assert "kredit_karta" not in categories
    assert "istemol_krediti" not in categories
