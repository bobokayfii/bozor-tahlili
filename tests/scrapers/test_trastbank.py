from pathlib import Path
from unittest.mock import patch

from scrapers.trastbank import TrastBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    TrastBankScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "trastbank_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


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
    published for the live product, just spread across sub-tables."""
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = TrastBankScraper().run()

    assert len(products) == 1
    product = products[0]
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
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = TrastBankScraper().run()

    product = products[0]
    assert product.grace_period_months == 0


def test_trastbank_mikroqarz_force_collateral_overrides_false_negative_auto_detection():
    """Naive has_collateral_requirement() on the raw page text would
    actually return False here: the page's own "imtiyozli davri: mavjud
    emas" sentence puts the phrase "mavjud emas" into the full page text,
    which trips has_collateral_requirement's negative-match branch even
    though real collateral (guarantor/insurance/vehicle-or-property
    pledge) is required by every one of the three customer segments. This
    is exactly why FORCE_COLLATERAL is used instead of auto-detection for
    this category."""
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch):
        products = TrastBankScraper().run()

    product = products[0]
    assert product.requires_collateral is True


def test_trastbank_scraper_fetches_only_the_microloans_page():
    with patch("scrapers.base.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        TrastBankScraper().run()

    assert mock_fetch.call_count == 1
    assert mock_fetch.call_args.args[0] == TrastBankScraper.CATEGORY_URLS["mikroqarz"]
