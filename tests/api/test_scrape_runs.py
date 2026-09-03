from datetime import datetime, timedelta, timezone

from auth.security import create_access_token
from db.models import ScrapeRunRow, UserRow
from scrapers.registry import ALL_SCRAPERS

import api.main as api_main


def test_list_scrape_runs_requires_admin(client):
    with api_main.SessionLocal() as session:
        regular = UserRow(username="regular", password_hash="unused", role="user", created_at=datetime.now(timezone.utc))
        session.add(regular)
        session.commit()
        session.refresh(regular)
        regular_id = regular.id
    non_admin_token = create_access_token(user_id=regular_id, username="regular", role="user")

    response = client.get("/admin/scrape-runs", headers={"Authorization": f"Bearer {non_admin_token}"})
    assert response.status_code == 403


def test_list_scrape_runs_defaults_to_never_run_with_no_history(client):
    response = client.get("/admin/scrape-runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(ALL_SCRAPERS)
    assert all(row["status"] == "never_run" for row in data)
    assert all(row["started_at"] is None for row in data)
    bank_names = {scraper_cls.bank_name for scraper_cls in ALL_SCRAPERS}
    assert {row["bank"] for row in data} == bank_names


def test_list_scrape_runs_shows_only_the_latest_run_per_bank(client):
    bank = ALL_SCRAPERS[0].bank_name
    with api_main.SessionLocal() as session:
        session.add(ScrapeRunRow(
            bank=bank,
            started_at=datetime.now(timezone.utc) - timedelta(days=1),
            finished_at=datetime.now(timezone.utc) - timedelta(days=1),
            status="failed",
            error_message="old failure",
            products_found=0,
        ))
        session.add(ScrapeRunRow(
            bank=bank,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            status="success",
            error_message=None,
            products_found=7,
        ))
        session.commit()

    response = client.get("/admin/scrape-runs")
    data = response.json()
    row = next(r for r in data if r["bank"] == bank)
    assert row["status"] == "success"
    assert row["products_found"] == 7
    assert row["error_message"] is None


def test_list_scrape_runs_sorts_failed_and_running_before_success_and_never_run(client):
    failed_bank = ALL_SCRAPERS[0].bank_name
    success_bank = ALL_SCRAPERS[1].bank_name
    with api_main.SessionLocal() as session:
        session.add(ScrapeRunRow(
            bank=success_bank,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            status="success",
            products_found=3,
        ))
        session.add(ScrapeRunRow(
            bank=failed_bank,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            status="failed",
            error_message="timed out",
            products_found=0,
        ))
        session.commit()

    response = client.get("/admin/scrape-runs")
    data = response.json()
    statuses_in_order = [row["status"] for row in data]
    assert statuses_in_order.index("failed") < statuses_in_order.index("success")
    assert statuses_in_order.index("failed") < statuses_in_order.index("never_run")
