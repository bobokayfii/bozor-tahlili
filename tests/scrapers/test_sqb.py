from pathlib import Path
from unittest.mock import patch

from scrapers.sqb import SQBScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    SQBScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "sqb_avtokredit.html").read_text(encoding="utf-8"),
    SQBScraper.CATEGORY_URLS["avtokredit_ikkilamchi"]: (FIXTURES_DIR / "sqb_avtokredit_ikkilamchi.html").read_text(
        encoding="utf-8"
    ),
    SQBScraper.CATEGORY_URLS["ipoteka_tijorat"]: (FIXTURES_DIR / "sqb_ipoteka_tijorat.html").read_text(
        encoding="utf-8"
    ),
    SQBScraper.CATEGORY_URLS["ipoteka_davlat"]: (FIXTURES_DIR / "sqb_ipoteka_davlat.html").read_text(
        encoding="utf-8"
    ),
    SQBScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "sqb_mikroqarz.html").read_text(encoding="utf-8"),
    SQBScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (FIXTURES_DIR / "sqb_mikroqarz_onlayn.html").read_text(
        encoding="utf-8"
    ),
    SQBScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "sqb_kredit_karta.html").read_text(encoding="utf-8"),
    SQBScraper.CATEGORY_URLS["istemol_krediti"]: (FIXTURES_DIR / "sqb_istemol_krediti.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_sqb_scraper_parses_all_eight_categories():
    with patch("scrapers.sqb.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = SQBScraper().run()

    assert mock_fetch.call_count == 8
    categories = {p.category for p in products}
    assert categories == {
        "avtokredit",
        "avtokredit_ikkilamchi",
        "ipoteka_tijorat",
        "ipoteka_davlat",
        "mikroqarz",
        "mikroqarz_onlayn",
        "kredit_karta",
        "istemol_krediti",
    }
    assert all(p.bank == "SQB" for p in products)


def test_sqb_ipoteka_davlat_parses_correctly():
    """"Exclusive ipoteka" — "Yangi tartib doirasida Iqtisodiyot va moliya
    vazirligi mablag'lari hamda Bankning o'z mablag'lari hisobidan
    moliyalashtiriladigan ipoteka krediti" deb aniq yozilgan — davlat
    (Moliya vazirligi) va bank mablag'lari aralash moliyalashtirilgan,
    "ipoteka_tijorat"dagi 100% bank mablag'idan farqli. SQB saytida
    shunga o'xshash "hamkor" nomli boshqa sahifalar ham bor, lekin ular
    qurilish bosqichidagi obyektga ulush kiritish uchun (tugallangan
    uy-joy xaridi emas) — shu sabab bu yerga kiritilmagan.

    "Kreditning eng ko'p miqdori" bo'limida uchta raqam bor: umumiy
    chegara ("1 000 000 000 so'mgacha") va ikkita mintaqaviy Moliya
    vazirligi sub-chegarasi ("380"/"480 mln so'mgacha") — umumiy chegara
    "mln" so'zisiz to'g'ridan-to'g'ri "so'mgacha"ga ulangan yagona
    guruhlangan son bo'lgani uchun maxsus regex bilan ajratiladi (aks
    holda eng kichik sub-chegaraga tushib qolardi). Stavka "Yillik 18%
    dan" — yagona qiymat, min=max=18.0."""
    with patch("scrapers.sqb.fetch_html", side_effect=_fake_fetch):
        products = SQBScraper().run()

    davlat = next(p for p in products if p.category == "ipoteka_davlat")
    assert davlat.product_name == "Exclusive ipoteka"
    assert davlat.rate_min == 18.0
    assert davlat.rate_max == 18.0
    assert davlat.term_min_months == 240
    assert davlat.term_max_months == 240
    assert davlat.amount_max_som == 1_000_000_000
    assert davlat.down_payment_pct == 20.0
    assert davlat.grace_period_months == 6
    assert davlat.payment_method == "Annuitet, Differensial"
    assert davlat.requires_collateral is True


def test_sqb_ipoteka_tijorat_parses_correctly():
    """"Ishonchli ipoteka krediti" — bankning o'z mablag'i hisobidan
    birlamchi va ikkilamchi bozorlardan uy-joy uchun. "Kredit foiz
    stavkasi" bo'limi mijoz toifasi bo'yicha 3 qatordan iborat (23,5% /
    24% / 24,5%), har biri o'z "N yilgacha" muddatiga ega (15/10/15 yil,
    ya'ni 180/120/180 oy). Apostroflar bu sahifada Unicode o'ng
    qo'shtirnoq (‘) bilan yozilgan, boshqa SQB sahifalaridagi oddiy ASCII
    (') dan farqli."""
    with patch("scrapers.sqb.fetch_html", side_effect=_fake_fetch):
        products = SQBScraper().run()

    tijorat = next(p for p in products if p.category == "ipoteka_tijorat")
    assert tijorat.product_name == "Ishonchli ipoteka krediti"
    assert tijorat.rate_min == 23.5
    assert tijorat.rate_max == 24.5
    assert tijorat.term_min_months == 120
    assert tijorat.term_max_months == 180
    assert tijorat.amount_max_som == 1_500_000_000
    assert tijorat.down_payment_pct == 20.0
    assert tijorat.grace_period_months == 24
    assert tijorat.payment_method == "Annuitet, Differensial"
    assert tijorat.requires_collateral is True


def test_sqb_istemol_krediti_ignores_unrelated_page_percentages():
    """The real consumer-credit page has a mortgage cross-sell banner (17%)
    before the rate table and a debt-ratio eligibility note (50%) after it.
    CATEGORY_HEADINGS must scope extraction to just the "Foiz stavkasi"
    table so those unrelated percentages don't pollute rate_min/rate_max."""
    with patch("scrapers.sqb.fetch_html", side_effect=_fake_fetch):
        products = SQBScraper().run()

    istemol_krediti = next(p for p in products if p.category == "istemol_krediti")
    assert istemol_krediti.rate_min == 21.99
    assert istemol_krediti.rate_max == 25.99
    assert istemol_krediti.term_min_months == 36
    assert istemol_krediti.term_max_months == 60
    assert istemol_krediti.amount_max_som == 200_000_000
    # Collateral requirement lives outside the narrowed rate section, so it
    # must be checked against the full fetched page, not just that section.
    assert istemol_krediti.requires_collateral is True


def test_sqb_avtokredit_ignores_unrelated_page_percentages():
    """The real avtokredit page's "Boshlang'ich badal" (25%) sits right next
    to the "Foiz stavkalari" table, and the page also has an unrelated
    debt-ratio note (50%), an LTV cap (75%), and a mortgage cross-sell
    banner (17%) further down. None of those should leak into rate_min/
    rate_max — only the three actual rate tiers (20/21/22%) should."""
    with patch("scrapers.sqb.fetch_html", side_effect=_fake_fetch):
        products = SQBScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.product_name == "«Avto imkon» avtokrediti"
    assert avtokredit.rate_min == 20.0
    assert avtokredit.rate_max == 22.0
    assert avtokredit.term_min_months == 12
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 800_000_000
    assert avtokredit.down_payment_pct == 25.0
    assert avtokredit.grace_period_months == 3
    assert avtokredit.payment_method == "Annuitet, Differensial"
    assert avtokredit.requires_collateral is True


def test_sqb_avtokredit_ikkilamchi_parses_correctly():
    """"«Ikkilamchi bozordan avtotransport» krediti" — the hero card only
    shows the best rate/longest term ("25% dan", "60 oygacha"), but the
    detailed "Kredit shartlari" table breaks the rate down by customer
    tier (official-income: 27%/36mo, 28%/48mo, 29%/60mo; salary-project:
    25%/36mo, 26%/48mo, 27%/60mo) — the full table is used, so rate_max
    (29%) is a value the hero card never shows. "Kredit miqdori" lists two
    figures (400 mln for the vehicle itself, 40 mln for related goods/
    services) — the larger one wins. The rate/term table must be scoped
    narrowly (stops before the next section) so "Imtiyozli davr: 3 oy"
    doesn't leak into term_min_months."""
    with patch("scrapers.sqb.fetch_html", side_effect=_fake_fetch):
        products = SQBScraper().run()

    ikkilamchi = next(p for p in products if p.category == "avtokredit_ikkilamchi")
    assert ikkilamchi.product_name == "«Ikkilamchi bozordan avtotransport» krediti"
    assert ikkilamchi.rate_min == 25.0
    assert ikkilamchi.rate_max == 29.0
    assert ikkilamchi.term_min_months == 36
    assert ikkilamchi.term_max_months == 60
    assert ikkilamchi.amount_max_som == 400_000_000
    assert ikkilamchi.down_payment_pct == 50.0
    assert ikkilamchi.grace_period_months == 3
    assert ikkilamchi.payment_method == "Annuitet, Differensial"
    assert ikkilamchi.requires_collateral is True


def test_sqb_mikroqarz_onlayn_parses_correctly():
    """"SQB Mobile ilovasida mikroqarz" — the hero card only shows the
    best rate/shortest term ("24% dan boshlab", "48 oygacha"), but the
    "Batafsil shartlar" section has a full 6-row tier table (24%/6mo,
    25%/9mo, 26%/12mo, 27%/24mo, 28%/36mo, 29%/48mo) — the full table is
    used, so rate_max (29%) is a value the hero card never shows.
    "Mikroqarz ta'minoti" states only an insurance policy is required
    (not property collateral), so requires_collateral is False."""
    with patch("scrapers.sqb.fetch_html", side_effect=_fake_fetch):
        products = SQBScraper().run()

    onlayn = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert onlayn.product_name == "SQB Mobile ilovasida mikroqarz"
    assert onlayn.rate_min == 24.0
    assert onlayn.rate_max == 29.0
    assert onlayn.term_min_months == 6
    assert onlayn.term_max_months == 48
    assert onlayn.amount_max_som == 100_000_000
    assert onlayn.down_payment_pct is None
    assert onlayn.grace_period_months is None
    assert onlayn.payment_method is None
    assert onlayn.requires_collateral is False


def test_sqb_mikroqarz_parses_correctly():
    """The page is titled just "Mikrokredit" — the only "onlayn" mentions on
    the page are unrelated boilerplate (mobile app tips, a live-stream
    banner), not the product name itself, so this belongs under the
    offline "mikroqarz" category rather than "mikroqarz_onlayn"."""
    with patch("scrapers.sqb.fetch_html", side_effect=_fake_fetch):
        products = SQBScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz")
    assert mikroqarz.product_name == "Mikrokredit"
    assert mikroqarz.rate_min == 26.9
    assert mikroqarz.rate_max == 28.9
    assert mikroqarz.term_min_months == 36
    assert mikroqarz.term_max_months == 60
    assert mikroqarz.amount_max_som == 300_000_000
    assert mikroqarz.payment_method == "Annuitet, Differensial"
    assert mikroqarz.requires_collateral is True
