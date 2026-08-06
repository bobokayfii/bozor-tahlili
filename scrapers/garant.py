import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_grace_period_months,
    extract_payment_method,
    extract_percentages,
    extract_section,
    extract_term_months,
    fetch_html,
    has_collateral_requirement,
    html_to_text,
)

_YENGIL_AMOUNT_RE = re.compile(r"(\d{1,3}(?:[ \xa0]\d{3})+)(?:[.,]\d+)?\s*\([^)]*\)\s*so", re.IGNORECASE)
_MIKROZAJM_AMOUNT_RE = re.compile(r"(\d{1,4})(?:[.,]\d+)?\s*\([^)]*\)\s*million\s*so", re.IGNORECASE)
_PARENTHESIZED_TERM_RE = re.compile(r"(\d{1,3})\s*\([^)]*\)\s*oygacha")


class GarantBankScraper(TextSectionScraper):
    """Garant bank (garantbank.uz) mahsulot sahifalari o'zining "Kredit
    haqida" bo'limida "Ko'rsatkich / Qiymati" jadvalini beradi, unda
    summa "kengaytirilgan raqam + so'zda izoh" shaklida yoziladi
    (masalan "600 000 000,0 (olti yuz million) so'mgacha" yoki "100,0
    (bir yuz) million so'm") — scrapers/utils.py'dagi
    extract_amount_som'ning ikkala regex tarmog'i ham (raqam+"mln"+"so'm"
    yopishiq, yoki guruhlangan-minglik+"so'm" yopishiq) bu formatga mos
    kelmaydi, chunki qavs ichidagi so'z-izoh ular orasiga kirib qoladi.
    Shu sabab ikkita alohida bankka xos regex ishlatiladi — ikkala
    sahifa turli birlik ishlatgani uchun (biri to'liq so'm raqami,
    ikkinchisi million-qisqartma) ular BIRLASHTIRILMAYDI.

    Har bir sahifada bir xil yorliq ("Kredit miqdori"/"Foiz stavkasi"/
    "Kredit muddati") IKKI marta uchraydi: avval kichik harfli hero
    kartochka sifatida ("kredit miqdori"), keyin katta harfli batafsil
    jadvalda ("Kredit miqdori"). Bu holat naqadar qulay - katta/kichik
    harf farqi extract_section'ning birinchi (text.find) uchrashuvini
    to'g'ridan-to'g'ri kerakli (batafsil jadval) joyga yo'naltiradi,
    qo'shimcha toraytirish shart emas.

    mikrozajm-onlajn'ning batafsil jadvalidagi muddat "48 (qirq sakkiz)
    oygacha" — sonning o'zi bilan "oygacha" orasida so'zdagi izoh
    (parenthetical) bor, shu sabab extract_term_months (u \\s*oygacha
    ko'rinishida faqat bo'sh joy kutadi, qavscha emas) bu yerda hech
    narsa topolmaydi — xuddi summa formatidagi bilan bir xil muammo,
    shu sabab bu yerda ham alohida regex (_PARENTHESIZED_TERM_RE)
    ishlatiladi. Avtokredit «Yengil»'ning hero kartochkasidagi muddat esa
    ("60 oygacha", qavschasiz) bunday muammoga duch kelmaydi, shu sabab
    o'sha yerda umumiy extract_term_months baribir ishlatiladi.

    Avtokredit «Yengil» sahifasida "Imtiyozli muddat: Mavjud emas" iborasi
    garovga aloqasi yo'q (u imtiyozli davr haqida), lekin
    has_collateral_requirement to'liq sahifa matnida "mavjud emas"ni
    ko'rib, uni yolg'on-manfiy ("garov yo'q") deb talqin qilib qo'yardi —
    shu sabab bu yerda garov tekshiruvi "Mahsulot bo'yicha
    ta'minot" sarlavhasidan boshlab (haqiqiy "...garov ta'minoti..."
    joylashgan joy, va yuqoridagi "mavjud emas"dan keyin) toraytirilgan
    bo'limda o'tkaziladi. mikroqarz_onlayn sahifasida "garov" so'zi umuman
    yo'q va bunday chalkash "mavjud emas" ham yo'q, shu sabab u yerda
    to'liq sahifa matni xavfsiz ishlatilaveradi."""

    bank_name = "Garant bank"
    url = "https://garantbank.uz/uz/avtokredit-Yengil"
    CATEGORY_URLS = {
        "avtokredit_brend_birlamchi": "https://garantbank.uz/uz/avtokredit-Yengil",
        "mikroqarz_onlayn": "https://garantbank.uz/uz/mikrozajm-onlajn",
    }
    PRODUCT_NAMES = {
        "avtokredit_brend_birlamchi": "Avtokredit «Yengil»",
        "mikroqarz_onlayn": "Mikrozayim onlayn",
    }

    def run(self) -> list[Product]:
        now = datetime.now(timezone.utc)
        products: list[Product] = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)
                if category == "avtokredit_brend_birlamchi":
                    product = self._build_avtokredit_product(url, now, text)
                else:
                    product = self._build_mikrozajm_product(url, now, text)
            except Exception:
                continue
            if product is not None:
                products.append(product)
        return products

    def _build_avtokredit_product(self, url: str, now: datetime, text: str) -> Product | None:
        rate_term_section = extract_section(text, "kredit miqdori", "Kredit haqida")
        rates = extract_percentages(rate_term_section)
        terms = extract_term_months(rate_term_section)

        amount_section = extract_section(text, "Kredit miqdori", "Kredit muddati")
        amount_match = _YENGIL_AMOUNT_RE.search(amount_section)

        grace_section = extract_section(text, "Imtiyozli muddat", "Kredit valyutasi")
        grace_period_months = extract_grace_period_months("Imtiyozli muddat" + grace_section)

        payment_section = extract_section(text, "Foiz hisoblash", "Asosiy qarz")
        payment_method = extract_payment_method(payment_section)

        # "Imtiyozli muddat: Mavjud emas" earlier on this page trips
        # has_collateral_requirement's negative-phrase guard when scanning
        # full-page text (the guard doesn't know "mavjud emas" here refers to
        # the grace period, not collateral) — the actual collateral
        # statement ("...avtotransport vositasi garov ta'minoti...") lives
        # further down, under the "Mahsulot bo'yicha ta'minot" heading, so
        # scoping to everything from there onward (past the earlier "mavjud
        # emas") avoids the false negative. Unlike mikroqarz_onlayn, this
        # page cannot safely use unscoped full-page text.
        collateral_section = extract_section(text, "Mahsulot bo", None)
        requires_collateral = has_collateral_requirement(collateral_section)

        if not rates or not terms or amount_match is None:
            return None

        return Product(
            bank=self.bank_name,
            category="avtokredit_brend_birlamchi",
            product_name=self.PRODUCT_NAMES["avtokredit_brend_birlamchi"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=int(amount_match.group(1).replace(" ", "").replace("\xa0", "")),
            requires_collateral=requires_collateral,
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_mikrozajm_product(self, url: str, now: datetime, text: str) -> Product | None:
        rate_section = extract_section(text, "Minimal kredit foiz stavkasi", "Foiz hisoblash")
        rates = extract_percentages(rate_section)

        term_section = extract_section(text, "Kredit muddati", "Kreditning imtiyozli davri")
        term_match = _PARENTHESIZED_TERM_RE.search(term_section)
        terms = [int(term_match.group(1))] if term_match else []

        amount_section = extract_section(text, "Kredit miqdori", "Kredit muddati")
        amount_match = _MIKROZAJM_AMOUNT_RE.search(amount_section)

        grace_section = extract_section(text, "Kreditning imtiyozli davri", "Kredit maqsadi")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        payment_section = extract_section(text, "Foiz hisoblash", "Asosiy qarz")
        payment_method = extract_payment_method(payment_section)

        if not rates or not terms or amount_match is None:
            return None

        return Product(
            bank=self.bank_name,
            category="mikroqarz_onlayn",
            product_name=self.PRODUCT_NAMES["mikroqarz_onlayn"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=int(amount_match.group(1)) * 1_000_000,
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )
