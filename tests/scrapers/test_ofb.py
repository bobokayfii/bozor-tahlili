from pathlib import Path
from unittest.mock import patch

from scrapers.ofb import OFBScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    OFBScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "ofb_avtokredit.html").read_text(encoding="utf-8"),
    OFBScraper.CATEGORY_URLS["avtokredit_elektro"]: (FIXTURES_DIR / "ofb_avtokredit_elektro.html").read_text(
        encoding="utf-8"
    ),
    OFBScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "ofb_mikroqarzlar.html").read_text(encoding="utf-8"),
    OFBScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (FIXTURES_DIR / "ofb_onlayn_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    OFBScraper.CATEGORY_URLS["ipoteka_davlat"]: (FIXTURES_DIR / "ofb_foydali_ipoteka.html").read_text(
        encoding="utf-8"
    ),
    OFBScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "ofb_niyat_kredit_kartasi.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_ofb_scraper_parses_all_categories():
    """mikroqarz and mikroqarz_onlayn share ONE fetch of the mikroqarzlar
    hub page (mikroqarz_onlayn also fetches its own onlayn-mikroqarz page
    for the term); ipoteka_davlat and kredit_karta each have their own
    dedicated page and do not participate in that sharing — so 6
    categories produce 6 total fetch_html calls (not 7), confirming the
    hub page isn't fetched twice."""
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = OFBScraper().run()

    assert mock_fetch.call_count == 6
    categories = {p.category for p in products}
    assert categories == {
        "avtokredit",
        "avtokredit_elektro",
        "mikroqarz",
        "mikroqarz_onlayn",
        "ipoteka_davlat",
        "kredit_karta",
    }
    assert all(p.bank == "OFB" for p in products)


def test_ofb_avtokredit_ignores_down_payment_share_percentages():
    """The real "Foiz stavkasi qancha?" table has two kinds of percentage
    per row — the down-payment SHARE (25/30/40/50%) and the actual annual
    rate that share unlocks (24,5/23,9/22,9/21,9%). A naive
    extract_percentages over that block would blend both sets together
    and push rate_max up to a bogus 50%; only the number after "dan —"
    should be picked up."""
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch):
        products = OFBScraper().run()

    avtokredit = next(p for p in products if p.category == "avtokredit")
    assert avtokredit.product_name == "Oson avtokredit"
    assert avtokredit.rate_min == 21.9
    assert avtokredit.rate_max == 24.5
    assert avtokredit.term_min_months == 60
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 800_000_000
    assert avtokredit.down_payment_pct == 25.0
    assert avtokredit.requires_collateral is True
    assert avtokredit.grace_period_months is None
    assert avtokredit.payment_method is None


def test_ofb_avtokredit_elektro_parses_dual_term_and_no_yillik_rate_table():
    """"Avtokredit BYD" shares the exact same FAQ template as "Oson
    avtokredit" but with different numbers: the term is stated as "36
    yoki 60 oyga" (two explicit options, no "oygacha" suffix, so the
    generic extract_term_months regex doesn't match it) and the rate
    table omits the word "yillik" entirely (unlike the plain avtokredit
    page) — both quirks are handled by dedicated regexes."""
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch):
        products = OFBScraper().run()

    elektro = next(p for p in products if p.category == "avtokredit_elektro")
    assert elektro.product_name == "Avtokredit BYD"
    assert elektro.rate_min == 18.9
    assert elektro.rate_max == 21.5
    assert elektro.term_min_months == 36
    assert elektro.term_max_months == 60
    assert elektro.amount_max_som == 800_000_000
    assert elektro.down_payment_pct == 25.0
    assert elektro.requires_collateral is True
    assert elektro.grace_period_months is None
    assert elektro.payment_method is None


def test_ofb_mikroqarz_parses_ishonch_card_from_shared_hub_page():
    """"Ishonch mikroqarz" is the SECOND card on the mikroqarzlar hub page
    (after "Onlayn mikroqarz"). The bare word "Ishonch" also appears much
    earlier on the same page inside an unrelated nav dropdown ("OFB
    Ishonch" — a savings product, "OFB Ishonchli" — a business loan), so a
    naive extract_section(hub_text, "Ishonch", ...) over the full page
    would anchor on the wrong, much earlier occurrence; the real
    implementation first narrows to the text after "Onlayn mikroqarz"
    (unique on the page) before looking for "Ishonch"."""
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch):
        products = OFBScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz")
    assert mikroqarz.product_name == "Ishonch mikroqarz"
    assert mikroqarz.rate_min == 24.0
    assert mikroqarz.rate_max == 24.0
    assert mikroqarz.term_min_months == 36
    assert mikroqarz.term_max_months == 36
    assert mikroqarz.amount_max_som == 100_000_000
    assert mikroqarz.requires_collateral is False
    assert mikroqarz.down_payment_pct is None
    assert mikroqarz.grace_period_months is None
    assert mikroqarz.payment_method is None
    assert mikroqarz.source_url == OFBScraper.CATEGORY_URLS["mikroqarz"]


def test_ofb_mikroqarz_onlayn_combines_hub_amount_rate_with_own_page_term():
    """"Onlayn mikroqarz" is the FIRST card on the shared hub page (amount
    and rate come from there), but the hub page never states its term —
    that's only on the product's own onlayn-mikroqarz page ("Mikroqarz
    muddati: 24 oygacha."). This confirms both sources get combined into
    one product without a second, redundant hub fetch (see
    test_ofb_scraper_parses_all_categories for the call-count check)."""
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch):
        products = OFBScraper().run()

    onlayn = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert onlayn.product_name == "Onlayn mikroqarz"
    assert onlayn.rate_min == 30.0
    assert onlayn.rate_max == 30.0
    assert onlayn.term_min_months == 24
    assert onlayn.term_max_months == 24
    assert onlayn.amount_max_som == 50_000_000
    assert onlayn.requires_collateral is False
    assert onlayn.down_payment_pct is None
    assert onlayn.grace_period_months is None
    assert onlayn.payment_method is None
    assert onlayn.source_url == OFBScraper.CATEGORY_URLS["mikroqarz_onlayn"]


def test_ofb_ipoteka_davlat_picks_largest_combined_amount_and_uncaps_240_month_term():
    """"Foydali ipoteka" is a state-program mortgage. Its "01. Kredit
    summasi" section lists THREE figures — a combined Tashkent ceiling
    (1,06 mlrd) plus two smaller state-program sub-limits by region (480
    mln, 380 mln) and a regional combined ceiling (960 mln); the platform
    schema wants the single largest overall figure a customer could
    borrow (1,06 mlrd, Tashkent), which extract_amount_som's built-in
    max()-of-all-matches already produces correctly without a custom
    regex.

    Its term is "240 oygacha" (20 years) — well past the standard
    extract_term_months helper's hard 120-month cap, which would silently
    drop it entirely (empty list). A dedicated regex is used instead, the
    same pattern other >120-month mortgage products in this codebase use
    (see scrapers/bdb.py's _YEAR_TERM_RE).

    Unlike the brief's "may not be present" assumption, a real down
    payment (25% dan), payment method (annuitet yoki differensial), and
    grace period (6 oy) ARE all stated on the page — just in a lower
    "Kreditlash shartlari" detail block rather than the "01/02/03" summary,
    and only reachable by narrowing past a decoy: an EARLIER, unrelated
    "Boshlang'ich badal" mention in the "Daromad talablari" section ("agar
    35% dan bo'lsa, daromadni tasdiqlash talab etilmaydi" — an income
    verification waiver threshold, not the actual minimum down payment)."""
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch):
        products = OFBScraper().run()

    ipoteka = next(p for p in products if p.category == "ipoteka_davlat")
    assert ipoteka.product_name == "Foydali ipoteka"
    assert ipoteka.rate_min == 17.0
    assert ipoteka.rate_max == 25.0
    assert ipoteka.term_min_months == 240
    assert ipoteka.term_max_months == 240
    assert ipoteka.amount_max_som == 1_060_000_000
    assert ipoteka.requires_collateral is True
    assert ipoteka.down_payment_pct == 25.0
    assert ipoteka.grace_period_months == 6
    assert ipoteka.payment_method == "Annuitet, Differensial"
    assert ipoteka.source_url == OFBScraper.CATEGORY_URLS["ipoteka_davlat"]


def test_ofb_kredit_karta_parses_clean_parameter_table_and_omits_lossy_grace_period():
    """"Kredit karta Niyat" lives at a `/kartalar/` URL path, unlike every
    other OFB category (all under `/kreditlar/`). Its page has a clean
    "Parametr / Shart" table where each heading ("Amal qilish muddati",
    "Imtiyozli muddat", "Maksimal summa", "Foiz stavkasi") appears exactly
    once, so each field is read from a tight, unambiguous slice between
    two neighboring headings — unlike the other five OFB categories, no
    multi-step narrowing or bespoke regex is needed here.

    "million so'm" appears twice on the real page (the summary table row
    and a later FAQ answer), but both state the identical 50 million
    figure, so this isn't an actual decoy — the narrow "Maksimal summa" ->
    "Foiz stavkasi" slice only ever reaches the first one anyway. The
    "Foiz stavkasi" section is deliberately narrowed to end at "Mahsulot
    va xizmatlar" so it doesn't also swallow the unrelated 0% / 0,5%
    service-fee percentages just below it in the raw text, which would
    otherwise drag rate_min down to 0.

    The page states the interest-free period only in DAYS ("45
    kungacha"), never in months, but Product.grace_period_months is a
    month-denominated field — 45 // 30 = 1 would understate the true
    ~1.5-month grace period and rounding up to 2 would overstate it, so
    there is no lossless conversion. This is the exact same day-vs-month
    mismatch that caused Apex Bank's kredit_karta category to be excluded
    entirely (confirmed: scrapers/apex.py's CATEGORY_URLS has no
    "kredit_karta" key at all). Here the category is kept — because the
    other four fields (limit, rate, term, product name) are all clean,
    concrete figures — but grace_period_months alone is left None rather
    than forcing a misleading rounded value into the wrong unit."""
    with patch("scrapers.ofb.fetch_html", side_effect=_fake_fetch):
        products = OFBScraper().run()

    kredit_karta = next(p for p in products if p.category == "kredit_karta")
    assert kredit_karta.product_name == "Kredit karta Niyat"
    assert kredit_karta.rate_min == 34.0
    assert kredit_karta.rate_max == 34.0
    assert kredit_karta.term_min_months == 36
    assert kredit_karta.term_max_months == 36
    assert kredit_karta.amount_max_som == 50_000_000
    assert kredit_karta.requires_collateral is False
    assert kredit_karta.down_payment_pct is None
    assert kredit_karta.grace_period_months is None
    assert kredit_karta.payment_method is None
    assert kredit_karta.source_url == OFBScraper.CATEGORY_URLS["kredit_karta"]
