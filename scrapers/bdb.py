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

_YEAR_TERM_RE = re.compile(r"(\d{1,2})\s*yilgacha")


class BDBScraper(TextSectionScraper):
    """BDB / Biznesni rivojlantirish banki (brb.uz) sahifalarida "Kredit
    muddati"/"Kredit miqdori" kabi yorliqlar bir necha marta uchraydi —
    masalan mikroqarz sahifasida "Kredit muddati" ikki marta chiqadi: bir
    marta HAQIQIY qiymat sifatida, so'ng muddat-bo'yicha-stavka jadvalining
    ustun sarlavhasi sifatida. Har bir _build_* metod avval sahifani FAQAT
    bir marta uchraydigan sarlavha ("Kredit maqsadi"/"Kreditning maqsadi")
    bilan tor bo'limga ajratadi, shundan keyingina ichki extract_section
    chaqiruvlari xavfsiz bo'ladi.

    Ko'pchilik boshqa avtokredit/mikroqarz sahifalarida ("shartnoma
    qiymatining N% gacha" formulasi bilan) aniq so'm raqami umuman yo'q —
    bu bank uchun faqat aniq raqam beruvchi 3 ta sahifa tanlangan, aks
    holda Octobank'dagi bilan bir xil muammoga duch kelinar edi.

    ipoteka_davlat'ning muddati "20 yilgacha" (240 oy) — extract_term_months
    barcha natijalarni 120 oy bilan cheklaydi, shu sabab bu yerda ham
    to'g'ridan-to'g'ri regex ishlatiladi (aab.py'dagi ipoteka_davlat bilan
    bir xil yechim).

    MUHIM (apostrof): brb.uz sahifalarida bir xil sahifa ichida turli xil
    apostrof belgilari ishlatiladi — masalan "Boshlang'ich badal" so'zida
    U+2018 (‘), "Ta'minot miqdori"da U+2019 (’), "O'zbekiston"da yana U+2018
    ishlatilgan (fixture'lardan to'g'ridan-to'g'ri tekshirilgan), mikroqarz
    sahifasidagi "To'lov turi"/"Ta'minot turi"da esa oddiy ASCII apostrof
    (U+0027) ishlatilgan. Shu sabab apostrof o'z ichiga olgan har qanday
    anchor apostrofsiz qismga qisqartirilgan (masalan "Boshlang", "minot
    miqdori", "zbekiston Respublikasi fuqarosi bo") — mikroqarz sahifasidagi
    "To'lov turi"/"Ta'minot turi" esa ASCII apostrof bilan to'g'ridan-to'g'ri
    tekshirilgani uchun o'zgarishsiz qoldirilgan."""

    bank_name = "BRB"
    url = "https://brb.uz/jismoniy-shaxslarga/kreditlar/avtokredit"
    CATEGORY_URLS = {
        "avtokredit": "https://brb.uz/jismoniy-shaxslarga/kreditlar/avtokredit",
        "mikroqarz": "https://brb.uz/jismoniy-shaxslarga/kreditlar/mikroqarz",
        "ipoteka_davlat": "https://brb.uz/jismoniy-shaxslarga/ipoteka/birlamchi-ipoteka",
    }
    PRODUCT_NAMES = {
        "avtokredit": "Avtokredit",
        "mikroqarz": "Mikroqarz",
        "ipoteka_davlat": "Birlamchi ipoteka",
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
                elif category == "mikroqarz":
                    product = self._build_mikroqarz_product(url, now, text)
                else:
                    product = self._build_ipoteka_product(url, now, text)
            except Exception:
                continue
            if product is not None:
                products.append(product)
        return products

    def _build_avtokredit_product(self, url: str, now: datetime, text: str) -> Product | None:
        section = extract_section(text, "Kredit maqsadi", "Talablar")

        amount_section = extract_section(section, "Kredit miqdori", "Kredit muddati")
        term_section = extract_section(section, "Kredit muddati", "Foiz stavkasi")
        # End anchor truncated before the apostrophe in "Boshlang'ich badal"
        # (the live page uses a curly U+2018 there, not a straight ASCII
        # apostrophe) — same apostrophe-free-prefix convention as
        # agro.py/aloqa.py/apex.py.
        rate_section = extract_section(section, "Foiz stavkasi", "Boshlang")
        # "Ta'minot miqdori" uses a different curly apostrophe (U+2019) at
        # this exact spot — anchored on the apostrophe-free suffix "minot
        # miqdori" instead of the prefix, matching the same fix pattern.
        down_section = extract_section(section, "Boshlang", "minot miqdori")
        grace_section = extract_section(section, "Imtiyozli davr", "Mijoz segmenti")

        amount = extract_amount_som(amount_section)
        terms = extract_term_months(term_section)
        rates = extract_percentages(rate_section)
        if amount is None or not terms or not rates:
            return None

        down_rates = extract_percentages(down_section)
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        return Product(
            bank=self.bank_name,
            category="avtokredit",
            product_name=self.PRODUCT_NAMES["avtokredit"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=True,
            down_payment_pct=min(down_rates) if down_rates else None,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=extract_payment_method(section),
        )

    def _build_mikroqarz_product(self, url: str, now: datetime, text: str) -> Product | None:
        detail = extract_section(text, "Kredit maqsadi", "Rasmiy daromadga ega bo'lgan shaxslar")

        amount_section = extract_section(detail, "Kredit miqdori", "To'lov turi")
        term_section = extract_section(detail, "Kredit muddati", "Kredit miqdori")
        rate_section = extract_section(detail, "Ish haqi lohiyasidagi mijozlar uchun", "Rasmiy daromadga")
        payment_section = extract_section(detail, "To'lov turi", "Ta'minot turi")
        collateral_section = extract_section(detail, "Ta'minot turi", "Kredit muddati")

        amount = extract_amount_som(amount_section)
        terms = extract_term_months(term_section)
        rates = extract_percentages(rate_section)
        if amount is None or not terms or not rates:
            return None

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
            grace_period_months=None,
            payment_method=extract_payment_method(payment_section),
        )

    def _build_ipoteka_product(self, url: str, now: datetime, text: str) -> Product | None:
        # End anchor truncated before the apostrophe in "O'zbekiston
        # Respublikasi fuqarosi bo'lishi lozim" (the live page uses a curly
        # U+2018 there, not a straight ASCII apostrophe) — apostrophe-free
        # suffix, same convention as above.
        section = extract_section(text, "Kreditning maqsadi", "zbekiston Respublikasi fuqarosi bo")

        # "Boshlang'ich badal" uses the same curly U+2018 apostrophe as on
        # the avtokredit page — apostrophe-free prefix.
        down_section = extract_section(section, "Boshlang", "Kredit miqdori")
        amount_section = extract_section(section, "Kredit miqdori", "Kredit muddati")
        term_section = extract_section(section, "Kredit muddati", "Foiz stavkasi")
        rate_section = extract_section(section, "Foiz stavkasi", "Kredit valyutasi")
        grace_section = extract_section(section, "Imtiyozli davr", "Uchinchi shaxs kafilligi")
        payment_section = extract_section(section, "Grafik", "Imtiyozli davr")

        down_rates = extract_percentages(down_section)
        amount = extract_amount_som(amount_section)
        term_match = _YEAR_TERM_RE.search(term_section)
        rates = extract_percentages(rate_section)
        if amount is None or term_match is None or not rates:
            return None

        term = int(term_match.group(1)) * 12
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        return Product(
            bank=self.bank_name,
            category="ipoteka_davlat",
            product_name=self.PRODUCT_NAMES["ipoteka_davlat"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=term,
            term_max_months=term,
            amount_max_som=amount,
            requires_collateral=True,
            down_payment_pct=min(down_rates) if down_rates else None,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=extract_payment_method(payment_section),
        )
