from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from categories import CATEGORIES
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

_CATEGORY_LABELS: dict[str, str] = {category.key: category.label_uz for category in CATEGORIES}


@dataclass
class Product:
    bank: str
    category: str
    product_name: str
    rate_min: float
    rate_max: float
    term_min_months: int
    term_max_months: int
    amount_max_som: int
    requires_collateral: bool
    down_payment_pct: float | None
    source_url: str
    scraped_at: datetime
    grace_period_months: int | None = None
    payment_method: str | None = None
    special_terms: str | None = None


class BaseScraper(ABC):
    bank_name: str
    url: str
    # Set to a filename under scrapers/certs/ when the bank's server sends an
    # incomplete certificate chain (see fetch_html's extra_ca_cert param).
    EXTRA_CA_CERT: str | None = None

    def run(self) -> list[Product]:
        html = fetch_html(self.url, extra_ca_cert=self.EXTRA_CA_CERT)
        return self.parse(html)

    @abstractmethod
    def parse(self, html: str) -> list[Product]:
        ...


class TextSectionScraper(BaseScraper):
    """Umumiy parser: HTML'ni matnga aylantirib, sarlavhalar orasidagi
    bo'limlardan foiz stavkasi, muddat, summa va garov ma'lumotini o'qiydi.
    Har bir bank sinfi faqat bank_name, url, CATEGORY_HEADINGS'ni belgilaydi.

    Ba'zi banklar retail kredit kategoriyalarini bitta sahifada emas, balki
    alohida sahifalarda joylashtiradi. Bunday holatda CATEGORY_URLS'ni
    belgilang: {category: url}. CATEGORY_HEADINGS shu category uchun ham
    berilgan bo'lsa, mos sahifa matni o'sha sarlavhalar bilan toraytiriladi;
    aks holda butun sahifa matni bo'lim sifatida ishlatiladi."""

    CATEGORY_HEADINGS: dict[str, tuple[str, str | None]] = {}
    CATEGORY_URLS: dict[str, str] | None = None
    # Ba'zi mahsulotlar uchun garov talabi mahsulot turi bo'yicha shubhasiz
    # ma'lum (masalan, avtokredit doim sotib olingan avtomobilning o'zi bilan
    # ta'minlanadi), lekin sahifa matnida buni aniq "garov" so'zi bilan
    # yozilmasligi mumkin — chunki bu odatiy amaliyot sifatida qabul qilinadi.
    # Bunday holatlarda matndan aniqlashga urinish o'rniga shu yerda aniq
    # qiymat belgilanadi: {category: requires_collateral}.
    FORCE_COLLATERAL: dict[str, bool] = {}
    # Mahsulotning saytdagi haqiqiy (asl) nomi — berilmasa, umumiy
    # "{bank_name} {kategoriya}" shakli ishlatiladi.
    PRODUCT_NAMES: dict[str, str] = {}
    # Boshlang'ich badal, imtiyozli davr va to'lov usuli ko'pincha stavka
    # jadvalidan tashqarida (yoki undan ataylab chetlab o'tilgan, foiz
    # kontaminatsiyasidan qochish uchun) joylashadi — shuning uchun ular
    # CATEGORY_HEADINGS bilan bir xil mantiqda, lekin alohida sarlavha
    # juftliklari orqali, xuddi shu sahifa matnidan qo'shimcha ravishda
    # qidiriladi. Berilmasa, mos maydon bo'sh (None) qoladi.
    DOWN_PAYMENT_HEADINGS: dict[str, tuple[str, str | None]] = {}
    PAYMENT_METHOD_HEADINGS: dict[str, tuple[str, str | None]] = {}
    GRACE_PERIOD_HEADINGS: dict[str, tuple[str, str | None]] = {}

    def _extract_down_payment_pct(self, category: str, text: str) -> float | None:
        heading_pair = self.DOWN_PAYMENT_HEADINGS.get(category)
        if heading_pair is None:
            return None
        section = extract_section(text, *heading_pair)
        rates = extract_percentages(section)
        return min(rates) if rates else None

    def _extract_payment_method(self, category: str, text: str) -> str | None:
        heading_pair = self.PAYMENT_METHOD_HEADINGS.get(category)
        section = extract_section(text, *heading_pair) if heading_pair is not None else text
        return extract_payment_method(section)

    def _extract_grace_period_months(self, category: str, text: str) -> int | None:
        heading_pair = self.GRACE_PERIOD_HEADINGS.get(category)
        if heading_pair is None:
            return extract_grace_period_months(text)
        start_heading, end_heading = heading_pair
        section = extract_section(text, start_heading, end_heading)
        # extract_section strips the start_heading itself out of the result,
        # but extract_grace_period_months requires the word "imtiyozli" to be
        # present (as a guard against false positives on unscoped text) — so
        # the heading is prefixed back on before handing the section over.
        return extract_grace_period_months(start_heading + section)

    def _build_product(
        self,
        category: str,
        section: str,
        source_url: str,
        scraped_at: datetime,
        full_text: str | None = None,
        down_payment_pct: float | None = None,
        grace_period_months: int | None = None,
        payment_method: str | None = None,
    ) -> Product | None:
        if not section.strip():
            return None

        rates = extract_percentages(section)
        terms = extract_term_months(section)
        amount = extract_amount_som(section)
        if not rates or not terms or amount is None:
            return None

        # Garov/kafillik talablari ko'pincha stavka jadvalidan ancha pastda,
        # alohida "Ta'minot talablari" bo'limida joylashadi — ba'zan o'sha
        # bo'limning o'zida ham foiz belgilari bor (masalan, "ta'minot
        # miqdori kredit summasining 125%"). Shu sababli garov tekshiruvi
        # har doim to'liq sahifa matnida (full_text) o'tkaziladi, toraytirilgan
        # `section`da emas — aks holda foiz kontaminatsiyasidan qochish uchun
        # bo'limni tor qilib olsak, garov ma'lumoti ham yo'qolib qoladi.
        collateral_text = full_text if full_text is not None else section
        requires_collateral = (
            self.FORCE_COLLATERAL[category]
            if category in self.FORCE_COLLATERAL
            else has_collateral_requirement(collateral_text)
        )

        label = _CATEGORY_LABELS.get(category, category)
        product_name = self.PRODUCT_NAMES.get(category) or f"{self.bank_name} {label}"
        return Product(
            bank=self.bank_name,
            category=category,
            product_name=product_name,
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=requires_collateral,
            down_payment_pct=down_payment_pct,
            source_url=source_url,
            scraped_at=scraped_at,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def parse(self, html: str) -> list[Product]:
        text = html_to_text(html)
        now = datetime.now(timezone.utc)
        products: list[Product] = []

        for category, (start_heading, end_heading) in self.CATEGORY_HEADINGS.items():
            try:
                section = extract_section(text, start_heading, end_heading)
                product = self._build_product(
                    category,
                    section,
                    self.url,
                    now,
                    down_payment_pct=self._extract_down_payment_pct(category, text),
                    grace_period_months=self._extract_grace_period_months(category, text),
                    payment_method=self._extract_payment_method(category, text),
                )
            except Exception:
                continue
            if product is not None:
                products.append(product)
        return products

    def run(self) -> list[Product]:
        if self.CATEGORY_URLS is None:
            return super().run()

        now = datetime.now(timezone.utc)
        products: list[Product] = []

        for category, url in self.CATEGORY_URLS.items():
            # Har bir kategoriya o'z URL'idan mustaqil olinadi — bittasi
            # (masalan, o'chirilgan yoki manzili o'zgargan sahifa, 404)
            # butun bank uchun barcha boshqa kategoriyalarni ham yo'qotib
            # qo'ymasligi kerak (bu xato avval NBU'da "istemol_krediti"ning
            # 404 qaytarishi sabab "avtokredit" ham hech qachon
            # yangilanmasligiga olib kelgan edi).
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)

                heading_pair = self.CATEGORY_HEADINGS.get(category)
                if heading_pair is not None:
                    start_heading, end_heading = heading_pair
                    section = extract_section(text, start_heading, end_heading)
                else:
                    section = text

                product = self._build_product(
                    category,
                    section,
                    url,
                    now,
                    full_text=text,
                    down_payment_pct=self._extract_down_payment_pct(category, text),
                    grace_period_months=self._extract_grace_period_months(category, text),
                    payment_method=self._extract_payment_method(category, text),
                )
            except Exception:
                continue
            if product is not None:
                products.append(product)
        return products
