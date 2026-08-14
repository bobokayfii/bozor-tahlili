from pathlib import Path
from unittest.mock import patch

from scrapers.trastbank import TrastBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    TrastBankScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "trastbank_avtokredit.html").read_text(
        encoding="utf-8"
    ),
    TrastBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "trastbank_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    TrastBankScraper.CATEGORY_URLS["ipoteka_tijorat"]: (
        FIXTURES_DIR / "trastbank_ipoteka_tijorat.html"
    ).read_text(encoding="utf-8"),
    TrastBankScraper.CATEGORY_URLS["ipoteka_davlat"]: (
        FIXTURES_DIR / "trastbank_ipoteka_davlat.html"
    ).read_text(encoding="utf-8"),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def _products_by_category():
    with patch("scrapers.trastbank.fetch_html", side_effect=_fake_fetch):
        products = TrastBankScraper().run()
    return {product.category: product for product in products}


def test_trastbank_avtokredit_and_ikkilamchi_share_one_page_covering_both_markets():
    """The "Avtokredit" page (https://trustbank.uz/uz/private/crediting/auto/)
    explicitly states it covers "birlamchi va ikkilamchi bozordan" (both
    primary and secondary market) car purchases in one place, unlike most
    other banks that split them into separate pages — so both categories
    map to the same URL and the same extracted figures. Four customer-segment
    tables each publish two rates (25% down for an unused car, 40% down for
    a used one) — down-payment percentages (25/40) are distinguished from
    real rate percentages (21-23.9%, never equal to 25 or 40) via
    _TRAST_AUTO_DOWN_VALUES rather than a heading-based section split, since
    all eight numbers sit under one shared "Foiz stavkasi" column header
    with no distinguishing text between them."""
    products = _products_by_category()

    for category in ("avtokredit", "avtokredit_ikkilamchi"):
        product = products[category]
        assert product.bank == "TrastBank"
        assert product.product_name == "Avtokredit"
        assert product.rate_min == 21.0
        assert product.rate_max == 23.9
        assert product.term_min_months == 60
        assert product.term_max_months == 60
        assert product.down_payment_pct == 25.0
        assert product.requires_collateral is True
        assert product.grace_period_months is None
        assert product.payment_method is None
        assert product.source_url == TrastBankScraper.CATEGORY_URLS["avtokredit"]


def test_trastbank_avtokredit_amount_falls_back_to_pptx_since_site_publishes_none():
    """The page never states a maximum loan amount anywhere — the calculator
    only has a blank "Kredit summasi" input field, not a real figure. Per
    this project's PPTX-fallback rule (existence confirmed live, only the
    numeric amount is missing), the max amount is pulled from the
    independently-verified competitor PPTX (2 000 mln so'm) and the
    fallback is documented via special_terms."""
    products = _products_by_category()

    for category in ("avtokredit", "avtokredit_ikkilamchi"):
        product = products[category]
        assert product.amount_max_som == 2_000_000_000
        assert "pptx" in (product.special_terms or "").lower()


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


def test_trastbank_ipoteka_davlat_reads_not_more_than_term_and_penalty_rate_is_excluded():
    """The "Sharq bahori ipoteka krediti" page (state/mixed-funding mortgage
    for the "Sharq bahori" housing complex in New Tashkent) states its term
    as "240 oydan ko'p bo'lmagan muddatga" ("not more than 240 months") — a
    word form the standard extract_term_months helper does not recognize
    (it only knows "N oygacha"/"N oydan M oygacha"), and even if it did,
    its 120-month hard cap would silently discard 240 anyway. So the
    dedicated _TERM_NOT_MORE_RE regex is used directly, bypassing
    extract_term_months entirely.

    The amount is stated as "800,0 mln so'mdan ko'p bo'lmagan miqdorda"
    (comma-decimal, same trap as ipoteka_tijorat's "700,0 mln so'mgacha") —
    ",0 mln" -> " mln" before extract_amount_som gives 800_000_000. Row 3.1
    also states a smaller 480,0 mln sub-limit split by funding source
    (state vs. bank), but the overall 800 mln figure takes priority since
    it is larger.

    The rate section states 17 foiz (fixed-income borrowers) / 18 foiz
    (self-employed) via word-form _FOIZ_RE, immediately followed (row 6.1,
    "Foizni hisoblashning sharti") by a conditional PENALTY clause: if the
    collateral is not registered within 20 days, the rate changes to 25
    foiz. That 25% is not part of the product's normal advertised rate
    range, so the rate_section's end_heading is "Foizni hisoblashning
    sharti" specifically to stop before it — verified directly against the
    live fixture that rate_max is 18.0, not 25.0."""
    products = _products_by_category()
    product = products["ipoteka_davlat"]

    assert product.bank == "TrastBank"
    assert product.category == "ipoteka_davlat"
    assert product.product_name == "Sharq bahori ipoteka krediti"
    assert product.rate_min == 17.0
    assert product.rate_max == 18.0
    assert product.term_min_months == 240
    assert product.term_max_months == 240
    assert product.amount_max_som == 800_000_000
    assert product.down_payment_pct == 15.0
    assert product.payment_method == "Annuitet, Differensial"
    assert product.source_url == TrastBankScraper.CATEGORY_URLS["ipoteka_davlat"]


def test_trastbank_ipoteka_davlat_grace_period_is_explicitly_none_available():
    """Unlike the task brief's initial assumption, the live "Sharq bahori"
    page DOES mention "imtiyozli" — its intro paragraph (before the
    numbered table) states, word for word, "Kreditning imtiyozli davri
    mavjud emas" (the exact same sentence ipoteka_tijorat's page uses).
    That is a real "none available" signal (0 months), not "unknown"
    (which would be None) — confirmed directly against the live fixture,
    not assumed from the brief."""
    products = _products_by_category()

    assert products["ipoteka_davlat"].grace_period_months == 0


def test_trastbank_ipoteka_davlat_force_collateral_is_true():
    """State/mixed-funding mortgages always require real-estate collateral,
    consistent with the FORCE_COLLATERAL convention used for ipoteka_tijorat
    and every other bank's mortgage category in this codebase (see
    scrapers/sqb.py, scrapers/ofb.py, scrapers/aab.py). This page's own
    "Ta'minot" row also describes the purchased apartment as collateral,
    later replacing an interim guarantor arrangement once the cadastral
    documents are finalized."""
    products = _products_by_category()

    assert products["ipoteka_davlat"].requires_collateral is True


def test_trastbank_scraper_fetches_all_category_pages():
    """avtokredit and avtokredit_ikkilamchi share one URL, so the number of
    fetch_html calls (5, one per CATEGORY_URLS entry) exceeds the number of
    distinct URLs actually requested (4)."""
    with patch("scrapers.trastbank.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        TrastBankScraper().run()

    fetched_urls = {call.args[0] for call in mock_fetch.call_args_list}
    assert fetched_urls == set(TrastBankScraper.CATEGORY_URLS.values())
    assert mock_fetch.call_count == 5
