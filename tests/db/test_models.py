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


def test_product_row_new_fields_default_to_none(db_session):
    row = ProductRow(
        bank="SQB",
        category="ipoteka_tijorat",
        product_name="SQB Ipoteka",
        rate_min=23.9,
        rate_max=24.9,
        term_min_months=12,
        term_max_months=240,
        amount_max_som=1_700_000_000,
        requires_collateral=True,
        down_payment_pct=25.0,
        source_url="https://sqb.uz/ipoteka",
        scraped_at=datetime.now(timezone.utc),
    )
    db_session.add(row)
    db_session.commit()

    fetched = db_session.query(ProductRow).filter_by(bank="SQB", category="ipoteka_tijorat").one()
    assert fetched.grace_period_months is None
    assert fetched.payment_method is None
    assert fetched.special_terms is None


def test_product_row_new_fields_roundtrip_when_set(db_session):
    row = ProductRow(
        bank="NBU",
        category="ipoteka_tijorat",
        product_name="NBU Ipoteka",
        rate_min=20.0,
        rate_max=26.0,
        term_min_months=12,
        term_max_months=240,
        amount_max_som=1_500_000_000,
        requires_collateral=True,
        down_payment_pct=25.0,
        source_url="https://nbu.uz/ipoteka",
        scraped_at=datetime.now(timezone.utc),
        grace_period_months=12,
        payment_method="annuitet_yoki_differensial",
        special_terms="Sotib olinayotgan uy-joy va sug'urta polisi",
    )
    db_session.add(row)
    db_session.commit()

    fetched = db_session.query(ProductRow).filter_by(bank="NBU").one()
    assert fetched.grace_period_months == 12
    assert fetched.payment_method == "annuitet_yoki_differensial"
    assert "sug'urta" in fetched.special_terms
