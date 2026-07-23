from pathlib import Path
from unittest.mock import patch

from scrapers.nbu import NBUScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    NBUScraper.CATEGORY_URLS["avtokredit"]: (FIXTURES_DIR / "nbu_avtokredit.html").read_text(encoding="utf-8"),
    NBUScraper.CATEGORY_URLS["avtokredit_ikkilamchi"]: (
        FIXTURES_DIR / "nbu_avtokredit_ikkilamchi.html"
    ).read_text(encoding="utf-8"),
    NBUScraper.CATEGORY_URLS["avtokredit_brend_birlamchi"]: (
        FIXTURES_DIR / "nbu_avtokredit_brend_birlamchi.html"
    ).read_text(encoding="utf-8"),
    NBUScraper.CATEGORY_URLS["avtokredit_elektro"]: (FIXTURES_DIR / "nbu_avtokredit_elektro.html").read_text(
        encoding="utf-8"
    ),
    NBUScraper.CATEGORY_URLS["mikroqarz"]: (FIXTURES_DIR / "nbu_mikroqarz.html").read_text(encoding="utf-8"),
    NBUScraper.CATEGORY_URLS["mikroqarz_onlayn"]: (FIXTURES_DIR / "nbu_onlayn_mikroqarz.html").read_text(
        encoding="utf-8"
    ),
    NBUScraper.CATEGORY_URLS["kredit_karta"]: (FIXTURES_DIR / "nbu_kredit_karta.html").read_text(encoding="utf-8"),
    NBUScraper.CATEGORY_URLS["ipoteka_davlat"]: (FIXTURES_DIR / "nbu_ipoteka_davlat.html").read_text(
        encoding="utf-8"
    ),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_nbu_scraper_parses_all_eight_categories():
    """"istemol_krediti" was removed: its old URL
    ("jismoniy-shaxslarga-kreditlar/istemol-krediti") now 404s, and the
    site's current credit hub lists no consumer-loan sub-page at all
    (only avtokreditlar/ipoteka-kreditlari/mikroqarzlar/national-green/
    overdraft/talim-krediti-1) — the product appears to have been
    discontinued (consistent with the competitor-analysis pptx, used
    here only as corroborating context, marking NBU's "Iste'mol krediti"
    as "Vaqtincha to'xtatilgan")."""
    with patch("scrapers.nbu.fetch_html", side_effect=_fake_fetch) as mock_fetch:
        products = NBUScraper().run()

    assert mock_fetch.call_count == 8
    categories = {p.category for p in products}
    assert categories == {
        "avtokredit",
        "avtokredit_ikkilamchi",
        "avtokredit_brend_birlamchi",
        "avtokredit_elektro",
        "mikroqarz",
        "mikroqarz_onlayn",
        "kredit_karta",
        "ipoteka_davlat",
    }
    assert all(p.bank == "NBU" for p in products)


def test_nbu_ipoteka_davlat_parses_correctly():
    """"Standard ipoteka krediti" — "Kreditlash manbai: O'zbekiston
    Respublikasi Iqtisodiyot va moliya vazirligi mablag'lari" deb aniq
    yozilgan — davlat (byudjet) mablag'i, bankning boshqa sahifadagi
    "Bankning o'z mablag'lari hisobidan" tijorat mahsulotidan farqli.
    Stavka mijoz toifasi x boshlang'ich badal ulushiga qarab beriladi
    ("Dastlabki badalning 15% to'langanda - yillik 17%" kabi) — "yillik
    N%" va "badalning N%" uchun alohida regexlar ishlatiladi."""
    with patch("scrapers.nbu.fetch_html", side_effect=_fake_fetch):
        products = NBUScraper().run()

    davlat = next(p for p in products if p.category == "ipoteka_davlat")
    assert davlat.product_name == "Standard ipoteka krediti"
    assert davlat.rate_min == 16.5
    assert davlat.rate_max == 17.0
    assert davlat.term_min_months == 240
    assert davlat.term_max_months == 240
    assert davlat.amount_max_som == 480_000_000
    assert davlat.down_payment_pct == 15.0
    assert davlat.grace_period_months == 6
    assert davlat.payment_method == "Annuitet, Differensial"
    assert davlat.requires_collateral is True


def test_nbu_avtokredit_elektro_parses_correctly():
    """"Elektromobillar va gibridlar uchun avtokredit" — bir xil "Kredit
    maqsadi" -> tierli stavka jadvali shabloni ("avtokredit" bilan bir xil
    _build_avtokredit_product metodi orqali, faqat category parametri
    farq qiladi). Bu sahifada "Kredit xavfsizligi" sarlavhasi umuman yo'q
    — extract_section matn oxirigacha davom etadi, lekin _RATE_TIER_RE
    yetarlicha o'ziga xos bo'lgani uchun bu xavfsiz."""
    with patch("scrapers.nbu.fetch_html", side_effect=_fake_fetch):
        products = NBUScraper().run()

    elektro = next(p for p in products if p.category == "avtokredit_elektro")
    assert elektro.product_name == "Elektromobillar va gibridlar uchun avtokredit"
    assert elektro.rate_min == 21.0
    assert elektro.rate_max == 22.0
    assert elektro.term_min_months == 12
    assert elektro.term_max_months == 48
    assert elektro.amount_max_som == 500_000_000
    assert elektro.down_payment_pct == 30.0
    assert elektro.grace_period_months == 6
    assert elektro.payment_method == "Annuitet, Differensial"
    assert elektro.requires_collateral is True

    avtokredit = next(p for p in products if p.category == "avtokredit")
    # Guards against the "imtiyozli davr" (grace period) figure being
    # mis-extracted as the term minimum (previously 6 instead of 12).
    assert avtokredit.term_min_months == 12
    assert avtokredit.term_max_months == 60
    assert avtokredit.product_name == "Yangi avtomobillar uchun avtokredit"
    # Rate table is "20% - 21% yillik" / "30% - 20% yillik" (official
    # income) and "30% - 22% yillik" (self-employed) — first number of each
    # pair is the down-payment tier, second is the actual rate; they must
    # not be conflated even though both fall in a similar 20-30% range.
    assert avtokredit.rate_min == 20.0
    assert avtokredit.rate_max == 22.0
    assert avtokredit.down_payment_pct == 20.0
    assert avtokredit.amount_max_som == 1_000_000_000
    assert avtokredit.grace_period_months == 6
    assert avtokredit.payment_method == "Annuitet, Differensial"
    assert avtokredit.requires_collateral is True


def test_nbu_avtokredit_brend_birlamchi_parses_correctly():
    """"Avtokredit KIA, Chery" — birlamchi bozordan KIA (Carens, K9,
    Sportage, K5C, EV6) va Chery avtomobillari uchun. "Kredit shartlari"
    tab-bo'limida 6 ta mustaqil narx jadvali bor (model guruhi x mijoz
    toifasi), har biri 30%/40%/50% boshlang'ich to'lov ulushi x 12-60 oy
    muddat bo'yicha guruhlangan; "Imtiyozli davr: 6 oygacha" alohida
    ajratilmasa umumiy muddat aniqlashga aralashib, 12 o'rniga 6 ni
    noto'g'ri minimal muddat sifatida ko'rsatadi."""
    with patch("scrapers.nbu.fetch_html", side_effect=_fake_fetch):
        products = NBUScraper().run()

    brend = next(p for p in products if p.category == "avtokredit_brend_birlamchi")
    assert brend.product_name == "Avtokredit KIA, Chery"
    assert brend.rate_min == 0.0
    assert brend.rate_max == 22.5
    assert brend.term_min_months == 12
    assert brend.term_max_months == 60
    assert brend.amount_max_som == 1_000_000_000
    assert brend.down_payment_pct == 30.0
    assert brend.grace_period_months == 6
    assert brend.payment_method is None
    assert brend.requires_collateral is True


def test_nbu_avtokredit_ikkilamchi_parses_correctly():
    """"Ikkilamchi bozor uchun avtokredit" — product name states it's the
    secondary market. Rate table is grouped by down-payment tier just like
    the primary-market avtokredit ("20% – 22% yillik" / "30% – 21% yillik"
    / "30% - 23% yilik" for self-employed), so the same tier-pair regex is
    reused. "Kreditni ta'minlash" doesn't use the word "garov", so
    collateral is forced True (same convention as other avtokredit
    scrapers) rather than trusting the generic keyword check."""
    with patch("scrapers.nbu.fetch_html", side_effect=_fake_fetch):
        products = NBUScraper().run()

    ikkilamchi = next(p for p in products if p.category == "avtokredit_ikkilamchi")
    assert ikkilamchi.product_name == "Ikkilamchi bozor uchun avtokredit"
    assert ikkilamchi.rate_min == 21.0
    assert ikkilamchi.rate_max == 23.0
    assert ikkilamchi.term_min_months == 12
    assert ikkilamchi.term_max_months == 48
    assert ikkilamchi.amount_max_som == 500_000_000
    assert ikkilamchi.down_payment_pct == 20.0
    assert ikkilamchi.grace_period_months == 3
    assert ikkilamchi.payment_method is None
    assert ikkilamchi.requires_collateral is True


def test_nbu_mikroqarz_parses_correctly():
    """"Mikroqarz" info sheet states "1. Kreditning turi: Mikroqarz" (no
    "Onlayn" prefix) and is disbursed via cash or card transfer — the
    offline category. Its "Kredit muddati" heading repeats 4 times on the
    page (empty calculator fields + the real list); the extraction must
    land on the real values (60 oygacha / 24-28% / 100 mln so'mgacha)
    rather than an empty calculator field."""
    with patch("scrapers.nbu.fetch_html", side_effect=_fake_fetch):
        products = NBUScraper().run()

    mikroqarz = next(p for p in products if p.category == "mikroqarz")
    assert mikroqarz.product_name == "Mikroqarz"
    assert mikroqarz.rate_min == 24.0
    assert mikroqarz.rate_max == 28.0
    assert mikroqarz.term_min_months == 60
    assert mikroqarz.term_max_months == 60
    assert mikroqarz.amount_max_som == 100_000_000
    # "Ta'minot: Mol-mulk garovi, uchinchi shaxs kafilligi yoki ..." lists
    # property collateral as one of the accepted options.
    assert mikroqarz.requires_collateral is True
    assert mikroqarz.grace_period_months is None
    assert mikroqarz.payment_method is None


def test_nbu_mikroqarz_onlayn_parses_correctly():
    """"Onlayn mikroqarz" page title is "Onlayn mikrozaym — NBU" and states
    "Onlayn rasmiylashtirish: Ofisga bormasdan va qog'ozbozliksiz kreditni
    rasmiylashtiring" — the online category. Its security is an insurance
    policy only ("Kreditni qaytarmaslik xavfidan sug'urta polisi"), not
    property collateral, unlike the offline "Mikroqarz" product."""
    with patch("scrapers.nbu.fetch_html", side_effect=_fake_fetch):
        products = NBUScraper().run()

    mikroqarz_onlayn = next(p for p in products if p.category == "mikroqarz_onlayn")
    assert mikroqarz_onlayn.product_name == "Onlayn mikroqarz"
    assert mikroqarz_onlayn.rate_min == 25.0
    assert mikroqarz_onlayn.rate_max == 28.0
    assert mikroqarz_onlayn.term_min_months == 36
    assert mikroqarz_onlayn.term_max_months == 60
    assert mikroqarz_onlayn.amount_max_som == 100_000_000
    assert mikroqarz_onlayn.requires_collateral is False
    assert mikroqarz_onlayn.grace_period_months is None
    assert mikroqarz_onlayn.payment_method is None
