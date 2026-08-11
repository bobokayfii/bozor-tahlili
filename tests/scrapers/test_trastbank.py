from pathlib import Path
from unittest.mock import patch

from scrapers.trastbank import TrastBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    TrastBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "trastbank_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    TrastBankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (
        FIXTURES_DIR / "trastbank_ipoteka_tijorat.html"
    ).read_text(encoding="utf-8"),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def _products_by_category():
    with patch("scrapers.trastbank.fetch_html", side_effect=_fake_fetch):
        products = TrastBankScraper().run()
    return {product.category: product for product in products}


def test_trastbank_mikroqarz_combines_three_customer_segments_into_one_range():
    """The real "Mikroqarzlar" page lists THREE customer-segment tables back
    to back (fixed-income earners, self-employed, payroll-project/education
    -and-healthcare workers), each with its own rate/term/amount figures.
    Rather than extracting them separately, the implementation takes the
    ENTIRE span from "Doimiy daromadga ega bo" (start of the first segment)
    to "Mikroqarz rasmiylashtirishda" (the unique heading right after the
    third segment, at the start of the required-documents list) as one
    section, then runs the standard extract_percentages/extract_term_months/
    extract_amount_som over it. This is deliberate, not an artifact: all
    five real rate tables (28/29/30, then 29/30/31.9 for segment 1;
    28/29/30 for segment 2; 24/25/26, then 25/26.5/27.9 for segment 3) and
    all three amount figures (100 mln, 50,0 mln, 100 mln) are genuinely
    published for the live product, just spread across sub-tables.

    NOTE: as of Task 2, TrastBankScraper.run() is a custom override (no
    longer the base TextSectionScraper.run() default) that dispatches
    "mikroqarz" through the same generic CATEGORY_HEADINGS/_build_product
    path the base class used to run directly — this test's expectations
    are unchanged from Task 1, only the fetch_html patch target moved from
    scrapers.base to scrapers.trastbank (see _fake_fetch usage above)."""
    products = _products_by_category()

    product = products["mikroqarz"]
    assert product.bank == "TrastBank"
    assert product.category == "mikroqarz"
    assert product.product_name == "Mikroqarz"
    assert product.rate_min == 24.0
    assert product.rate_max == 31.9
    assert product.term_min_months == 12
    assert product.term_max_months == 60
    assert product.amount_max_som == 100_000_000
    assert product.requires_collateral is True
    assert product.down_payment_pct is None
    assert product.payment_method is None
    assert product.source_url == TrastBankScraper.CATEGORY_URLS["mikroqarz"]


def test_trastbank_mikroqarz_grace_period_is_explicitly_none_available():
    """The page states, right before the first segment table, "Mikroqarzning
    imtiyozli davri: mavjud emas" ("no grace period available") — a real
    "none" signal (0 months), not an "unknown" (which would be None)."""
    products = _products_by_category()

    assert products["mikroqarz"].grace_period_months == 0


def test_trastbank_mikroqarz_force_collateral_overrides_false_negative_auto_detection():
    """Naive has_collateral_requirement() on the raw page text would
    actually return False here: the page's own "imtiyozli davri: mavjud
    emas" sentence puts the phrase "mavjud emas" into the full page text,
    which trips has_collateral_requirement's negative-match branch even
    though real collateral (guarantor/insurance/vehicle-or-property
    pledge) is required by every one of the three customer segments. This
    is exactly why FORCE_COLLATERAL is used instead of auto-detection for
    this category."""
    products = _products_by_category()

    assert products["mikroqarz"].requires_collateral is True


def test_trastbank_ipoteka_tijorat_reads_word_form_percentages_and_comma_decimal_amount():
    """The "Bankning o'z mablag'lari hisobidan ajratiladigan ipoteka
    krediti" page states rates as "23 foiz"/"24 foiz" (word form, no "%"
    sign) rather than "23%"/"24%" — the standard extract_percentages helper
    only recognizes "%" and would find nothing, so _FOIZ_RE is used
    instead. The amount is stated as "700,0 mln so'mgacha" (comma-decimal
    immediately before "mln") — extract_amount_som's million-figure regex
    does not expect a comma there and would silently match just the "0"
    after the comma (giving a bogus near-zero amount) rather than failing
    loudly, so ",0 mln" is replaced with " mln" before calling
    extract_amount_som. The page also states two RELATIVE/BHM-multiplier
    housing-amount figures ("Bazaviy hisoblash miqdorining 2 500/3 000
    barobarigacha") alongside the literal "700,0 mln so'mgacha" figure —
    only the literal figure counts toward amount_max_som."""
    products = _products_by_category()
    product = products["ipoteka_tijorat"]

    assert product.bank == "TrastBank"
    assert product.category == "ipoteka_tijorat"
    assert product.product_name == "Bankning o'z mablag'lari hisobidan ajratiladigan ipoteka krediti"
    assert product.rate_min == 23.0
    assert product.rate_max == 24.0
    assert product.term_min_months == 120
    assert product.term_max_months == 120
    assert product.amount_max_som == 700_000_000
    assert product.down_payment_pct == 20.0
    assert product.payment_method == "Annuitet, Differensial"
    assert product.grace_period_months == 0
    assert product.source_url == TrastBankScraper.CATEGORY_URLS["ipoteka_tijorat"]


def test_trastbank_ipoteka_tijorat_force_collateral_is_true():
    """Mortgages always require real-estate collateral by definition, even
    though this page's own "Ta'minot" row describes it as "Kredit hisobiga
    sotib olinayotgan uy-joy (kvartira)" rather than literally using the
    word "garov" — the same FORCE_COLLATERAL convention used for every
    other bank's mortgage category in this codebase (see scrapers/sqb.py,
    scrapers/ofb.py, scrapers/aab.py)."""
    products = _products_by_category()

    assert products["ipoteka_tijorat"].requires_collateral is True


def test_trastbank_scraper_fetches_both_category_pages():
    with patch("scrapers.trastbank.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        TrastBankScraper().run()

    fetched_urls = {call.args[0] for call in mock_fetch.call_args_list}
    assert fetched_urls == set(TrastBankScraper.CATEGORY_URLS.values())
    assert mock_fetch.call_count == 2
