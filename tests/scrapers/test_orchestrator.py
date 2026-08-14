import time
from datetime import datetime, timezone
from unittest.mock import patch

from db.models import ProductRow, ScrapeRunRow
from scrapers.base import BaseScraper, Product
from scrapers import orchestrator
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


class HangingScraper(BaseScraper):
    """run() never returns within the test's patched timeout — simulates the
    2026-08-14 live-Railway incident where one bank's scraper hung
    indefinitely (network stall or pathological regex backtracking) and,
    because run_all_scrapers awaited each scraper.run() sequentially with no
    bound, blocked every subsequent bank in ALL_SCRAPERS forever."""

    bank_name = "HangingBank"
    url = "https://hanging.uz"

    def parse(self, html: str) -> list[Product]:
        return []

    def run(self) -> list[Product]:
        time.sleep(10)
        return []


class BadPersistenceScraper(BaseScraper):
    """run() succeeds but returns a Product whose `category` is None,
    which violates the non-nullable `category` column on ProductRow and
    raises an IntegrityError during flush/commit (persistence phase, not
    inside run())."""

    bank_name = "BadPersistenceBank"
    url = "https://badpersistence.uz"

    def parse(self, html: str) -> list[Product]:
        return []

    def run(self) -> list[Product]:
        return [
            Product(
                bank="BadPersistenceBank", category=None, product_name="broken",
                rate_min=10.0, rate_max=15.0, term_min_months=6, term_max_months=24,
                amount_max_som=100_000_000, requires_collateral=False,
                down_payment_pct=None, source_url=self.url,
                scraped_at=datetime.now(timezone.utc),
            )
        ]


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


def test_run_all_scrapers_times_out_a_hanging_bank_without_blocking_others(db_session):
    """A scraper that never returns must not stall the whole batch — this is
    the exact failure mode observed live on 2026-08-14 (see HangingScraper
    docstring). WorkingBank must still be scraped and persisted even though
    HangingBank comes first in ALL_SCRAPERS and never completes."""
    with (
        patch("scrapers.orchestrator.ALL_SCRAPERS", [HangingScraper, WorkingScraper]),
        patch.object(orchestrator, "SCRAPER_TIMEOUT_SECONDS", 0.1),
    ):
        run_all_scrapers(db_session)

    products = db_session.query(ProductRow).all()
    assert len(products) == 1
    assert products[0].bank == "WorkingBank"

    runs = {r.bank: r for r in db_session.query(ScrapeRunRow).all()}
    assert runs["HangingBank"].status == "failed"
    assert "timeout" in runs["HangingBank"].error_message.lower()
    assert runs["WorkingBank"].status == "success"


def test_run_all_scrapers_isolates_persistence_failure_from_other_banks(db_session):
    """A scraper whose run() succeeds but whose returned Product fails during
    persistence (commit-time IntegrityError) must not crash run_all_scrapers
    or prevent subsequent banks from being processed. This exercises the
    error-isolation guarantee for the persistence phase, not just run()."""
    with patch(
        "scrapers.orchestrator.ALL_SCRAPERS", [BadPersistenceScraper, WorkingScraper]
    ):
        run_all_scrapers(db_session)

    products = db_session.query(ProductRow).all()
    assert len(products) == 1
    assert products[0].bank == "WorkingBank"

    runs = {r.bank: r for r in db_session.query(ScrapeRunRow).all()}
    assert runs["BadPersistenceBank"].status == "failed"
    assert runs["BadPersistenceBank"].error_message is not None
    assert runs["BadPersistenceBank"].finished_at is not None
    assert runs["WorkingBank"].status == "success"


def test_run_all_scrapers_persists_new_optional_fields(db_session):
    class ScraperWithExtras(BaseScraper):
        bank_name = "ExtrasBank"
        url = "https://extras.uz"

        def parse(self, html: str) -> list[Product]:
            return []

        def run(self) -> list[Product]:
            return [
                Product(
                    bank="ExtrasBank", category="ipoteka_tijorat", product_name="test",
                    rate_min=20.0, rate_max=25.0, term_min_months=12, term_max_months=240,
                    amount_max_som=1_700_000_000, requires_collateral=True,
                    down_payment_pct=25.0, source_url="https://extras.uz",
                    scraped_at=datetime.now(timezone.utc),
                    grace_period_months=6,
                    payment_method="annuitet_yoki_differensial",
                    special_terms="Sotib olinayotgan uy-joy garov sifatida olinadi.",
                )
            ]

    with patch("scrapers.orchestrator.ALL_SCRAPERS", [ScraperWithExtras]):
        run_all_scrapers(db_session)

    product = db_session.query(ProductRow).one()
    assert product.grace_period_months == 6
    assert product.payment_method == "annuitet_yoki_differensial"
    assert "garov" in product.special_terms
