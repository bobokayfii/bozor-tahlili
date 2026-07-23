from pathlib import Path
from unittest.mock import patch

from scrapers.infinbank import InfinBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    InfinBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "infin_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    InfinBankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (FIXTURES_DIR / "infin_ipoteka_tijorat.html").read_text(
        encoding="utf-8"
    ),
    InfinBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "infin_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    InfinBankScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "infin_kredit_karta.html").read_text(
        encoding="utf-8"
    ),
    InfinBankScraper.CATEGORY_URLS["istemol_krediti"]: (FIXTURES_DIR / "infin_istemol_krediti.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_infinbank_scraper_fetches_all_five_category_urls():
    with patch("scrapers.infinbank.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        InfinBankScraper().run()

    assert mock_fetch.call_count == 5
    mock_fetch.assert_any_call(
        InfinBankScraper.CATEGORY_URLS["avtokredit"], extra_ca_cert="infinbank_intermediate.pem"
    )


def test_infinbank_ipoteka_tijorat_parses_correctly():
    """"Ipoteka" — davlat mablag'i haqida ishora yo'q, bankning o'z
    mahsuloti; yakka tartibdagi uy-joy yoki kvartira sotib olish uchun.
    Muddat "180 oygacha" (15 yil) — bazaviy klassning umumiy
    CATEGORY_HEADINGS/_build_product mexanizmi ishlatilmaydi (uning 120
    oylik cheklovi 180 ni chetlab o'tar edi), shu sabab bu kategoriya
    uchun run() maxsus qayta yozilgan. Boshlang'ich badal "%" belgisisiz,
    so'z shaklida ("kamida 26 % miqdorida")."""
    with patch("scrapers.infinbank.fetch_html", side_effect=_fake_fetch):
        products = InfinBankScraper().run()

    tijorat = next(p for p in products if p.category == "ipoteka_tijorat")
    assert tijorat.bank == "InfinBank"
    assert tijorat.product_name == "Ipoteka"
    assert tijorat.rate_min == 20.99
    assert tijorat.rate_max == 24.99
    assert tijorat.term_min_months == 180
    assert tijorat.term_max_months == 180
    assert tijorat.amount_max_som == 1_236_000_000
    assert tijorat.down_payment_pct == 26.0
    assert tijorat.grace_period_months is None
    assert tijorat.payment_method is None
    assert tijorat.requires_collateral is True


def test_infinbank_mikroqarz_parses_correctly():
    with patch("scrapers.infinbank.fetch_html", side_effect=_fake_fetch):
        products = InfinBankScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz")
    assert mikroqarz.bank == "InfinBank"
    assert mikroqarz.rate_min == 28.99
    assert mikroqarz.rate_max == 28.99
    assert mikroqarz.term_min_months == 36
    assert mikroqarz.term_max_months == 36
    assert mikroqarz.amount_max_som == 100_000_000
    assert mikroqarz.requires_collateral is True


def test_infinbank_istemol_krediti_parses_correctly():
    with patch("scrapers.infinbank.fetch_html", side_effect=_fake_fetch):
        products = InfinBankScraper().run()

    istemol_krediti = next(p for p in products if p.category == "istemol_krediti")
    assert istemol_krediti.rate_min == 37.99
    assert istemol_krediti.rate_max == 37.99
    assert istemol_krediti.term_min_months == 18
    assert istemol_krediti.term_max_months == 18
    # Page states the exact sum ("41 200 000 so'mgacha"), not "mln so'm".
    assert istemol_krediti.amount_max_som == 41_200_000
    assert istemol_krediti.requires_collateral is True


def test_infinbank_avtokredit_yields_no_product_because_amount_is_unstated():
    """The avtokredit page prices loans against the vehicle's actual price
    ("Аvtotransport vositasining qiymatiga qarab") rather than a stated
    ceiling in so'm, across all of its variants. _build_product correctly
    skips a category it cannot find a concrete amount for, rather than
    fabricating one."""
    with patch("scrapers.infinbank.fetch_html", side_effect=_fake_fetch):
        products = InfinBankScraper().run()

    assert not any(p.category == "avtokredit" for p in products)


def test_infinbank_kredit_karta_parses_correctly():
    """"InfinBLACK" — aylanma kredit liniyali kredit karta. Toza
    "Maksimal kredit limiti" -> "Minimal to'lov" bo'limi stavka/limit
    beradi (100 mln UZS, 25,55%-54,75%), lekin muddat ("5 yil" — kredit
    limitining mavjudlik muddati) shu bo'limda yo'q; sahifaning yuqorisidagi
    alohida statistik kartadan aniq "Kredit limitining mavjudlik muddati"
    sarlavhasiga bog'langan maxsus regex bilan olinadi — pastroqdagi
    interaktiv kalkulyator qismi (slayder belgilari/komissiya foizlari
    bilan aralashib ketishi mumkin) chetlab o'tiladi. Sahifada "garov"/
    "ta'minot" so'zlari umuman yo'q — ta'minotsiz kredit karta."""
    with patch("scrapers.infinbank.fetch_html", side_effect=_fake_fetch):
        products = InfinBankScraper().run()

    kredit_karta = next(p for p in products if p.category == "kredit_karta")
    assert kredit_karta.bank == "InfinBank"
    assert kredit_karta.product_name == "InfinBLACK"
    assert kredit_karta.rate_min == 25.55
    assert kredit_karta.rate_max == 54.75
    assert kredit_karta.term_min_months == 60
    assert kredit_karta.term_max_months == 60
    assert kredit_karta.amount_max_som == 100_000_000
    assert kredit_karta.requires_collateral is False
    assert kredit_karta.down_payment_pct is None
    assert kredit_karta.grace_period_months is None
    assert kredit_karta.payment_method is None
