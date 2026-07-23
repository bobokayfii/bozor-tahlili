from pathlib import Path
from unittest.mock import patch

from scrapers.hamkor import HamkorBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    HamkorBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "hamkor_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    HamkorBankScraper.CATEGORY_URLS["avtokredit_ikkilamchi"]: (
        FIXTURES_DIR / "hamkor_avtokredit_ikkilamchi.html"
    ).read_text(encoding="utf-8"),
    HamkorBankScraper.CATEGORY_URLS["avtokredit_brend_birlamchi"]: (
        FIXTURES_DIR / "hamkor_avtokredit_brend_birlamchi.html"
    ).read_text(encoding="utf-8"),
    HamkorBankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (FIXTURES_DIR / "hamkor_ipoteka_tijorat.html").read_text(
        encoding="utf-8"
    ),
    HamkorBankScraper.CATEGORY_URLS["ipoteka_davlat"]: (FIXTURES_DIR / "hamkor_ipoteka_davlat.html").read_text(
        encoding="utf-8"
    ),
    HamkorBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "hamkor_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    HamkorBankScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (
        FIXTURES_DIR / "hamkor_mikroqarz_onlayn.html"
    ).read_text(encoding="utf-8"),
    HamkorBankScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "hamkor_kredit_karta.html").read_text(
        encoding="utf-8"
    ),
    HamkorBankScraper.CATEGORY_URLS["istemol_krediti"]: (FIXTURES_DIR / "hamkor_istemol_krediti.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_hamkor_scraper_parses_all_nine_categories():
    with patch("scrapers.hamkor.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = HamkorBankScraper().run()

    assert mock_fetch.call_count == 9
    categories = {p.category for p in products}
    assert categories == {
        "avtokredit",
        "avtokredit_ikkilamchi",
        "avtokredit_brend_birlamchi",
        "ipoteka_tijorat",
        "ipoteka_davlat",
        "mikroqarz",
        "mikroqarz_onlayn",
        "kredit_karta",
        "istemol_krediti",
    }
    assert all(p.bank == "HamkorBank" for p in products)


def test_hamkor_istemol_krediti_parses_correctly():
    """"Iste'mol krediti" ("personal-loan") — "Kredit miqdori" sarlavhasi
    sahifada ikki marta uchraydi: birinchisi noto'liq yuqori xulosa
    kartochkasida, ikkinchisi "Kredit haqida batafsil" bo'limidagi
    haqiqiy jadvalda (200 mln so'mgacha / 26-30% / 12-36 oy). Qidiruv
    "Kredit haqida batafsil"dan keyingi matnga chegaralanadi — aks holda
    "Qarz yuki 50%" (daromadga nisbat talabi) rate_max'ni yolg'on
    ravishda 50%ga ko'tarib yuborardi. Garov tekshiruvi ham faqat "Garov
    ta'minoti" -> "Hujjatlar" tor blokida o'tkaziladi — sahifaning
    boshqa joylarida aloqasiz "Garovsiz — 50 mln so'mgacha" reklama
    blurbi va "qarzdorlik mavjud emasligi" talabi bor, ikkalasi ham
    kengroq tekshiruvni yolg'on-manfiy qilib yuborardi."""
    with patch("scrapers.hamkor.fetch_html", side_effect=_fake_fetch):
        products = HamkorBankScraper().run()

    istemol_krediti = next(p for p in products if p.category == "istemol_krediti")
    assert istemol_krediti.product_name == "Iste'mol krediti"
    assert istemol_krediti.rate_min == 26.0
    assert istemol_krediti.rate_max == 30.0
    assert istemol_krediti.term_min_months == 12
    assert istemol_krediti.term_max_months == 36
    assert istemol_krediti.amount_max_som == 200_000_000
    assert istemol_krediti.grace_period_months == 0
    assert istemol_krediti.requires_collateral is True


def test_hamkor_ipoteka_davlat_parses_correctly():
    """"Yangi qurilgan uy-joy uchun ipoteka" ("mortgage-new-build") —
    "O'zbekiston Respublikasi Iqtisodiyot va moliya vazirligi va bank o'z
    mablag'lari hisobidan ... ipoteka krediti" deb aniq yozilgan — davlat
    va bank mablag'lari aralash, "Bank ipotekasi"dagi 100% bank
    mablag'idan farqli. "Foiz stavkasi" qatorida stavka ("17,5% -") va
    boshlang'ich badal oralig'i ("15% dan 30% gacha") bitta qatorda
    aralash beriladi — alohida regexlar bilan ajratiladi. "Kredit
    muddati" ikki xil qiymat beradi (20 yil — Vazirlik mablag'i, 10 yil —
    bank mablag'i), ikkalasi ham term_min/term_max sifatida saqlanadi."""
    with patch("scrapers.hamkor.fetch_html", side_effect=_fake_fetch):
        products = HamkorBankScraper().run()

    davlat = next(p for p in products if p.category == "ipoteka_davlat")
    assert davlat.product_name == "Yangi qurilgan uy-joy uchun ipoteka"
    assert davlat.rate_min == 17.0
    assert davlat.rate_max == 17.5
    assert davlat.term_min_months == 120
    assert davlat.term_max_months == 240
    assert davlat.amount_max_som == 600_000_000
    assert davlat.down_payment_pct == 15.0
    assert davlat.grace_period_months is None
    assert davlat.payment_method is None
    assert davlat.requires_collateral is True


def test_hamkor_ipoteka_tijorat_parses_correctly():
    """"Bank ipotekasi" — bankning o'z mablag'i hisobidan uy-joy sotib
    olish YOKI ta'mirlash uchun. "Foiz stavkasi" bo'limida stavka va
    boshlang'ich badal bir qatorda aralash beriladi ("yillik 26% -
    boshlang'ich to'lov 25% dan 30% gacha") — faqat "yillik N%" naqshiga
    mos regex bilan haqiqiy stavkalar ajratiladi. Yon menyudagi aloqasiz
    "Imtiyozli shartlar asosida" mahsuloti butun sahifa bo'yicha imtiyozli
    davr tekshiruvini yolg'on-ijobiy qilib yuborardi — shu sabab faqat
    "Kredit maqsadi" -> "Kafillik yoki garov" tor blokidan tekshiriladi."""
    with patch("scrapers.hamkor.fetch_html", side_effect=_fake_fetch):
        products = HamkorBankScraper().run()

    tijorat = next(p for p in products if p.category == "ipoteka_tijorat")
    assert tijorat.product_name == "Bank ipotekasi"
    assert tijorat.rate_min == 25.0
    assert tijorat.rate_max == 27.0
    assert tijorat.term_min_months == 72
    assert tijorat.term_max_months == 120
    assert tijorat.amount_max_som == 1_000_000_000
    assert tijorat.down_payment_pct == 25.0
    assert tijorat.grace_period_months is None
    assert tijorat.payment_method is None
    assert tijorat.requires_collateral is True


def test_hamkor_avtokredit_brend_birlamchi_parses_correctly():
    """"Auto KIA Sonet" (brend-maxsus, birlamchi bozor) shares the exact
    same page template as "Auto DAMAS" (rate matrix, term/amount/down-payment
    section boundaries) — both dispatch to the shared
    _build_avtokredit_product(category, ...) method."""
    with patch("scrapers.hamkor.fetch_html", side_effect=_fake_fetch):
        products = HamkorBankScraper().run()

    brend = next(p for p in products if p.category == "avtokredit_brend_birlamchi")
    assert brend.product_name == "Auto KIA Sonet"
    assert brend.rate_min == 0.0
    assert brend.rate_max == 18.5
    assert brend.term_min_months == 60
    assert brend.term_max_months == 60
    assert brend.amount_max_som == 600_000_000
    assert brend.down_payment_pct == 25.0
    assert brend.requires_collateral is True
    assert brend.grace_period_months is None
    assert brend.payment_method is None


def test_hamkor_avtokredit_ikkilamchi_parses_correctly():
    """"Auto light avtokrediti" states "Kredit maqsadi: Transport
    vositalarini birlamchi va ikkilamchi bozordan sotib olish uchun
    avtokredit" — covers both markets, mapped to avtokredit_ikkilamchi.
    The rate table splits into official-income and no-income tiers, each
    with several "N yilgacha — X%" rows; down-payment percentages in the
    same block always end in "dan boshlab" so a negative lookahead keeps
    them out of the rate list."""
    with patch("scrapers.hamkor.fetch_html", side_effect=_fake_fetch):
        products = HamkorBankScraper().run()

    ikkilamchi = next(p for p in products if p.category == "avtokredit_ikkilamchi")
    assert ikkilamchi.product_name == "Auto light avtokrediti"
    assert ikkilamchi.rate_min == 23.99
    assert ikkilamchi.rate_max == 30.0
    assert ikkilamchi.term_min_months == 12
    assert ikkilamchi.term_max_months == 60
    assert ikkilamchi.amount_max_som == 600_000_000
    assert ikkilamchi.down_payment_pct == 25.0
    assert ikkilamchi.requires_collateral is True
    assert ikkilamchi.grace_period_months is None
    assert ikkilamchi.payment_method is None


def test_hamkor_avtokredit_ignores_down_payment_tier_percentages():
    """The real "Auto DAMAS" page has two full rate matrices (unofficial and
    official income) grouped by down-payment tier (25%-70%) x term
    (13-60 months). Those tier labels ("Kamida 30%" etc.) are themselves
    percentages and must not leak into rate_min/rate_max — only the actual
    "N oy -> X%" rate pairs should. A cross-sell "Imtiyozli shartlar
    asosida" mention for an unrelated home-repair loan must also not cause
    a false grace-period reading."""
    with patch("scrapers.hamkor.fetch_html", side_effect=_fake_fetch):
        products = HamkorBankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.product_name == "Auto DAMAS"
    assert avtokredit.rate_min == 0.0
    assert avtokredit.rate_max == 19.0
    assert avtokredit.term_min_months == 60
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 600_000_000
    assert avtokredit.down_payment_pct == 25.0
    assert avtokredit.requires_collateral is True
    assert avtokredit.grace_period_months is None
    assert avtokredit.payment_method is None


def test_hamkor_mikroqarz_ignores_debt_ratio_qualifier_percentage():
    """"Mikrokredit Plus" requires a branch visit ("ariza bank ofisida
    to'ldiriladi") — this is the offline mikroqarz category, not online.
    Its rate table is grouped by debt-ratio and collateral-age qualifiers
    (e.g. "Qarz yuki 50% gacha bo'lgan..."), and that qualifier percentage
    must not leak into rate_min/rate_max — only the "N oygacha X%" pairs
    that follow it should."""
    with patch("scrapers.hamkor.fetch_html", side_effect=_fake_fetch):
        products = HamkorBankScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz")
    assert mikroqarz.product_name == "Mikrokredit Plus"
    assert mikroqarz.rate_min == 23.99
    assert mikroqarz.rate_max == 29.99
    assert mikroqarz.term_min_months == 60
    assert mikroqarz.term_max_months == 60
    assert mikroqarz.amount_max_som == 300_000_000
    assert mikroqarz.requires_collateral is True
    assert mikroqarz.grace_period_months is None
    assert mikroqarz.payment_method is None


def test_hamkor_mikroqarz_onlayn_parses_correctly():
    """"Onlayn kredit" page states "garovsiz" ("Faqat pasport kerak") and
    "Ariza berish joyi: Hamkor ilovasida" (via the Hamkor mobile app, no
    branch visit) — the online category; even the page <title> calls it
    a "mikroqarz". Term is written as a mixed-unit range ("6 oydan 3
    yilgacha"), which neither the plain month-range nor year-range regex
    matches, hence the dedicated pattern."""
    with patch("scrapers.hamkor.fetch_html", side_effect=_fake_fetch):
        products = HamkorBankScraper().run()

    mikroqarz_onlayn = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert mikroqarz_onlayn.product_name == "Onlayn kredit"
    assert mikroqarz_onlayn.rate_min == 19.9
    assert mikroqarz_onlayn.rate_max == 46.0
    assert mikroqarz_onlayn.term_min_months == 6
    assert mikroqarz_onlayn.term_max_months == 36
    assert mikroqarz_onlayn.amount_max_som == 100_000_000
    assert mikroqarz_onlayn.requires_collateral is False
    assert mikroqarz_onlayn.grace_period_months is None
    assert mikroqarz_onlayn.payment_method is None
