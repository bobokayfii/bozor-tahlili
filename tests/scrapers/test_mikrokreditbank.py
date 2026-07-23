from pathlib import Path
from unittest.mock import patch

from scrapers.mikrokreditbank import MikrokreditBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    MikrokreditBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "mk_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    MikrokreditBankScraper.CATEGORY_URLS["avtokredit_ikkilamchi"]: (
        FIXTURES_DIR / "mk_avtokredit_ikkilamchi.html"
    ).read_text(encoding="utf-8"),
    MikrokreditBankScraper.CATEGORY_URLS["avtokredit_brend_birlamchi"]: (
        FIXTURES_DIR / "mk_avtokredit_brend_birlamchi.html"
    ).read_text(encoding="utf-8"),
    MikrokreditBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "mk_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    MikrokreditBankScraper.CATEGORY_URLS["ipoteka_davlat"]: (
        FIXTURES_DIR / "mk_ipoteka_davlat.html"
    ).read_text(encoding="utf-8"),
    MikrokreditBankScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "mk_kredit_karta.html").read_text(
        encoding="utf-8"
    ),
    MikrokreditBankScraper.CATEGORY_URLS["istemol_krediti"]: (FIXTURES_DIR / "mk_istemol_krediti.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_mikrokreditbank_scraper_parses_all_seven_categories():
    with patch("scrapers.mikrokreditbank.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = MikrokreditBankScraper().run()

    assert mock_fetch.call_count == 7
    categories = {p.category for p in products}
    assert categories == {
        "avtokredit",
        "avtokredit_ikkilamchi",
        "avtokredit_brend_birlamchi",
        "mikroqarz",
        "kredit_karta",
        "istemol_krediti",
        "ipoteka_davlat",
    }
    assert all(p.bank == "Mikrokreditbank" for p in products)


def test_mikrokreditbank_ipoteka_davlat_parses_correctly():
    """"Imkoniyat ipotekasi krediti" — "Mahalla yettiligi" tavsiyasi
    asosida Kambag'allikdan chiqarish dasturiga kiritilgan fuqarolar
    uchun; hujjatlar bo'limida "Moliya vazirligi mablag'lari hisobidan
    ajratiladigan ipoteka krediti" deb aniq yozilgan — davlat (byudjet)
    mablag'i, bankning o'z mahsuloti emas. Muddat "20 yilgacha" (240 oy)
    — umumiy extract_term_months'ning 120 oylik cheklovi bu yerda
    chetlab o'tiladi."""
    with patch("scrapers.mikrokreditbank.fetch_html", side_effect=_fake_fetch):
        products = MikrokreditBankScraper().run()

    davlat = next(p for p in products if p.category == "ipoteka_davlat")
    assert davlat.bank == "Mikrokreditbank"
    assert davlat.product_name == "Imkoniyat ipotekasi krediti"
    assert davlat.rate_min == 18.0
    assert davlat.rate_max == 18.0
    assert davlat.term_min_months == 240
    assert davlat.term_max_months == 240
    assert davlat.amount_max_som == 120_000_000
    assert davlat.down_payment_pct == 15.0
    assert davlat.grace_period_months == 6
    assert davlat.payment_method == "Annuitet, Differensial"
    assert davlat.requires_collateral is True


def test_mikrokreditbank_avtokredit_brend_birlamchi_parses_correctly():
    """"Avtokredit ADM GLOBAL" — KIA, Chery, Haval va Changan avtomobillari
    uchun (birlamchi bozor). Uch xil pastki mahsulot ("KREDIT", "ROODELL I",
    "ROODELL II") uchun alohida boshlang'ich badal (25%-60%) x muddat
    (12-60 oy) narx jadvali bor; ulush yorliqlari butun son ("25%"), haqiqiy
    stavkalar esa doim vergul-kasr ("0,0%") — shu farq orqali ajratiladi."""
    with patch("scrapers.mikrokreditbank.fetch_html", side_effect=_fake_fetch):
        products = MikrokreditBankScraper().run()

    brend = next(p for p in products if p.category == "avtokredit_brend_birlamchi")
    assert brend.product_name == "Avtokredit ADM GLOBAL"
    assert brend.rate_min == 0.0
    assert brend.rate_max == 17.0
    assert brend.term_min_months == 12
    assert brend.term_max_months == 60
    assert brend.amount_max_som == 824_000_000
    assert brend.down_payment_pct == 25.0
    assert brend.grace_period_months == 0
    assert brend.payment_method == "Annuitet, Differensial"
    assert brend.requires_collateral is True


def test_mikrokreditbank_avtokredit_ikkilamchi_parses_correctly():
    """"Foydalanilgan avtomobillar uchun avtokredit" — page <title> says
    "yo'l bosilgan avtomobillar uchun kredit" (used-car loan). "60 oygacha"
    appears twice on the page (summary card + "Qo'shimcha shartlar" table);
    extraction is scoped to the table block only, where header order
    (Muddati / Boshlang'ich badal / Yillik foiz stavkasi) maps to value
    order (60 oygacha / 40% / 24%)."""
    with patch("scrapers.mikrokreditbank.fetch_html", side_effect=_fake_fetch):
        products = MikrokreditBankScraper().run()

    ikkilamchi = next(p for p in products if p.category == "avtokredit_ikkilamchi")
    assert ikkilamchi.product_name == "Foydalanilgan avtomobillar uchun avtokredit"
    assert ikkilamchi.rate_min == 24.0
    assert ikkilamchi.rate_max == 24.0
    assert ikkilamchi.term_min_months == 60
    assert ikkilamchi.term_max_months == 60
    assert ikkilamchi.amount_max_som == 824_000_000
    assert ikkilamchi.down_payment_pct == 40.0
    assert ikkilamchi.grace_period_months == 0
    assert ikkilamchi.payment_method == "Annuitet, Differensial"
    assert ikkilamchi.requires_collateral is True


def test_mikrokreditbank_avtokredit_parses_correctly():
    with patch("scrapers.mikrokreditbank.fetch_html", side_effect=_fake_fetch):
        products = MikrokreditBankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.product_name == "Avtokredit UzAuto Motors"
    assert avtokredit.rate_min == 0.0
    assert avtokredit.rate_max == 0.0
    assert avtokredit.term_min_months == 60
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 824_000_000
    assert avtokredit.down_payment_pct == 25.0
    assert avtokredit.grace_period_months == 0
    assert avtokredit.payment_method == "Annuitet, Differensial"
    assert avtokredit.requires_collateral is True


def test_mikrokreditbank_mikroqarz_parses_correctly():
    """"Mikroqarz" is delivered "Kreditni rasmiylashtirish usuli: Bank
    ofisi" (branch visit) — offline mikroqarz category, not online. The
    amount section ("Kredit ajratishning eng yuqori miqdori") must stop at
    "Muammoli kreditlar" — without that boundary it runs to the end of the
    page and picks up an unrelated "824 mln" mention (the avtokredit
    product's own ceiling) as a false maximum instead of the real 100 mln."""
    with patch("scrapers.mikrokreditbank.fetch_html", side_effect=_fake_fetch):
        products = MikrokreditBankScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz")
    assert mikroqarz.product_name == "Mikroqarz"
    assert mikroqarz.rate_min == 24.0
    assert mikroqarz.rate_max == 28.0
    assert mikroqarz.term_min_months == 12
    assert mikroqarz.term_max_months == 60
    assert mikroqarz.amount_max_som == 100_000_000
    assert mikroqarz.requires_collateral is True
    assert mikroqarz.grace_period_months == 0
    assert mikroqarz.payment_method == "Annuitet, Differensial"


def test_mikrokreditbank_kredit_karta_parses_correctly():
    """"Kredit muddati" is stated as a bare "60 oy" (no "gacha" suffix) and
    the amount as a grouped exact sum ("100 000 000 so'mgacha") rather than
    "mln so'm" — both exercise the general fallback parsing added for
    InfinBank, confirming it isn't a one-bank special case."""
    with patch("scrapers.mikrokreditbank.fetch_html", side_effect=_fake_fetch):
        products = MikrokreditBankScraper().run()

    kredit_karta = next(p for p in products if p.category == "kredit_karta")
    assert kredit_karta.rate_min == 24.0
    assert kredit_karta.rate_max == 24.0
    assert kredit_karta.term_min_months == 60
    assert kredit_karta.term_max_months == 60
    assert kredit_karta.amount_max_som == 100_000_000


def test_mikrokreditbank_istemol_krediti_parses_correctly():
    with patch("scrapers.mikrokreditbank.fetch_html", side_effect=_fake_fetch):
        products = MikrokreditBankScraper().run()

    istemol_krediti = next(p for p in products if p.category == "istemol_krediti")
    assert istemol_krediti.rate_min == 28.0
    assert istemol_krediti.rate_max == 28.0
    assert istemol_krediti.term_min_months == 60
    assert istemol_krediti.term_max_months == 60
    assert istemol_krediti.amount_max_som == 150_000_000
    assert istemol_krediti.requires_collateral is True
