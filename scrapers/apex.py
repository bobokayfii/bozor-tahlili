import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_grace_period_months,
    extract_payment_method,
    extract_percentages,
    extract_section,
    extract_term_months,
    fetch_html,
    has_collateral_requirement,
    html_to_text,
)

_IPOTEKA_TERM_RE = re.compile(r"(\d{1,3})\s*dan\s*(\d{1,3})\s*oygacha")


class ApexBankScraper(TextSectionScraper):
    """Apex Bank (apexbank.uz) har bir mahsulot sahifasida "Kredit
    muddati"/"Foiz stavkasi"/"Kredit miqdori" kabi yorliqlar 2-3 marta
    takrorlanadi: hero-kartochkada, interaktiv kalkulyator vidjetida (ba'zan
    hech qanday matnsiz, faqat yalang' son sifatida) va haqiqiy "batafsil
    shartlar" bo'limida. Shu sabab har bir _build_* metod avval sahifani
    FAQAT bir marta uchraydigan sarlavha ("Kreditning minimal va maksimal
    miqdori", "Kreditning maksimal summasi") bilan tor bo'limga ajratadi —
    shu tor bo'lim ichida keyingi barcha extract_section chaqiruvlari
    xavfsiz, chunki kalkulyator/hero takrorlari allaqachon chetlab
    o'tilgan.

    offlayn-kredit sahifasida asosiy muddat "6 dan 36 oygacha" shaklida —
    "oy" so'zisiz ("6 oydan" emas) — shu sabab umumiy extract_term_months
    buni range sifatida tanimaydi. Lekin shu bo'limning davomida (bir xil
    tor "Kredit muddati".."Imtiyozli davr" bo'lagida) ish haqi loyihasi
    ishtirokchilari uchun to'liq "N oydan M oygacha" shaklidagi 5 ta bosqich
    ham bor (6 oydan 9 oygacha, ..., 25 oydan 36 oygacha) — shularning eng
    kichik/eng katta chegaralari aynan 6 va 36 ga teng, shuning uchun
    umumiy extract_term_months o'sha bosqichlar orqali to'g'ri javob beradi
    va bexos "36 oygacha" yagona ko'rsatkichiga tushib qolmaydi (chunki
    range topilgan holatda extract_term_months yagona ko'rsatkichlarni
    e'tiborsiz qoldiradi). Xuddi shu tor bo'lakda foiz stavkasi ham bor
    (asosiy "28% dan 35% gacha" va bosqichli "22%...30%"), shu sabab bitta
    tor bo'lak ham muddat, ham stavka uchun ishlatiladi.

    ipoteka-comfort sahifasidagi muddat ham "6 dan 120 oygacha" — birinchi
    sondan keyin "oy" so'zi yo'q — lekin bu sahifada muddat range'ini
    qoplaydigan bosqichli foiz jadvali yo'q, shu sabab bu yerda alohida
    regex ishlatiladi."""

    bank_name = "Apex Bank"
    url = "https://apexbank.uz/customer/offlayn-kredit/"
    CATEGORY_URLS = {
        "mikroqarz": "https://apexbank.uz/customer/offlayn-kredit/",
        "mikroqarz_onlayn": "https://apexbank.uz/customer/onlayn-kredit/",
        "ipoteka_tijorat": "https://apexbank.uz/customer/ipoteka-comfort/",
    }
    PRODUCT_NAMES = {
        "mikroqarz": "Offlayn kredit",
        "mikroqarz_onlayn": "Onlayn kredit",
        "ipoteka_tijorat": "Ipoteka Comfort",
    }

    def run(self) -> list[Product]:
        now = datetime.now(timezone.utc)
        products: list[Product] = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)
                if category == "mikroqarz":
                    product = self._build_offline_product(url, now, text)
                elif category == "mikroqarz_onlayn":
                    product = self._build_online_product(url, now, text)
                else:
                    product = self._build_ipoteka_product(url, now, text)
            except Exception:
                continue
            if product is not None:
                products.append(product)
        return products

    def _build_offline_product(self, url: str, now: datetime, text: str) -> Product | None:
        # End anchor truncated before the apostrophe in "sug'urta" (the
        # live page uses a curly U+2018 there, not a straight ASCII
        # apostrophe) — same apostrophe-free-prefix convention as
        # agro.py/aloqa.py.
        detail = extract_section(text, "Kreditning minimal va maksimal miqdori", "Majburiy sug")
        # No "eng kam miqdori" sub-label actually precedes the figure on
        # this page (unlike the onlayn variant below) — the amount is the
        # only "N so'm"-tagged figure left in `detail` after the outer
        # bracket already excluded the calculator/hero duplicates, so it
        # can be read directly off the narrowed block.
        amount = extract_amount_som(detail)

        rate_term_section = extract_section(detail, "Kredit muddati", "Imtiyozli davr")
        terms = extract_term_months(rate_term_section)
        rates = extract_percentages(rate_term_section)
        if amount is None or not terms or not rates:
            return None

        grace_section = extract_section(detail, "Imtiyozli davr", "Kechiktirilgan")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        payment_section = extract_section(detail, "Qaytarish usuli", "Foizlar va asosiy")
        # Apostrophe-free prefix ("bo'yicha"/"ta'minlash" both contain
        # curly apostrophes on the live page); no end heading needed since
        # `detail` already ends right where "Majburiy sug'urta" begins.
        collateral_section = extract_section(detail, "Kredit bo", None)

        return Product(
            bank=self.bank_name,
            category="mikroqarz",
            product_name=self.PRODUCT_NAMES["mikroqarz"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=has_collateral_requirement(collateral_section),
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=extract_payment_method(payment_section),
        )

    def _build_online_product(self, url: str, now: datetime, text: str) -> Product | None:
        detail = extract_section(text, "Kreditning minimal va maksimal miqdori", None)
        amount_section = extract_section(detail, "eng kam miqdori", "Kredit valyutasi")
        amount = extract_amount_som(amount_section)

        # Same tor bo'lak texnikasi as the offline build: this page's own
        # "Kredit muddati" statement is properly fused ("6 oydan 36
        # oygacha"), and the following tiered rate list shares the same
        # 6-36 range, so a single narrowed section covers both term and
        # rate cleanly.
        rate_term_section = extract_section(detail, "Kredit muddati", "Imtiyozli davr")
        terms = extract_term_months(rate_term_section)
        rates = extract_percentages(rate_term_section)
        if amount is None or not terms or not rates:
            return None

        grace_section = extract_section(detail, "Imtiyozli davr", "Muddati o")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        # This page's heading is "So'ndirish usuli" (curly apostrophe
        # after "So") — anchored on the apostrophe-free suffix "ndirish
        # usuli" instead of truncating the prefix, since "So" alone would
        # also match unrelated "So'm" occurrences.
        payment_section = extract_section(detail, "ndirish usuli", "Foizlar va asosiy")
        # No "garov" word appears anywhere on this page (only an insurance
        # policy is required) — has_collateral_requirement correctly
        # resolves to False here regardless of the exact section bounds,
        # verified directly against the fixture.
        collateral_section = extract_section(detail, "Kredit ta", "Mahsulot")

        return Product(
            bank=self.bank_name,
            category="mikroqarz_onlayn",
            product_name=self.PRODUCT_NAMES["mikroqarz_onlayn"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=has_collateral_requirement(collateral_section),
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=extract_payment_method(payment_section),
        )

    def _build_ipoteka_product(self, url: str, now: datetime, text: str) -> Product | None:
        # "Kreditning maksimal summasi" appears only once on this page, so
        # no outer detail-bracket is needed before sub-scoping (unlike the
        # two microloan pages above, which repeat labels several times).
        amount_term_section = extract_section(text, "Kreditning maksimal summasi", "Boshlang")
        amount = extract_amount_som(amount_term_section)
        term_match = _IPOTEKA_TERM_RE.search(amount_term_section)

        down_section = extract_section(text, "Boshlang", "Imtiyozli davr")
        down_rates = extract_percentages(down_section)

        grace_section = extract_section(text, "Imtiyozli davr", "Foiz stavkasi miqdori")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        rate_section = extract_section(text, "Foiz stavkasi miqdori", "Muddati o")
        rates = extract_percentages(rate_section)

        if amount is None or term_match is None or not rates:
            return None

        return Product(
            bank=self.bank_name,
            category="ipoteka_tijorat",
            product_name=self.PRODUCT_NAMES["ipoteka_tijorat"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=int(term_match.group(1)),
            term_max_months=int(term_match.group(2)),
            amount_max_som=amount,
            # Mortgage collateral (the purchased property) is universal
            # for this product type; the page never places the literal
            # word "garov" next to a safely-unique anchor, so this is
            # hardcoded rather than built on a fragile guess.
            requires_collateral=True,
            down_payment_pct=min(down_rates) if down_rates else None,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            # No "Annuitet"/"Differensial" keyword appears anywhere near
            # a reliable anchor on this page (only the descriptive "Har
            # oy teng ulushlarda") — left unset rather than guessed.
            payment_method=None,
        )
