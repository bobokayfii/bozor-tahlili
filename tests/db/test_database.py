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
