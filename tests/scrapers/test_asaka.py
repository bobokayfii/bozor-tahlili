from pathlib import Path
from unittest.mock import patch

from scrapers.asaka import AsakabankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    AsakabankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "asaka_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    AsakabankScraper.CATEGORY_URLS["avtokredit_brend_birlamchi"]: (
        FIXTURES_DIR / "asaka_avtokredit_brend_birlamchi.html"
    ).read_text(encoding="utf-8"),
    AsakabankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (
        FIXTURES_DIR / "asaka_ipoteka_tijorat.html"
    ).read_text(encoding="utf-8"),
    AsakabankScraper.CATEGORY_URLS["ipoteka_davlat"]: (
        FIXTURES_DIR / "asaka_ipoteka_davlat.html"
    ).read_text(encoding="utf-8"),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_asaka_avtokredit_parses_correctly():
    with patch("scrapers.asaka.fetch_html", side_effect=_fake_fetch):
        products = AsakabankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.bank == "Asakabank"
    # Real promotional UzAuto Motors financing rate, confirmed on the live
    # (Playwright-rendered) page.
    assert avtokredit.rate_min == 0.0
    assert avtokredit.rate_max == 0.0
    assert avtokredit.term_min_months == 60
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 1_000_000_000
    assert avtokredit.requires_collateral is True
    assert avtokredit.product_name == "Avtokredit UzAuto Motors"
    assert avtokredit.down_payment_pct == 25.0
    assert avtokredit.grace_period_months == 0
    assert avtokredit.payment_method == "Annuitet, Differensial"


def test_asaka_avtokredit_brend_birlamchi_parses_correctly():
    """"ADM Global I" — ADM Jizzakh zavodida ishlab chiqarilgan KIA
    avtomobillari (Sonet, Carens, Bongo, Carnival PE, K8 PE) uchun, xuddi
    shu "Kredit haqida" -> "Shart va talablar" shabloni bilan ("uzaytirish
    huquqisiz 60 oygacha", "80%dan" avtomobil qiymatiga nisbatan ulush —
    stavka emas — olib tashlanadi, "1 (bir) mlrd. so'mdan oshmagan
    miqdorda")."""
    with patch("scrapers.asaka.fetch_html", side_effect=_fake_fetch):
        products = AsakabankScraper().run()

    brend = next(p for p in products if p.category == "avtokredit_brend_birlamchi")
    assert brend.bank == "Asakabank"
    assert brend.product_name == "ADM Global I"
    assert brend.rate_min == 0.0
    assert brend.rate_max == 0.0
    assert brend.term_min_months == 60
    assert brend.term_max_months == 60
    assert brend.amount_max_som == 1_000_000_000
    assert brend.requires_collateral is True
    assert brend.down_payment_pct == 20.0
    assert brend.grace_period_months == 0
    assert brend.payment_method == "Annuitet, Differensial"


def test_asaka_ipoteka_davlat_parses_correctly():
    """"Qulay Makon" — sahifada aniq "Moliya vazirligi" so'zi yo'q, lekin
    ikkita mustaqil signal buni davlat mablag'i bilan moliyalashtirilgan
    ekanini tasdiqlaydi: (1) "Kredit summasi" chegaralari (Toshkent 480,0
    mln / viloyat 380,0 mln so'mgacha) boshqa banklarda "Moliya vazirligi"
    deb aniq yozilgan xuddi shu davlat dasturi chegaralari bilan bir xil;
    (2) hujjatlar ro'yxatida "Subsidiya xabarnomasi (mavjud bo'lsa)" tilga
    olinadi. "Ipoteka Universal 2.0" (bankning o'z mablag'i) da bunday
    chegara yoki subsidiya hujjati yo'q. Summalar vergul-o'nlik ("480,0
    mln so'mgacha") formatida — maxsus regex bilan olinadi."""
    with patch("scrapers.asaka.fetch_html", side_effect=_fake_fetch):
        products = AsakabankScraper().run()

    davlat = next(p for p in products if p.category == "ipoteka_davlat")
    assert davlat.bank == "Asakabank"
    assert davlat.product_name == "Qulay Makon"
    assert davlat.rate_min == 17.0
    assert davlat.rate_max == 17.0
    assert davlat.term_min_months == 240
    assert davlat.term_max_months == 240
    assert davlat.amount_max_som == 480_000_000
    assert davlat.down_payment_pct == 15.0
    assert davlat.grace_period_months is None
    assert davlat.payment_method == "Annuitet, Differensial"
    assert davlat.requires_collateral is True


def test_asaka_ipoteka_tijorat_parses_correctly():
    """"Ipoteka Universal 2.0" — davlat mablag'i haqida ishora yo'q,
    bankning o'z mahsuloti; birlamchi va ikkilamchi bozordan uy-joy uchun.
    Ikkita stavka beriladi (21,99% asosiy, 20,99% ish haqi loyihasi
    ishtirokchilari uchun). Muddat "Turar joyni sotib olish uchun - 240
    oygacha" iborasiga bog'langan regex bilan olinadi. Boshlang'ich badal
    "%" belgisisiz, so'z shaklida ("25 foizidan\xa0kam") — uzilmaydigan
    probel tufayli \\s* ishlatiladi."""
    with patch("scrapers.asaka.fetch_html", side_effect=_fake_fetch):
        products = AsakabankScraper().run()

    tijorat = next(p for p in products if p.category == "ipoteka_tijorat")
    assert tijorat.bank == "Asakabank"
    assert tijorat.product_name == "Ipoteka Universal 2.0"
    assert tijorat.rate_min == 20.99
    assert tijorat.rate_max == 21.99
    assert tijorat.term_min_months == 240
    assert tijorat.term_max_months == 240
    assert tijorat.amount_max_som == 800_000_000
    assert tijorat.down_payment_pct == 25.0
    assert tijorat.grace_period_months is None
    assert tijorat.payment_method == "Annuitet, Differensial"
    assert tijorat.requires_collateral is True
