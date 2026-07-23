from pathlib import Path
from unittest.mock import patch

from scrapers.ipakyuli import IpakYuliBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    IpakYuliBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "ipak_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    IpakYuliBankScraper.CATEGORY_URLS["avtokredit_ikkilamchi"]: (
        FIXTURES_DIR / "ipak_avtokredit_ikkilamchi.html"
    ).read_text(encoding="utf-8"),
    IpakYuliBankScraper.CATEGORY_URLS["avtokredit_brend_birlamchi"]: (
        FIXTURES_DIR / "ipak_avtokredit_brend_birlamchi.html"
    ).read_text(encoding="utf-8"),
    IpakYuliBankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (
        FIXTURES_DIR / "ipak_ipoteka_tijorat.html"
    ).read_text(encoding="utf-8"),
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
    with patch("scrapers.ipakyuli.fetch_html", side_effect=_fake_fetch):
        products = IpakYuliBankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.bank == "Ipak Yo'li Bank"
    assert avtokredit.product_name == "Birlamchi bozor avtokrediti"
    # Full 6-row rate table spans 20.9%-24.9% across 12-60 month terms —
    # previously only the first row (20.9%/60 months) was captured.
    assert avtokredit.rate_min == 20.9
    assert avtokredit.rate_max == 24.9
    assert avtokredit.term_min_months == 12
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 800_000_000
    assert avtokredit.down_payment_pct == 25.0
    assert avtokredit.grace_period_months is None
    assert avtokredit.payment_method is None
    assert avtokredit.requires_collateral is True


def test_ipakyuli_avtokredit_ikkilamchi_parses_correctly():
    """"Ikkilamchi bozor uchun avtomobil krediti" — 6-row rate table with
    a down-payment column that mixes plain percentages ("25%") and ranges
    ("25% dan 49,99% gacha", itself containing a comma-decimal number) —
    the rate/term extraction must not be confused by the range's own
    percentages."""
    with patch("scrapers.ipakyuli.fetch_html", side_effect=_fake_fetch):
        products = IpakYuliBankScraper().run()

    ikkilamchi = next(p for p in products if p.category == "avtokredit_ikkilamchi")
    assert ikkilamchi.product_name == "Ikkilamchi bozor uchun avtomobil krediti"
    assert ikkilamchi.rate_min == 20.9
    assert ikkilamchi.rate_max == 24.9
    assert ikkilamchi.term_min_months == 12
    assert ikkilamchi.term_max_months == 60
    assert ikkilamchi.amount_max_som == 800_000_000
    assert ikkilamchi.down_payment_pct == 25.0
    assert ikkilamchi.grace_period_months is None
    assert ikkilamchi.payment_method is None
    assert ikkilamchi.requires_collateral is True


def test_ipakyuli_avtokredit_brend_birlamchi_parses_correctly():
    """"Volkswagen uchun avtokredit" — rasmiy dilerdan yangi Volkswagen/
    Jetta avtomobili uchun. "Foiz stavkasi haqida" bo'limida 3 ta mustaqil
    narx jadvali bor (rasmiy daromadli/davlat tashkiloti xodimlari/
    norasmiy daromadli), har biri 25%/50% boshlang'ich to'lov ulushi x
    12-60 oy muddat bo'yicha guruhlangan; ulush yorlig'i butun son ("25%"),
    haqiqiy stavkalar esa doim vergul-kasr ("20,9%") — shu farq orqali
    ajratiladi."""
    with patch("scrapers.ipakyuli.fetch_html", side_effect=_fake_fetch):
        products = IpakYuliBankScraper().run()

    brend = next(p for p in products if p.category == "avtokredit_brend_birlamchi")
    assert brend.product_name == "Volkswagen uchun avtokredit"
    assert brend.rate_min == 20.9
    assert brend.rate_max == 24.9
    assert brend.term_min_months == 12
    assert brend.term_max_months == 60
    assert brend.amount_max_som == 800_000_000
    assert brend.down_payment_pct == 25.0
    assert brend.grace_period_months is None
    assert brend.payment_method == "Annuitet, Differensial"
    assert brend.requires_collateral is True


def test_ipakyuli_ipoteka_tijorat_parses_correctly():
    """"Ipoteka-24" — bankning o'z mablag'i hisobidan (davlat mablag'i
    haqida hech qanday ishora yo'q) birlamchi/ikkilamchi bozordan ko'chmas
    mulk sotib olish uchun. "Foiz stavkalari haqida batafsil" jadvali
    mijoz toifasi x muddat (84/120 oygacha) bo'yicha guruhlangan, xuddi
    Volkswagen sahifasi bilan bir xil naqsh (vergul-kasr stavka, 2 xonali
    butun son badal ulushi), lekin muddat "N oygacha" shaklida (bare "N
    oy" emas), shu sabab alohida regex ishlatiladi."""
    with patch("scrapers.ipakyuli.fetch_html", side_effect=_fake_fetch):
        products = IpakYuliBankScraper().run()

    tijorat = next(p for p in products if p.category == "ipoteka_tijorat")
    assert tijorat.product_name == "Ipoteka-24"
    assert tijorat.rate_min == 21.9
    assert tijorat.rate_max == 24.9
    assert tijorat.term_min_months == 84
    assert tijorat.term_max_months == 120
    assert tijorat.amount_max_som == 1_500_000_000
    assert tijorat.down_payment_pct == 20.0
    assert tijorat.grace_period_months is None
    assert tijorat.payment_method == "Annuitet, Differensial"
    assert tijorat.requires_collateral is True


def test_ipakyuli_mikroqarz_parses_correctly():
    """"Kafillik asosidagi mikroqarz" table lists three rate/term rows
    (25,9%/12 oygacha, 26,9%/24 oygacha, 28,9%/36 oygacha) with the amount
    ("100 mln so'mgacha") stated once, applying to all three rows."""
    with patch("scrapers.ipakyuli.fetch_html", side_effect=_fake_fetch):
        products = IpakYuliBankScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz")
    assert mikroqarz.product_name == "Kafillik asosida mikroqarz"
    assert mikroqarz.rate_min == 25.9
    assert mikroqarz.rate_max == 28.9
    assert mikroqarz.term_min_months == 12
    assert mikroqarz.term_max_months == 36
    assert mikroqarz.amount_max_som == 100_000_000
    assert mikroqarz.grace_period_months is None
    assert mikroqarz.payment_method is None
    # "Kafillik asosidagi mikroqarz" explicitly does not require property
    # collateral (guarantor/insurance-policy based instead).
    assert mikroqarz.requires_collateral is False


def test_ipakyuli_kredit_karta_and_istemol_krediti_yield_no_product():
    """kredit_karta ("Imkoniyatlar" card) is an interest-free-period +
    cashback product with no stated APR, and istemol_krediti's page states
    no concrete amount or rate at all ("dastur shartlariga bog'liq").
    Neither page gives _build_product enough to work with, so both are
    correctly skipped rather than filled in with guesses."""
    with patch("scrapers.ipakyuli.fetch_html", side_effect=_fake_fetch):
        products = IpakYuliBankScraper().run()

    categories = {p.category for p in products}
    assert "kredit_karta" not in categories
    assert "istemol_krediti" not in categories
