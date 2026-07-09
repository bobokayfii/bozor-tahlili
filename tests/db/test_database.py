from db.database import get_engine, get_session_factory, init_db
from db.models import ProductRow


def test_init_db_creates_tables_and_session_works(tmp_path):
    engine = get_engine(tmp_path / "test.db")
    init_db(engine)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        session.add(ProductRow(
            bank="NBU", category="mikroqarz", product_name="test",
            rate_min=25.0, rate_max=30.0, term_min_months=6, term_max_months=36,
            amount_max_som=100_000_000, requires_collateral=False,
            down_payment_pct=None, source_url="https://nbu.uz",
            scraped_at=__import__("datetime").datetime.now(),
        ))
        session.commit()
        assert session.query(ProductRow).count() == 1


def test_init_db_adds_new_columns_to_existing_products_table(tmp_path):
    from sqlalchemy import inspect, text

    db_path = tmp_path / "legacy.db"
    engine = get_engine(db_path)
    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank VARCHAR(100),
                category VARCHAR(50),
                product_name VARCHAR(200),
                rate_min FLOAT,
                rate_max FLOAT,
                term_min_months INTEGER,
                term_max_months INTEGER,
                amount_max_som INTEGER,
                requires_collateral BOOLEAN,
                down_payment_pct FLOAT,
                source_url VARCHAR(500),
                scraped_at DATETIME
            )
            """
        ))
    engine.dispose()

    engine_v2 = get_engine(db_path)
    init_db(engine_v2)

    inspector = inspect(engine_v2)
    columns = {col["name"] for col in inspector.get_columns("products")}
    assert "grace_period_months" in columns
    assert "payment_method" in columns
    assert "special_terms" in columns


def test_init_db_migration_is_idempotent(tmp_path):
    db_path = tmp_path / "twice.db"
    engine = get_engine(db_path)
    init_db(engine)
    init_db(engine)  # must not raise "duplicate column" on second call
