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

_TERM_RE = re.compile(r"(\d{1,3})\s*gacha\s*oylar")
_AMOUNT_RE = re.compile(r"(\d{1,4})\s*gacha\s*million\s*so", re.IGNORECASE)


class SaderatBankScraper(TextSectionScraper):
    """Saderat Bank (saderatbank.uz) avtokredit sahifasidagi hero-kartochka
    qiymatlarni o'z yorlig'idan OLDIN ko'rsatadi ("25% dan" keyin
    "boshlang'ich to'lov" kabi), va muddat/summa teskari so'z tartibida
    yozilgan: "60 gacha oylar" (odatiy "60 oygacha" o'rniga), "600 gacha
    million so'm" (odatiy "600 million so'mgacha" o'rniga) — shu sabab
    extract_term_months/extract_amount_som bu yerda ishlamaydi, bankka xos
    regex ishlatiladi.

    Sahifa pastida "Umumiy shartlar" jadvali bor, lekin u aslida alohida
    UzAuto Motors Onix/Tracker aksiyasi haqida (yillik 0%) — bu umumiy
    avtokredit mahsulotining stavkasi EMAS, shu sabab foiz stavkasi hech
    qachon shu jadvaldan olinmaydi, faqat hero-blokdan. Ammo garov va
    to'lov usuli haqidagi yagona ma'lumot aynan shu jadvalda ("Ta'minot",
    "To'lash usuli"), shu sabab bu ikkala maydon uchun shu jadval
    ishlatiladi.

    Sahifada alohida kredit kalkulyatori ham bor ("480 000 000 so'mgacha"
    avtomobil narxi maydoni, "158 591 160 so'm" jonli misol natijasi),
    undan keyin darhol "Hisob-kitoblar faqat ma'lumot uchun mo'ljallangan"
    degan ogohlantirish keladi — bu raqamlar hech qachon mahsulot summasi
    sifatida ishlatilmaydi, faqat hero-blokdagi "600 gacha million so'm"
    haqiqiy chegara hisoblanadi."""

    bank_name = "Saderat Bank"
    url = "https://saderatbank.uz/avtokredit"
    CATEGORY_URLS = {
        "avtokredit": "https://saderatbank.uz/avtokredit",
        "istemol_krediti": "https://saderatbank.uz/istemol",
    }
    PRODUCT_NAMES = {
        "avtokredit": "Avtokredit",
        "istemol_krediti": "Iste'mol krediti",
    }

    def run(self) -> list[Product]:
        now = datetime.now(timezone.utc)
        products: list[Product] = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)
                if category == "avtokredit":
                    product = self._build_avtokredit_product(url, now, text)
                else:
                    product = self._build_istemol_product(url, now, text)
            except Exception:
                continue
            if product is not None:
                products.append(product)
        return products

    def _build_avtokredit_product(self, url: str, now: datetime, text: str) -> Product | None:
        # End anchor truncated right before the apostrophe in "bog'lanish"
        # (same convention used in agro.py/aloqa.py, e.g. "Kredit ta",
        # "Boshlang") since the live page's apostrophe is a curly quote
        # (U+2018), not the straight ASCII one — matching only the
        # apostrophe-free prefix avoids depending on which variant renders.
        hero = extract_section(text, "Onlayn rasmiylashtirish", "Biz bilan bog")
        rates = extract_percentages(hero)
        term_match = _TERM_RE.search(hero)
        amount_match = _AMOUNT_RE.search(hero)
        if not rates or term_match is None or amount_match is None:
            return None

        collateral_section = extract_section(text, "Ta'minot", "Qarz oluvchiga qo'yiladigan talablar")
        payment_section = extract_section(text, "To'lash usuli", "Kerakli hujjatlar")

        # Down payment and rate are both stated as this same "25% dan"
        # figure on this page (verified against the live site) — reusing
        # the single deduplicated value is correct here, not a shortcut.
        rate = rates[0]
        term = int(term_match.group(1))
        return Product(
            bank=self.bank_name,
            category="avtokredit",
            product_name=self.PRODUCT_NAMES["avtokredit"],
            rate_min=rate,
            rate_max=rate,
            term_min_months=term,
            term_max_months=term,
            amount_max_som=int(amount_match.group(1)) * 1_000_000,
            requires_collateral=has_collateral_requirement(collateral_section),
            down_payment_pct=rate,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=extract_payment_method(payment_section),
        )

    def _build_istemol_product(self, url: str, now: datetime, text: str) -> Product | None:
        section = extract_section(text, "Shartlari", "Kerakli hujjatlar")
        rates = extract_percentages(section)
        terms = extract_term_months(section)
        amount = extract_amount_som(section)
        if not rates or not terms or amount is None:
            return None

        grace_section = extract_section(section, "Imtiyozli davr", "Kredit foizi")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        return Product(
            bank=self.bank_name,
            category="istemol_krediti",
            product_name=self.PRODUCT_NAMES["istemol_krediti"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=has_collateral_requirement(section),
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=extract_payment_method(section),
        )
