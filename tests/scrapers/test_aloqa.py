from pathlib import Path
from unittest.mock import patch

from scrapers.aloqa import AloqabankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    AloqabankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "aloqa_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    AloqabankScraper.CATEGORY_URLS["avtokredit_brend_birlamchi"]: (
        FIXTURES_DIR / "aloqa_avtokredit_brend_birlamchi.html"
    ).read_text(encoding="utf-8"),
    AloqabankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (
        FIXTURES_DIR / "aloqa_ipoteka_tijorat.html"
    ).read_text(encoding="utf-8"),
    AloqabankScraper.CATEGORY_URLS["ipoteka_davlat"]: (
        FIXTURES_DIR / "aloqa_ipoteka_davlat.html"
    ).read_text(encoding="utf-8"),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_aloqa_avtokredit_yields_no_product_without_stated_amount():
    """The product page states the credit ceiling as "cheklanmagan"
    (unlimited, tied to collateral value) rather than a concrete sum, so
    amount_max_som can't be parsed and the category is correctly skipped
    rather than filled in with a guess."""
    with patch("scrapers.aloqa.fetch_html", side_effect=_fake_fetch):
        products = AloqabankScraper().run()

    categories = {p.category for p in products}
    assert "avtokredit" not in categories


def test_aloqa_avtokredit_brend_birlamchi_parses_correctly():
    """"Avtokredit import" — "Birlamchi bozordan chet elda ishlab
    chiqarilgan yengil avtotransport vositalarini sotib olish uchun" (any
    foreign-made vehicle, not a single dealer-specific brand like
    Aloqabank's separate "avtokredit-byd-avto-"/"avtokredit-haval" pages).
    Rate table is grouped by down-payment tier for two customer classes:
    "Kamida 30%" -> "Yillik 23,5%"/"Yillik 24%", "Kamida 40%" -> "Yillik
    23%"/"Yillik 23,5%" — the "Kamida" tier labels and "Yillik" rate labels
    use separate anchored regexes so down-payment percentages never leak
    into rate_min/rate_max."""
    with patch("scrapers.aloqa.fetch_html", side_effect=_fake_fetch):
        products = AloqabankScraper().run()

    brend = next(p for p in products if p.category == "avtokredit_brend_birlamchi")
    assert brend.bank == "Aloqabank"
    assert brend.product_name == "Avtokredit import"
    assert brend.rate_min == 23.0
    assert brend.rate_max == 24.0
    assert brend.term_min_months == 60
    assert brend.term_max_months == 60
    assert brend.amount_max_som == 500_000_000
    assert brend.down_payment_pct == 30.0
    assert brend.grace_period_months == 0
    assert brend.payment_method == "Annuitet, Differensial"
    assert brend.requires_collateral is True


def test_aloqa_ipoteka_davlat_parses_correctly():
    """"Ipoteka krediti - Iqtisodiyot va moliya vazirligi mablag'lari
    hisobidan" — yon menyudagi mahsulot nomida aniq yozilgan, alohida
    "primary-mortgage" sahifasida, "Ipoteka (ikkilamchi bozor)"dagi
    bankning o'z mablag'idan farqli. Boshlang'ich badal "15 foizidan kam
    bo'lmagan" (qavschasiz so'z shaklida) — oddiy "\\d foiz" regexi bilan
    ajratiladi. Kredit miqdori "380,0 mln. so'mdan" / "480,0 mln.
    so'mgacha" — vergul-o'nlik va nuqtali "mln." birligi umumiy
    extract_amount_som'ga mos kelmagani uchun maxsus regex ishlatiladi.
    Rasmiy "Qaytarish usuli" qatorida "Annuitet" so'zi tipo bilan
    ("Annuutet") yozilgan, lekin pastroqdagi kalkulyator vidjetida to'g'ri
    yozilgani uchun butun sahifa matni bo'yicha tekshirilganda to'g'ri
    natija chiqadi."""
    with patch("scrapers.aloqa.fetch_html", side_effect=_fake_fetch):
        products = AloqabankScraper().run()

    davlat = next(p for p in products if p.category == "ipoteka_davlat")
    assert davlat.bank == "Aloqabank"
    assert davlat.product_name == "Ipoteka krediti - Iqtisodiyot va moliya vazirligi mablag'lari hisobidan"
    assert davlat.rate_min == 17.0
    assert davlat.rate_max == 17.0
    assert davlat.term_min_months == 240
    assert davlat.term_max_months == 240
    assert davlat.amount_max_som == 480_000_000
    assert davlat.down_payment_pct == 15.0
    assert davlat.grace_period_months == 6
    assert davlat.payment_method == "Annuitet, Differensial"
    assert davlat.requires_collateral is True


def test_aloqa_ipoteka_tijorat_parses_correctly():
    """"Ipoteka (ikkilamchi bozor)" — davlat mablag'i haqida ishora yo'q,
    bankning o'z mahsuloti; birlamchi va ikkilamchi bozorni ham qamrab
    oladi. "Kredit shartlari" ro'yxati toza yagona qiymatlar beradi (24%,
    800 mln so'm, 20 yilgacha). Boshlang'ich badal "%" belgisisiz, so'z
    shaklida ("20 (yigirma) foizidan kam bo'lmagan") — maxsus regex bilan
    ajratiladi. Muddat "20 yilgacha" (240 oy) — umumiy
    extract_term_months'ning 120 oylik cheklovi bu yerda chetlab
    o'tiladi."""
    with patch("scrapers.aloqa.fetch_html", side_effect=_fake_fetch):
        products = AloqabankScraper().run()

    tijorat = next(p for p in products if p.category == "ipoteka_tijorat")
    assert tijorat.bank == "Aloqabank"
    assert tijorat.product_name == "Ipoteka (ikkilamchi bozor)"
    assert tijorat.rate_min == 24.0
    assert tijorat.rate_max == 24.0
    assert tijorat.term_min_months == 240
    assert tijorat.term_max_months == 240
    assert tijorat.amount_max_som == 800_000_000
    assert tijorat.down_payment_pct == 20.0
    assert tijorat.grace_period_months == 12
    assert tijorat.payment_method == "Annuitet, Differensial"
    assert tijorat.requires_collateral is True
