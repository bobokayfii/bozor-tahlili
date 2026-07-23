from pathlib import Path
from unittest.mock import patch

from scrapers.turon import TuronBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    TuronBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "turon_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    TuronBankScraper.CATEGORY_URLS["avtokredit_brend_birlamchi"]: (
        FIXTURES_DIR / "turon_avtokredit_brend_birlamchi.html"
    ).read_text(encoding="utf-8"),
    TuronBankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (
        FIXTURES_DIR / "turon_ipoteka_tijorat.html"
    ).read_text(encoding="utf-8"),
    TuronBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "turon_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_turon_avtokredit_parses_correctly():
    with patch("scrapers.turon.fetch_html", side_effect=_fake_fetch):
        products = TuronBankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.bank == "Turonbank"
    assert avtokredit.rate_min == 0.0
    assert avtokredit.rate_max == 0.0
    assert avtokredit.term_min_months == 56
    assert avtokredit.term_max_months == 56
    # Stated on-page as "2000 (BHM)"; the calculator's own slider gives the
    # bank-computed so'm equivalent ("824 million so'mgacha").
    assert avtokredit.amount_max_som == 824_000_000
    assert avtokredit.requires_collateral is True
    assert avtokredit.product_name == '"UzAuto Motors" Avtokrediti'
    assert avtokredit.down_payment_pct == 30.0
    assert avtokredit.grace_period_months == 0
    assert avtokredit.payment_method == "Annuitet"


def test_turon_avtokredit_brend_birlamchi_parses_correctly():
    """"Green Avto" Avtokrediti — chetdan import qilingan avtomobillar
    uchun; sahifada birlamchi VA ikkilamchi bozor shartlari aralash
    beriladi ("Birlamchi bozor uchun - 60 oy" / "Ikkilamchi bozor uchun -
    48 oy" kabi), shu sabab faqat "Birlamchi bozor uchun:" dan keyingi
    stavka jadvali (30-40%/40-50%/50%+ ulush -> 22.99%/21.99%/20.99%) va
    alohida "Birlamchi bozor uchun - N oy/N% dan boshlab" iboralari
    olinadi. Rasmiy ro'yxatda summa "2000 (BHM)" deb berilgan — bank
    hisoblagan "Zarur summa" kalkulyator slayderining so'm ekvivalenti
    ("824 million so'mgacha") ishlatiladi, o'zimiz BHM kursini
    taxmin qilmaymiz."""
    with patch("scrapers.turon.fetch_html", side_effect=_fake_fetch):
        products = TuronBankScraper().run()

    brend = next(p for p in products if p.category == "avtokredit_brend_birlamchi")
    assert brend.bank == "Turonbank"
    assert brend.product_name == '"Green Avto" Avtokrediti'
    assert brend.rate_min == 20.99
    assert brend.rate_max == 22.99
    assert brend.term_min_months == 60
    assert brend.term_max_months == 60
    assert brend.amount_max_som == 824_000_000
    assert brend.down_payment_pct == 30.0
    assert brend.grace_period_months == 0
    assert brend.payment_method == "Annuitet, Differensial"
    assert brend.requires_collateral is True


def test_turon_avtokredit_brend_ikkilamchi_parses_correctly():
    """"Green Avto" Avtokrediti sahifasining ikkilamchi bozor qismi —
    birlamchidan farqli, tierlarsiz bitta qat'iy qiymat beradi:
    "Ikkilamchi avtotransport uchun - 25%" (stavka), "Ikkilamchi bozor
    uchun - 48 oy" (muddat), "Ikkilamchi bozor uchun - 50%" (boshlang'ich
    badal) — har biri o'z prefiksiga xos regex bilan ajratiladi, chunki
    "Ikkilamchi bozor uchun" prefiksi ham muddat, ham badal uchun
    takrorlanadi."""
    with patch("scrapers.turon.fetch_html", side_effect=_fake_fetch):
        products = TuronBankScraper().run()

    ikkilamchi = next(p for p in products if p.category == "avtokredit_brend_ikkilamchi")
    assert ikkilamchi.bank == "Turonbank"
    assert ikkilamchi.product_name == '"Green Avto" Avtokrediti'
    assert ikkilamchi.rate_min == 25.0
    assert ikkilamchi.rate_max == 25.0
    assert ikkilamchi.term_min_months == 48
    assert ikkilamchi.term_max_months == 48
    assert ikkilamchi.amount_max_som == 824_000_000
    assert ikkilamchi.down_payment_pct == 50.0
    assert ikkilamchi.grace_period_months == 0
    assert ikkilamchi.payment_method == "Annuitet, Differensial"
    assert ikkilamchi.requires_collateral is True


def test_turon_ipoteka_tijorat_parses_correctly():
    """"Yanada oson" ipoteka krediti — rasmiy daromad manbaiga ega
    bo'lmagan fuqarolarga birlamchi/ikkilamchi uy-joy uchun (davlat
    mablag'i haqida ishora yo'q). Rasmiy ro'yxatda summa "4 000 (BHM)"
    deb berilgan — bank hisoblagan "Zarur summa" kalkulyator slayderining
    so'm ekvivalenti ("1.5 milliard so'mgacha") ishlatiladi. Muddat
    "Kredit muddati" sarlavhasidan DARHOL keyin keladigan bare "10 yil"
    dan olinadi — sahifa oxiridagi aloqasiz "21 yosh" talabi ham "yil"
    so'ziga mos kelgani uchun umumiy qidiruv ishlatilmaydi."""
    with patch("scrapers.turon.fetch_html", side_effect=_fake_fetch):
        products = TuronBankScraper().run()

    tijorat = next(p for p in products if p.category == "ipoteka_tijorat")
    assert tijorat.bank == "Turonbank"
    assert tijorat.product_name == '"Yanada oson" ipoteka krediti'
    assert tijorat.rate_min == 24.0
    assert tijorat.rate_max == 24.0
    assert tijorat.term_min_months == 120
    assert tijorat.term_max_months == 120
    assert tijorat.amount_max_som == 1_500_000_000
    assert tijorat.down_payment_pct == 20.0
    assert tijorat.grace_period_months == 0
    assert tijorat.payment_method == "Annuitet, Differensial"
    assert tijorat.requires_collateral is True


def test_turon_mikroqarz_parses_correctly():
    """"Mikroqarz" states "Rasmiylashtirish usuli: Bank ofisi" (branch
    visit) — the offline category, despite a generic "onlayn ariza"
    marketing blurb elsewhere on the page. Ta'minot accepts "likvidli
    mol-mulk garovi" (property collateral) as one of three options
    alongside guarantor/insurance."""
    with patch("scrapers.turon.fetch_html", side_effect=_fake_fetch):
        products = TuronBankScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz")
    assert mikroqarz.bank == "Turonbank"
    assert mikroqarz.product_name == "Mikroqarz"
    assert mikroqarz.rate_min == 27.9
    assert mikroqarz.rate_max == 27.9
    assert mikroqarz.term_min_months == 48
    assert mikroqarz.term_max_months == 48
    assert mikroqarz.amount_max_som == 100_000_000
    assert mikroqarz.requires_collateral is True
    assert mikroqarz.grace_period_months == 0
    assert mikroqarz.payment_method == "Annuitet, Differensial"
