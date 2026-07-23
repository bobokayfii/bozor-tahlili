from pathlib import Path
from unittest.mock import patch

from scrapers.ipoteka import IpotekaBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    IpotekaBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "ipoteka_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    IpotekaBankScraper.CATEGORY_URLS["avtokredit_ikkilamchi"]: (
        FIXTURES_DIR / "ipoteka_avtokredit_ikkilamchi.html"
    ).read_text(encoding="utf-8"),
    IpotekaBankScraper.CATEGORY_URLS["avtokredit_brend_birlamchi"]: (
        FIXTURES_DIR / "ipoteka_avtokredit_brend_birlamchi.html"
    ).read_text(encoding="utf-8"),
    IpotekaBankScraper.CATEGORY_URLS["avtokredit_elektro"]: (
        FIXTURES_DIR / "ipoteka_avtokredit_elektro.html"
    ).read_text(encoding="utf-8"),
    IpotekaBankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (FIXTURES_DIR / "ipoteka_ipoteka_tijorat.html").read_text(
        encoding="utf-8"
    ),
    IpotekaBankScraper.CATEGORY_URLS["ipoteka_davlat"]: (FIXTURES_DIR / "ipoteka_ipoteka_davlat.html").read_text(
        encoding="utf-8"
    ),
    IpotekaBankScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (FIXTURES_DIR / "ipoteka_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    IpotekaBankScraper.CATEGORY_URLS["istemol_krediti"]: (FIXTURES_DIR / "ipoteka_istemol_krediti.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_ipoteka_scraper_parses_all_eight_categories():
    """"kredit_karta" was removed: its old "overdraft/" URL now redirects
    to an unrelated Russian-language Onlayn Mikrozaym page, and the live
    site has no dedicated credit-card (overdraft) loan product at all —
    only plain plastic/debit cards."""
    with patch("scrapers.ipoteka.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = IpotekaBankScraper().run()

    assert mock_fetch.call_count == 8
    categories = {p.category for p in products}
    assert categories == {
        "avtokredit",
        "avtokredit_ikkilamchi",
        "avtokredit_brend_birlamchi",
        "avtokredit_elektro",
        "ipoteka_tijorat",
        "ipoteka_davlat",
        "mikroqarz_onlayn",
        "istemol_krediti",
    }
    assert all(p.bank == "Ipoteka Bank" for p in products)


def test_ipoteka_ipoteka_davlat_parses_correctly():
    """""Oson" ipotekasi — sahifa title'ida "Moliya vazirligi subsidiyasi
    bilan" deb aniq yozilgan — davlat (byudjet) mablag'i, "ipoteka_tijorat"
    dagi bankning o'z mablag'idan farqli. Faqat birlamchi bozordagi yangi
    qurilgan uy-joy uchun. Barcha maydonlar FAQ savol-javob juftliklaridan
    olinadi (umumiy label:qiymat ro'yxati yo'q); stavka BITTA qat'iy
    qiymat ("yillik 16,99% (qat'iy)") — min=max. "Maksimal kredit miqdori
    qancha?" savoli sahifada ikki marta uchraydi (umumiy va hudud bo'yicha
    taqsimot) — faqat birinchi (umumiy, 480 mln so'm) javob olinadi.
    Sahifadagi aloqasiz "garovsiz mikrokredit" iborasi has_collateral_
    requirement'ni yolg'on-manfiy qilgani uchun ipoteka_tijorat bilan bir
    xil FORCE_COLLATERAL orqali True belgilangan."""
    with patch("scrapers.ipoteka.fetch_html", side_effect=_fake_fetch):
        products = IpotekaBankScraper().run()

    davlat = next(p for p in products if p.category == "ipoteka_davlat")
    assert davlat.product_name == '"Oson" ipotekasi'
    assert davlat.rate_min == 16.99
    assert davlat.rate_max == 16.99
    assert davlat.term_min_months == 240
    assert davlat.term_max_months == 240
    assert davlat.amount_max_som == 480_000_000
    assert davlat.down_payment_pct == 15.0
    assert davlat.grace_period_months == 0
    assert davlat.payment_method == "Annuitet, Differensial"
    assert davlat.requires_collateral is True


def test_ipoteka_ipoteka_tijorat_parses_correctly():
    """"Tijorat ipotekasi" — bankning o'z mablag'i hisobidan (davlat
    mablag'lari emas) birlamchi/ikkilamchi uy-joy uchun. Stavka mijoz
    toifasi x muddat (10/20 yil) bo'yicha guruhlangan ("10 yilgacha (120
    oy) — yillik 22.5%%" kabi) — "yillik N%" naqshiga qat'iy mos regex
    ishlatiladi, aks holda boshlang'ich badal ulushlari ham stavka
    sifatida hisoblanib ketardi. Muddat 20 yilgacha (240 oy) chiqadi —
    umumiy extract_term_months'ning 120 oylik avtokredit-cheklovi bu
    yerda ishlatilmaydi, aks holda 240 oy chetlab o'tilardi."""
    with patch("scrapers.ipoteka.fetch_html", side_effect=_fake_fetch):
        products = IpotekaBankScraper().run()

    tijorat = next(p for p in products if p.category == "ipoteka_tijorat")
    assert tijorat.product_name == "Tijorat ipotekasi"
    assert tijorat.rate_min == 22.5
    assert tijorat.rate_max == 26.99
    assert tijorat.term_min_months == 120
    assert tijorat.term_max_months == 240
    assert tijorat.amount_max_som == 1_700_000_000
    assert tijorat.down_payment_pct == 20.0
    assert tijorat.grace_period_months == 0
    assert tijorat.payment_method == "Annuitet, Differensial"
    assert tijorat.requires_collateral is True


def test_ipoteka_avtokredit_elektro_parses_correctly():
    """"Avtokredit Super BYD" — Song Plus DM-i/Pro DM-i, e2, Chazor, Song
    Plus EV (plug-in gibrid va elektromobil) modellari uchun, "Avtokredit
    Hyundai" bilan bir xil "Miqdori" -> "Talablar" shabloni. Boshlang'ich
    badal qatoridan keyin darhol "* agar 2024-yil 1-iyuldan keyin ... 15%
    ... 20%" footnote matni keladi — bu footnote'dagi raqamlar ham "%"
    bilan yozilgani uchun down-payment bo'limi "* agar"dan oldin
    to'xtatiladi, aks holda min() natijasi yolg'on ravishda 15%ga
    tushib qolardi."""
    with patch("scrapers.ipoteka.fetch_html", side_effect=_fake_fetch):
        products = IpotekaBankScraper().run()

    elektro = next(p for p in products if p.category == "avtokredit_elektro")
    assert elektro.product_name == "Avtokredit Super BYD"
    assert elektro.rate_min == 0.0
    assert elektro.rate_max == 21.9
    assert elektro.term_min_months == 60
    assert elektro.term_max_months == 60
    assert elektro.amount_max_som == 480_000_000
    assert elektro.down_payment_pct == 25.0
    assert elektro.grace_period_months == 0
    assert elektro.payment_method == "Annuitet"
    assert elektro.requires_collateral is True


def test_ipoteka_avtokredit_brend_birlamchi_parses_correctly():
    """"Avtokredit Hyundai" (brend-maxsus, birlamchi bozor) shares the same
    page template as "Avtokredit R1" (Miqdori -> Talablar block, same
    info-sheet structure). Rate is "0 - 19,9%" — a comma-decimal upper
    bound the shared _RATE_RANGE_RE must still capture alongside the
    leading "0"."""
    with patch("scrapers.ipoteka.fetch_html", side_effect=_fake_fetch):
        products = IpotekaBankScraper().run()

    brend = next(p for p in products if p.category == "avtokredit_brend_birlamchi")
    assert brend.product_name == "Avtokredit Hyundai"
    assert brend.rate_min == 0.0
    assert brend.rate_max == 19.9
    assert brend.term_min_months == 60
    assert brend.term_max_months == 60
    assert brend.amount_max_som == 480_000_000
    assert brend.down_payment_pct == 25.0
    assert brend.grace_period_months == 0
    assert brend.payment_method == "Annuitet"
    assert brend.requires_collateral is True


def test_ipoteka_avtokredit_ikkilamchi_parses_correctly():
    """"Avtokredit R1" page title states "yangi yoki ishlatilgan avtomobil
    uchun" (new or used vehicle), covering the secondary market. "Foiz
    stavkasi" appears twice on the page — an empty calculator widget first,
    then the real "Kreditlash shartlari" list — so extraction is scoped to
    the "Miqdori" -> "Talablar" block first, then sub-extracted within it."""
    with patch("scrapers.ipoteka.fetch_html", side_effect=_fake_fetch):
        products = IpotekaBankScraper().run()

    ikkilamchi = next(p for p in products if p.category == "avtokredit_ikkilamchi")
    assert ikkilamchi.product_name == "Avtokredit R1"
    assert ikkilamchi.rate_min == 27.99
    assert ikkilamchi.rate_max == 29.99
    assert ikkilamchi.term_min_months == 60
    assert ikkilamchi.term_max_months == 60
    assert ikkilamchi.amount_max_som == 480_000_000
    assert ikkilamchi.down_payment_pct == 25.0
    assert ikkilamchi.grace_period_months == 0
    assert ikkilamchi.payment_method == "Annuitet"
    assert ikkilamchi.requires_collateral is True


def test_ipoteka_avtokredit_separates_down_payment_from_rate_range():
    """The rate is given as "0-18%" — extract_percentages alone would miss
    the leading "0" (no "%" directly after it), and the nearby "25% dan
    boshlab" down payment badge must not leak into the rate range either."""
    with patch("scrapers.ipoteka.fetch_html", side_effect=_fake_fetch):
        products = IpotekaBankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.product_name == "Avtokredit Cobalt Special"
    assert avtokredit.rate_min == 0.0
    assert avtokredit.rate_max == 18.0
    assert avtokredit.term_min_months == 60
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 480_000_000
    assert avtokredit.down_payment_pct == 25.0
    # "imtiyozli davrsiz" ("without a grace period") in the info-sheet list.
    assert avtokredit.grace_period_months == 0
    assert avtokredit.payment_method == "Annuitet, Differensial"
    assert avtokredit.requires_collateral is True


def test_ipoteka_mikroqarz_onlayn_parses_correctly():
    """Page <title> and body both say "Onlayn Mikroqarz", delivered via the
    Ipoteka Mobile app to the customer's current account — this belongs
    under mikroqarz_onlayn, not the offline mikroqarz category."""
    with patch("scrapers.ipoteka.fetch_html", side_effect=_fake_fetch):
        products = IpotekaBankScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert mikroqarz.product_name == "Onlayn Mikroqarz"
    assert mikroqarz.rate_min == 24.0
    assert mikroqarz.rate_max == 48.9
    assert mikroqarz.term_min_months == 36
    assert mikroqarz.term_max_months == 60
    assert mikroqarz.amount_max_som == 100_000_000
    assert mikroqarz.grace_period_months == 0
    assert mikroqarz.payment_method == "Annuitet, Differensial"
    # No dedicated "Ta'minot" (collateral) section exists for this specific
    # product — unlike avtokredit, this is a correct negative, not a miss.
    assert mikroqarz.requires_collateral is False
