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
    Har bir bank sinfi faqat bank_name, url, CATEGORY_HEADINGS'ni belgilaydi."""

    CATEGORY_HEADINGS: dict[str, tuple[str, str | None]] = {}

    def parse(self, html: str) -> list[Product]:
        text = html_to_text(html)
        now = datetime.now(timezone.utc)
        products: list[Product] = []

        for category, (start_heading, end_heading) in self.CATEGORY_HEADINGS.items():
            section = extract_section(text, start_heading, end_heading)
            if not section.strip():
                continue

            rates = extract_percentages(section)
            terms = extract_term_months(section)
            amount = extract_amount_som(section)
            if not rates or not terms or amount is None:
                continue

            products.append(
                Product(
                    bank=self.bank_name,
                    category=category,
                    product_name=f"{self.bank_name} {start_heading}",
                    rate_min=min(rates),
                    rate_max=max(rates),
                    term_min_months=min(terms),
                    term_max_months=max(terms),
                    amount_max_som=amount,
                    requires_collateral=has_collateral_requirement(section),
                    down_payment_pct=None,
                    source_url=self.url,
                    scraped_at=now,
                )
            )
        return products
