from pathlib import Path
from unittest.mock import patch

from scrapers.agro import AgroBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    AgroBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "agro_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    AgroBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "agro_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    AgroBankScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "agro_kredit_karta.html").read_text(
        encoding="utf-8"
    ),
    AgroBankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (FIXTURES_DIR / "agro_ipoteka_tijorat.html").read_text(
        encoding="utf-8"
    ),
    AgroBankScraper.CATEGORY_URLS["ipoteka_davlat"]: (FIXTURES_DIR / "agro_ipoteka_davlat.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_agro_scraper_parses_all_five_categories():
    """"istemol_krediti" was removed: its old URL ("loans/green-energy")
    was actually a solar-panel/green-energy financing product, not a
    general consumer loan — a miscategorization, not the real thing.
    AgroBank's current loan lineup has no distinct general-purpose
    consumer-loan product at all (only purpose-specific ones: education,
    green energy, marketplace BNPL, various mortgages/microloans)."""
    with patch("scrapers.agro.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = AgroBankScraper().run()

    assert mock_fetch.call_count == 5
    categories = {p.category for p in products}
    assert categories == {
        "avtokredit",
        "mikroqarz",
        "kredit_karta",
        "ipoteka_tijorat",
        "ipoteka_davlat",
    }
    assert all(p.bank == "AgroBank" for p in products)


def test_agro_kredit_karta_parses_correctly():
    """"Kredit karta" — revolver tarzida ajratiladigan kredit karta.
    "Kredit karta faqat oxirgi 6 oy ichida barqaror daromadga ega
    bo'lgan fuqarolarga beriladi" jumlasidagi "6 oy" haqiqiy "4 yil (48
    oy)" muddatidan oldin yolg'on ravishda term sifatida olinishi mumkin
    edi — shu sabab muddat faqat "Kredit muddati:" sarlavhasiga
    bog'langan maxsus regex bilan olinadi. Foiz stavkasi ikkita mijoz
    toifasi uchun beriladi ("27% (Ish haqi loyihasi...)" / "30% (Doimiy
    daromad...)"). Kredit miqdori "100 000 000 (yuz million) so'mgacha"
    — grouped son bilan "so'mgacha" orasida qavscha bo'lgani uchun
    umumiy extract_amount_som mos kelmaydi, maxsus regex ishlatiladi."""
    with patch("scrapers.agro.fetch_html", side_effect=_fake_fetch):
        products = AgroBankScraper().run()

    kredit_karta = next(p for p in products if p.category == "kredit_karta")
    assert kredit_karta.product_name == "Kredit karta"
    assert kredit_karta.rate_min == 27.0
    assert kredit_karta.rate_max == 30.0
    assert kredit_karta.term_min_months == 48
    assert kredit_karta.term_max_months == 48
    assert kredit_karta.amount_max_som == 100_000_000
    assert kredit_karta.requires_collateral is True
    assert kredit_karta.down_payment_pct is None
    assert kredit_karta.grace_period_months is None
    assert kredit_karta.payment_method is None


def test_agro_ipoteka_davlat_parses_correctly():
    """""Ijtimoiy ko'mak" ipoteka krediti — nomining o'zi davlat ijtimoiy
    yordam dasturi ekanini bildiradi; "Subsidiya" bo'limida aniq
    yozilgan: kredit miqdorining 15 foizi subsidiya sifatida ajratiladi,
    dastlabki 5 yil davomida foiz stavkasining 12%dan oshgan qismini
    davlat qoplaydi — "Bizdan uy" (ipoteka_tijorat, bankning o'z
    mablag'i)dan farqli. Yakka tartibdagi uy-joy qurish/rekonstruksiya/
    ta'mirlash uchun (tayyor kvartira xaridi emas). Sahifada "ta'minot"
    o'rniga "garov ta'minoti" so'zi ishlatilgani uchun has_collateral_
    requirement to'g'ri True qaytaradi, FORCE_COLLATERAL kerak emas."""
    with patch("scrapers.agro.fetch_html", side_effect=_fake_fetch):
        products = AgroBankScraper().run()

    davlat = next(p for p in products if p.category == "ipoteka_davlat")
    assert davlat.product_name == '"Ijtimoiy ko\'mak" ipoteka krediti'
    assert davlat.rate_min == 18.0
    assert davlat.rate_max == 18.0
    assert davlat.term_min_months == 240
    assert davlat.term_max_months == 240
    assert davlat.amount_max_som == 120_000_000
    assert davlat.down_payment_pct == 15.0
    assert davlat.grace_period_months is None
    assert davlat.payment_method == "Annuitet, Differensial"
    assert davlat.requires_collateral is True


def test_agro_ipoteka_tijorat_parses_correctly():
    """""Bizdan uy" ipoteka krediti — "O'z mablag'lari hisobidan ipoteka
    krediti" (bank's own funds, not state-funded); birlamchi/ikkilamchi
    uy-joy uchun. Rate/down-payment tiers given inline ("boshlang'ich
    badal 40% - yillik foiz stavkasi 23,99%") — dedicated "yillik foiz
    stavkasi N%" regex isolates the real rate. No absolute amount in the
    static list (tied to house price) — the calculator's own ceiling
    ("900 000 000 сум gacha", Cyrillic currency word + \xa0 grouping) is
    used instead."""
    with patch("scrapers.agro.fetch_html", side_effect=_fake_fetch):
        products = AgroBankScraper().run()

    tijorat = next(p for p in products if p.category == "ipoteka_tijorat")
    assert tijorat.product_name == '"Bizdan uy" ipoteka krediti'
    assert tijorat.rate_min == 23.99
    assert tijorat.rate_max == 24.99
    assert tijorat.term_min_months == 180
    assert tijorat.term_max_months == 180
    assert tijorat.amount_max_som == 900_000_000
    assert tijorat.down_payment_pct == 25.0
    assert tijorat.grace_period_months == 12
    assert tijorat.payment_method == "Annuitet, Differensial"
    assert tijorat.requires_collateral is True


def test_agro_avtokredit_parses_correctly():
    """The avtokredit fixture is Playwright-rendered real content (SPA),
    unlike the other three categories' fixtures which still encode
    secondary-aggregator figures. It covers both the 0% promo tiers
    (specific models, 24-60 month terms) and the standard rate table
    (24%-27%, 4-5 year terms) — both must be reflected in rate_min/
    rate_max and term_min/term_max."""
    with patch("scrapers.agro.fetch_html", side_effect=_fake_fetch):
        products = AgroBankScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.product_name == "Avtokredit (birlamchi bozor uchun)"
    assert avtokredit.rate_min == 0.0
    assert avtokredit.rate_max == 27.0
    assert avtokredit.term_min_months == 24
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 300_000_000
    assert avtokredit.down_payment_pct == 25.0
    assert avtokredit.payment_method == "Annuitet, Differensial"
    assert avtokredit.grace_period_months is None
    assert avtokredit.requires_collateral is True
