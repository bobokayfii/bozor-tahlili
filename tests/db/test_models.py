from datetime import datetime, timezone

from db.models import ProductRow, ScrapeRunRow


def test_product_row_roundtrip(db_session):
    row = ProductRow(
        bank="SQB",
        category="avtokredit",
        product_name="SQB Avtokredit",
        rate_min=24.9,
        rate_max=27.9,
        term_min_months=12,
        term_max_months=60,
        amount_max_som=800_000_000,
        requires_collateral=True,
        down_payment_pct=30.0,
        source_url="https://sqb.uz/kredit/avto",
        scraped_at=datetime.now(timezone.utc),
    )
    db_session.add(row)
    db_session.commit()

    fetched = db_session.query(ProductRow).filter_by(bank="SQB").one()
    assert fetched.category == "avtokredit"
    assert fetched.rate_min == 24.9
    assert fetched.requires_collateral is True


def test_scrape_run_row_roundtrip(db_session):
    run = ScrapeRunRow(
        bank="SQB",
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    db_session.add(run)
    db_session.commit()

    fetched = db_session.query(ScrapeRunRow).filter_by(bank="SQB").one()
    assert fetched.status == "running"
    assert fetched.products_found == 0
