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

_MORTGAGE_TERM_RE = re.compile(r"(\d{1,3})\s*oygacha")
_FOIZ_WORD_RE = re.compile(r"(\d{1,2})\s*foiz")

_HAS_DOWN_PAYMENT = {"avtokredit_ikkilamchi", "ipoteka_davlat"}


class AsiaAllianceBankScraper(TextSectionScraper):
    """Asia Alliance Bank (aab.uz) barcha retail kredit sahifalari bitta
    umumiy CMS shabloniga ega: "Umumiy shartlar" bo'limi ichida ketma-ket
    "Kredit maqsadi", "Kredit valyutasi", "Kredit miqdori", (faqat
    avtokredit/ipoteka sahifalarida) "Dastlabki to'lov", "Foiz stavkasi",
    "Kredit muddati", "Kreditni rasmiylashtirish usuli", "Berish shakli",
    "Kredit ta'minoti", "Imtiyozli davr", "To'lov usuli", "To'lovlar
    davriyligi" — har bir yorliq shu blok ichida FAQAT bir marta uchraydi
    (to'g'ridan-to'g'ri tekshirilgan).

    MUHIM: "Foiz stavkasi"/"Kredit muddati" kabi yorliqlarning har biri
    sahifada YANA bir marta, "Umumiy shartlar"dan OLDIN, takroriy "hero
    stat" kartochkasi sifatida ham uchraydi. Shu sabab har qanday
    quyi-qidiruv avval to'liq sahifa matnidan emas, balki ALLAQACHON
    "Umumiy shartlar" -> "To'lovlar davriyligi" oralig'iga toraytirilgan
    `section` ichidan qilinadi — aks holda extract_section noto'g'ri
    (oldingi, hero) uchrashuvdan boshlab olib ketadi.

    "Kredit ta'minoti" jumlasida (masalan "avtomobil summasining 70% dan
    ko'p bo'lmagan") va "Dastlabki to'lov"da ("Avtomobil qiymatining 25%
    dan") stavkaga aloqasi yo'q foizlar bor — shu sabab foiz stavkasi
    faqat "Foiz stavkasi" -> "Kredit muddati" tor oralig'idan olinadi.

    ipoteka_davlat'ning boshlang'ich to'lovi "15 foizidan" (% belgisisiz,
    so'z shaklida) yozilgan — extract_percentages "%" belgisini talab
    qilgani uchun bu yerda alohida so'z-asosli regex ishlatiladi
    (aloqa.py'dagi _DAVLAT_DOWN_RE bilan bir xil yechim). Muddati "240
    oygacha" — extract_term_months barcha natijalarni 120 oy bilan
    cheklaydi va aks holda bo'sh ro'yxat qaytaradi, shu sabab bu yerda
    ham to'g'ridan-to'g'ri regex ishlatiladi (aloqa.py'dagi
    _MORTGAGE_TERM_RE bilan bir xil yechim)."""

    bank_name = "Asia Alliance Bank"
    url = "https://aab.uz/uz/private/crediting/avtokredit-vtorichnyy-rynok-/"
    CATEGORY_URLS = {
        "avtokredit_ikkilamchi": "https://aab.uz/uz/private/crediting/avtokredit-vtorichnyy-rynok-/",
        "mikroqarz": "https://aab.uz/uz/private/crediting/mikrozaym-imkon-/",
        "mikroqarz_onlayn": "https://aab.uz/uz/private/crediting/mikrozaym-online-/",
        "ipoteka_davlat": "https://aab.uz/uz/private/crediting/ipotechnyy-kredit-novyy-dom/",
    }
    PRODUCT_NAMES = {
        "avtokredit_ikkilamchi": "Avtokredit «Ikkilamchi»",
        "mikroqarz": "Mikroqarz «Imkon»",
        "mikroqarz_onlayn": "Mikroqarz «Online»",
        "ipoteka_davlat": "Ipoteka krediti - Yangi uy (Iqtisodiyot va moliya vazirligi mablag'lari hisobidan)",
    }

    def run(self) -> list[Product]:
        now = datetime.now(timezone.utc)
        products: list[Product] = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)
                product = self._build_product_from_template(category, url, now, text)
            except Exception:
                continue
            if product is not None:
                products.append(product)
        return products

    def _build_product_from_template(self, category: str, url: str, now: datetime, text: str) -> Product | None:
        section = extract_section(text, "Umumiy shartlar", "To'lovlar davriyligi")
        if not section.strip():
            return None

        rate_section = extract_section(section, "Foiz stavkasi", "Kredit muddati")
        rates = extract_percentages(rate_section)

        term_section = extract_section(section, "Kredit muddati", "Kreditni rasmiylashtirish usuli")
        if category == "ipoteka_davlat":
            term_match = _MORTGAGE_TERM_RE.search(term_section)
            terms = [int(term_match.group(1))] if term_match else []
        else:
            terms = extract_term_months(term_section)

        amount_end = "Dastlabki to'lov" if category in _HAS_DOWN_PAYMENT else "Foiz stavkasi"
        amount_section = extract_section(section, "Kredit miqdori", amount_end)
        amount = extract_amount_som(amount_section)

        if not rates or not terms or amount is None:
            return None

        down_payment_pct = None
        if category in _HAS_DOWN_PAYMENT:
            down_section = extract_section(section, "Dastlabki to'lov", "Foiz stavkasi")
            if category == "ipoteka_davlat":
                down_match = _FOIZ_WORD_RE.search(down_section)
                down_payment_pct = float(down_match.group(1)) if down_match else None
            else:
                down_rates = extract_percentages(down_section)
                down_payment_pct = min(down_rates) if down_rates else None

        grace_section = extract_section(section, "Imtiyozli davr", "To'lov usuli")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        payment_section = extract_section(section, "To'lov usuli", "To'lovlar davriyligi")
        payment_method = extract_payment_method(payment_section)

        collateral_section = extract_section(section, "Kredit ta'minoti", "Imtiyozli davr")
        requires_collateral = has_collateral_requirement(collateral_section)

        return Product(
            bank=self.bank_name,
            category=category,
            product_name=self.PRODUCT_NAMES[category],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=requires_collateral,
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )
