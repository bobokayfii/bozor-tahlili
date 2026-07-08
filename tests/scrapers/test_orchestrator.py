from datetime import datetime, timezone
from unittest.mock import patch

from db.models import ProductRow, ScrapeRunRow
from scrapers.base import BaseScraper, Product
from scrapers.orchestrator import run_all_scrapers


class WorkingScraper(BaseScraper):
    bank_name = "WorkingBank"
    url = "https://working.uz"

    def parse(self, html: str) -> list[Product]:
        return []

    def run(self) -> list[Product]:
        return [
            Product(
                bank="WorkingBank", category="avtokredit", product_name="test",
                rate_min=20.0, rate_max=25.0, term_min_months=12, term_max_months=48,
                amount_max_som=500_000_000, requires_collateral=True,
                down_payment_pct=25.0, source_url=self.url,
                scraped_at=datetime.now(timezone.utc),
            )
        ]


class FailingScraper(BaseScraper):
    bank_name = "FailingBank"
    url = "https://failing.uz"

    def parse(self, html: str) -> list[Product]:
        return []

    def run(self) -> list[Product]:
        raise RuntimeError("sayt javob bermadi")


def test_run_all_scrapers_persists_products_and_logs_success(db_session):
    with patch("scrapers.orchestrator.ALL_SCRAPERS", [WorkingScraper]):
        run_all_scrapers(db_session)

    products = db_session.query(ProductRow).all()
    assert len(products) == 1
    assert products[0].bank == "WorkingBank"

    runs = db_session.query(ScrapeRunRow).all()
    assert len(runs) == 1
    assert runs[0].status == "success"
    assert runs[0].products_found == 1


def test_run_all_scrapers_logs_failure_without_crashing(db_session):
    with patch("scrapers.orchestrator.ALL_SCRAPERS", [FailingScraper]):
        run_all_scrapers(db_session)

    assert db_session.query(ProductRow).count() == 0
    run = db_session.query(ScrapeRunRow).one()
    assert run.status == "failed"
    assert "sayt javob bermadi" in run.error_message


def test_run_all_scrapers_continues_after_one_bank_fails(db_session):
    with patch("scrapers.orchestrator.ALL_SCRAPERS", [FailingScraper, WorkingScraper]):
        run_all_scrapers(db_session)

    assert db_session.query(ProductRow).count() == 1
    statuses = {r.bank: r.status for r in db_session.query(ScrapeRunRow).all()}
    assert statuses == {"FailingBank": "failed", "WorkingBank": "success"}
