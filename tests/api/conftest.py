from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from auth.security import create_access_token, hash_password
from db.database import get_engine, get_session_factory, init_db
from db.models import ProductRow, UserRow


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = get_engine(tmp_path / "api_test.db")
    init_db(engine)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        session.add(ProductRow(
            bank="SQB", category="mikroqarz", product_name="SQB Mikroqarz",
            rate_min=28.0, rate_max=31.0, term_min_months=3, term_max_months=36,
            amount_max_som=100_000_000, requires_collateral=False,
            down_payment_pct=None, source_url="https://sqb.uz",
            scraped_at=datetime.now(timezone.utc),
        ))
        session.add(UserRow(
            id=1,
            username="test-admin",
            password_hash=hash_password("test-password"),
            role="admin",
            created_at=datetime.now(timezone.utc),
        ))
        session.commit()

    monkeypatch.setattr(api_main, "SessionLocal", session_factory)
    test_client = TestClient(api_main.app)
    token = create_access_token(user_id=1, username="test-admin", role="admin")
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    return test_client
