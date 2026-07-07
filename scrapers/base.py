from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from scrapers.utils import (
    extract_amount_som,
    extract_percentages,
    extract_section,
    extract_term_months,
    fetch_html,
    has_collateral_requirement,
    html_to_text,
)


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


class BaseScraper(ABC):
    bank_name: str
    url: str

    def run(self) -> list[Product]:
        html = fetch_html(self.url)
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

    def _build_product(
        self,
        category: str,
        section: str,
        source_url: str,
        scraped_at: datetime,
        heading: str | None = None,
    ) -> Product | None:
        if not section.strip():
            return None

        rates = extract_percentages(section)
        terms = extract_term_months(section)
        amount = extract_amount_som(section)
        if not rates or not terms or amount is None:
            return None

        label = heading if heading is not None else category
        return Product(
            bank=self.bank_name,
            category=category,
            product_name=f"{self.bank_name} {label}",
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=has_collateral_requirement(section),
            down_payment_pct=None,
            source_url=source_url,
            scraped_at=scraped_at,
        )

    def parse(self, html: str) -> list[Product]:
        text = html_to_text(html)
        now = datetime.now(timezone.utc)
        products: list[Product] = []

        for category, (start_heading, end_heading) in self.CATEGORY_HEADINGS.items():
            section = extract_section(text, start_heading, end_heading)
            product = self._build_product(category, section, self.url, now, heading=start_heading)
            if product is not None:
                products.append(product)
        return products

    def run(self) -> list[Product]:
        if self.CATEGORY_URLS is None:
            return super().run()

        now = datetime.now(timezone.utc)
        products: list[Product] = []

        for category, url in self.CATEGORY_URLS.items():
            html = fetch_html(url)
            text = html_to_text(html)

            heading_pair = self.CATEGORY_HEADINGS.get(category)
            if heading_pair is not None:
                start_heading, end_heading = heading_pair
                section = extract_section(text, start_heading, end_heading)
            else:
                start_heading = category
                section = text

            product = self._build_product(category, section, url, now, heading=start_heading)
            if product is not None:
                products.append(product)
        return products
