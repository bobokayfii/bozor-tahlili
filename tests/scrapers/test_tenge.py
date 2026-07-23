from pathlib import Path
from unittest.mock import patch

from scrapers.tenge import TengeBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    TengeBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "tenge_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    TengeBankScraper.CATEGORY_URLS["avtokredit_brend_birlamchi"]: (
        FIXTURES_DIR / "tenge_avtokredit_brend_birlamchi.html"
    ).read_text(encoding="utf-8"),
    TengeBankScraper.CATEGORY_URLS["avtokredit_elektro"]: (
        FIXTURES_DIR / "tenge_avtokredit_elektro.html"
    ).read_text(encoding="utf-8"),
    TengeBankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (
        FIXTURES_DIR / "tenge_ipoteka_tijorat.html"
    ).read_text(encoding="utf-8"),
    TengeBankScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (
        FIXTURES_DIR / "tenge_mikroqarz_onlayn.html"
    ).read_text(encoding="utf-8"),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_tenge_avtokredit_parses_correctly():
    with patch("scrapers.tenge.fetch_html", side_effect=_fake_fetch):
        products = TengeBankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.bank == "Tenge Bank"
    assert avtokredit.rate_min == 27.9
    assert avtokredit.rate_max == 27.9
    assert avtokredit.term_min_months == 48
    assert avtokredit.term_max_months == 48
    assert avtokredit.amount_max_som == 500_000_000
    assert avtokredit.requires_collateral is True
    assert avtokredit.product_name == "Yangi avtomobil uchun avtokredit"
    assert avtokredit.down_payment_pct == 26.0
    assert avtokredit.payment_method == "Annuitet, Differensial"
    # Sahifada "imtiyozli davr" haqida umuman gap yo'q — noma'lum.
    assert avtokredit.grace_period_months is None


def test_tenge_avtokredit_brend_birlamchi_parses_correctly():
    """"Import avtomobil uchun avtokredit" — chetdan import qilingan
    avtomobillar uchun; bir xil "Shartlar" shabloni ("Ustama" -> yillik
    foiz, "Maksimal miqdor", "Muddat", "Qarz oluvchi"gacha) generic
    "avtokredit" toifasi bilan bir xil. "Garovsiz onlayn mikroqarz" yon-
    menyu iborasi bu yerda ham butun matnda "garov" tekshiruvini yolg'on-
    manfiy qiladi — shu sabab FORCE_COLLATERAL orqali aniq True
    belgilangan."""
    with patch("scrapers.tenge.fetch_html", side_effect=_fake_fetch):
        products = TengeBankScraper().run()

    brend = next(p for p in products if p.category == "avtokredit_brend_birlamchi")
    assert brend.bank == "Tenge Bank"
    assert brend.product_name == "Import avtomobil uchun avtokredit"
    assert brend.rate_min == 27.9
    assert brend.rate_max == 27.9
    assert brend.term_min_months == 48
    assert brend.term_max_months == 48
    assert brend.amount_max_som == 500_000_000
    assert brend.requires_collateral is True
    assert brend.down_payment_pct == 26.0
    assert brend.payment_method == "Annuitet, Differensial"
    assert brend.grace_period_months is None


def test_tenge_avtokredit_elektro_parses_correctly():
    """"Elektromobil uchun avtokredit" — bir xil "Shartlar" shabloni, lekin
    haqiqiy sarlavha "Ustama" emas, "Boshlang'ich to'lov va ustama" deb
    birlashtirilgan (boshqa ikkita avtokredit sahifasidan farqli — yagona
    "Ustama" so'zi bu sahifada faqat bo'sh kalkulyator natijasida uchraydi).
    Boshlang'ich badal bo'limi ham "Boshlang'ich to'lov" o'rniga "Qarz
    oluvchi"dan boshlab olinadi, aks holda birlashtirilgan sarlavhadagi
    27,9% stavka badal ro'yxatiga aralashib ketardi."""
    with patch("scrapers.tenge.fetch_html", side_effect=_fake_fetch):
        products = TengeBankScraper().run()

    elektro = next(p for p in products if p.category == "avtokredit_elektro")
    assert elektro.bank == "Tenge Bank"
    assert elektro.product_name == "Elektromobil uchun avtokredit"
    assert elektro.rate_min == 27.9
    assert elektro.rate_max == 27.9
    assert elektro.term_min_months == 48
    assert elektro.term_max_months == 48
    assert elektro.amount_max_som == 500_000_000
    assert elektro.requires_collateral is True
    assert elektro.down_payment_pct == 26.0
    assert elektro.payment_method == "Annuitet, Differensial"
    assert elektro.grace_period_months is None


def test_tenge_ipoteka_tijorat_parses_correctly():
    """"Ipoteka krediti (yangi uy-joy)" — davlat mablag'i haqida ishora
    yo'q, bankning o'z mahsuloti. "Ustama va boshlang'ich to'lov"
    birlashtirilgan sarlavhasi ostida ikkita qator beriladi: "25%
    boshlang'ich to'lov bilan - yillik 24,9%" / "50% boshlang'ich to'lov
    bilan - yillik 23,9%" — bu yerda badal foizi RATE'dan OLDIN keladi
    (avtokredit sahifalaridan farqli tartib), shu sabab "yillik N%" va
    "N% boshlang'ich" uchun alohida regexlar ishlatiladi. Muddat "15
    yilgacha" (180 oy) — umumiy extract_term_months'ning 120 oylik
    cheklovi bu yerda chetlab o'tiladi."""
    with patch("scrapers.tenge.fetch_html", side_effect=_fake_fetch):
        products = TengeBankScraper().run()

    tijorat = next(p for p in products if p.category == "ipoteka_tijorat")
    assert tijorat.bank == "Tenge Bank"
    assert tijorat.product_name == "Ipoteka krediti (yangi uy-joy)"
    assert tijorat.rate_min == 23.9
    assert tijorat.rate_max == 24.9
    assert tijorat.term_min_months == 180
    assert tijorat.term_max_months == 180
    assert tijorat.amount_max_som == 820_000_000
    assert tijorat.down_payment_pct == 25.0
    assert tijorat.grace_period_months is None
    assert tijorat.payment_method == "Annuitet, Differensial"
    assert tijorat.requires_collateral is True


def test_tenge_mikroqarz_onlayn_parses_correctly():
    """"Onlayn mikroqarz" states "bankga tashrif buyurmasdan 24/7
    rasmiylashtirish" (no branch visit, 24/7) — the online category.
    Term is given as separate "Minimal muddat: 6 oy" / "Maksimal muddat:
    36 oygacha" labels rather than a single range, requiring dedicated
    regexes for each bound. Security is an insurance policy only, not
    property collateral."""
    with patch("scrapers.tenge.fetch_html", side_effect=_fake_fetch):
        products = TengeBankScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert mikroqarz.bank == "Tenge Bank"
    assert mikroqarz.product_name == "Onlayn mikroqarz"
    assert mikroqarz.rate_min == 24.6
    assert mikroqarz.rate_max == 49.0
    assert mikroqarz.term_min_months == 6
    assert mikroqarz.term_max_months == 36
    assert mikroqarz.amount_max_som == 90_000_000
    assert mikroqarz.requires_collateral is False
    assert mikroqarz.grace_period_months is None
    assert mikroqarz.payment_method == "Annuitet"
