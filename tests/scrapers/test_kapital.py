from pathlib import Path
from unittest.mock import patch

from scrapers.kapital import KapitalBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    KapitalBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "kapital_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    KapitalBankScraper.CATEGORY_URLS["avtokredit_ikkilamchi"]: (
        FIXTURES_DIR / "kapital_avtokredit_ikkilamchi.html"
    ).read_text(encoding="utf-8"),
    KapitalBankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (
        FIXTURES_DIR / "kapital_ipoteka_tijorat.html"
    ).read_text(encoding="utf-8"),
    KapitalBankScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (
        FIXTURES_DIR / "kapital_mikroqarz_onlayn.html"
    ).read_text(encoding="utf-8"),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_kapital_avtokredit_parses_correctly():
    with patch("scrapers.kapital.fetch_html", side_effect=_fake_fetch):
        products = KapitalBankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.bank == "Kapitalbank"
    assert avtokredit.rate_min == 0.0
    assert avtokredit.rate_max == 0.0
    assert avtokredit.term_min_months == 18
    assert avtokredit.term_max_months == 36
    assert avtokredit.amount_max_som == 300_000_000
    assert avtokredit.requires_collateral is True
    assert avtokredit.product_name == "Qulay Nasiya (Cobalt)"
    assert avtokredit.down_payment_pct == 30.0
    # Sahifada umuman tilga olinmagan — noma'lum, taxmin qilinmaydi.
    assert avtokredit.grace_period_months is None
    assert avtokredit.payment_method is None


def test_kapital_avtokredit_ikkilamchi_parses_correctly():
    """"Kapitalbankdan Avto Nasiya (ikkilamchi)" — same BNPL-style 0%
    dealer-markup mikrokredit structure as the primary-market "Qulay
    Nasiya (Cobalt)" product. "O'z ishtiroki" lists three product variants
    (base 20%, plyus 30%, Elektro 35%); the minimum (20%) matches the base
    variant used for this product's own name. Grace period is stated as
    "Imtiyoz davri" (without the "-li" suffix extract_grace_period_months
    normally requires) but still resolves to 0 via the "imtiyozli" prefix
    trick, since the real negative signal ("mavjud emas") is present."""
    with patch("scrapers.kapital.fetch_html", side_effect=_fake_fetch):
        products = KapitalBankScraper().run()

    ikkilamchi = next(p for p in products if p.category == "avtokredit_ikkilamchi")
    assert ikkilamchi.bank == "Kapitalbank"
    assert ikkilamchi.product_name == "Kapitalbankdan Avto Nasiya (ikkilamchi)"
    assert ikkilamchi.rate_min == 0.0
    assert ikkilamchi.rate_max == 0.0
    assert ikkilamchi.term_min_months == 12
    assert ikkilamchi.term_max_months == 48
    assert ikkilamchi.amount_max_som == 300_000_000
    assert ikkilamchi.down_payment_pct == 20.0
    assert ikkilamchi.grace_period_months == 0
    assert ikkilamchi.payment_method is None
    assert ikkilamchi.requires_collateral is True


def test_kapital_ipoteka_tijorat_parses_correctly():
    """"Qulay uy ipoteka krediti" — bankning o'z mablag'i hisobidan
    (davlat mablag'i haqida ishora yo'q) birlamchi/ikkilamchi bozordan
    turar-joy uchun. "Foiz stavkasi:" bo'limida mijoz toifasi x
    boshlang'ich to'lov ulushiga qarab 3 ta stavka beriladi ("Dastlabki
    to'lov 20%dan 25% gacha bo'lganda — yillik 26%" kabi) — faqat
    "yillik N%" naqshiga mos regex bilan ajratiladi. Imtiyozli davr
    "3 oygacha ... YOKI imtiyozli davrsiz" deb ixtiyoriy tarzda
    tavsiflangan — taklif etilayotgan maksimal qiymat (3 oy) olinadi,
    umumiy extract_grace_period_months emas (u inkor signalini ko'rib
    0 qaytarardi)."""
    with patch("scrapers.kapital.fetch_html", side_effect=_fake_fetch):
        products = KapitalBankScraper().run()

    tijorat = next(p for p in products if p.category == "ipoteka_tijorat")
    assert tijorat.bank == "Kapitalbank"
    assert tijorat.product_name == "Qulay uy ipoteka krediti"
    assert tijorat.rate_min == 24.0
    assert tijorat.rate_max == 26.0
    assert tijorat.term_min_months == 120
    assert tijorat.term_max_months == 120
    assert tijorat.amount_max_som == 1_000_000_000
    assert tijorat.down_payment_pct == 20.0
    assert tijorat.grace_period_months == 3
    assert tijorat.payment_method == "Annuitet"
    assert tijorat.requires_collateral is True


def test_kapital_mikroqarz_onlayn_parses_correctly():
    """"Onlayn mikroqarz" states "Ariza topshirish usuli: Kapitalbank.Online
    mobil ilovasi orqali" (via mobile app, no branch visit) — the online
    category. Term is written as "3 (uch) oy" / "6 (olti) oy" / "12 (o'n
    ikki) oy", which doesn't match the standard "N oygacha" pattern used
    elsewhere, hence the dedicated regex. Security is an insurance policy
    only, not property collateral."""
    with patch("scrapers.kapital.fetch_html", side_effect=_fake_fetch):
        products = KapitalBankScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert mikroqarz.bank == "Kapitalbank"
    assert mikroqarz.product_name == "Onlayn mikroqarz"
    assert mikroqarz.rate_min == 27.0
    assert mikroqarz.rate_max == 27.0
    assert mikroqarz.term_min_months == 3
    assert mikroqarz.term_max_months == 12
    assert mikroqarz.amount_max_som == 50_000_000
    assert mikroqarz.requires_collateral is False
    assert mikroqarz.grace_period_months is None
    assert mikroqarz.payment_method == "Annuitet"
