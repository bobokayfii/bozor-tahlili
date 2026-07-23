from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from db.database import get_engine, get_session_factory, init_db
from db.models import ProductRow


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
        session.commit()

    monkeypatch.setattr(api_main, "SessionLocal", session_factory)
    return TestClient(api_main.app)


def test_list_products_returns_seeded_row(client):
    response = client.get("/products", params={"category": "mikroqarz"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["bank"] == "SQB"


def test_list_products_returns_only_latest_scrape_per_bank_category(client):
    with api_main.SessionLocal() as session:
        session.add(ProductRow(
            bank="HamkorBank", category="avtokredit", product_name="Hamkor Avtokredit (old)",
            rate_min=10.0, rate_max=15.0, term_min_months=12, term_max_months=36,
            amount_max_som=100_000_000, requires_collateral=False,
            down_payment_pct=None, source_url="https://hamkor.uz",
            scraped_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ))
        session.add(ProductRow(
            bank="HamkorBank", category="avtokredit", product_name="Hamkor Avtokredit (new)",
            rate_min=20.0, rate_max=25.0, term_min_months=12, term_max_months=36,
            amount_max_som=100_000_000, requires_collateral=False,
            down_payment_pct=None, source_url="https://hamkor.uz",
            scraped_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        ))
        session.commit()

    response = client.get("/products", params={"category": "avtokredit"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["rate_min"] == 20.0
    assert data[0]["product_name"] == "Hamkor Avtokredit (new)"


def test_recommend_uses_only_latest_scrape_per_bank_category(client):
    with api_main.SessionLocal() as session:
        session.add(ProductRow(
            bank="HamkorBank", category="avtokredit", product_name="Hamkor Avtokredit (old)",
            rate_min=10.0, rate_max=15.0, term_min_months=12, term_max_months=36,
            amount_max_som=100_000_000, requires_collateral=False,
            down_payment_pct=None, source_url="https://hamkor.uz",
            scraped_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ))
        session.add(ProductRow(
            bank="HamkorBank", category="avtokredit", product_name="Hamkor Avtokredit (new)",
            rate_min=20.0, rate_max=25.0, term_min_months=12, term_max_months=36,
            amount_max_som=100_000_000, requires_collateral=False,
            down_payment_pct=None, source_url="https://hamkor.uz",
            scraped_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        ))
        session.commit()

    response = client.post("/recommend", json={
        "category": "avtokredit",
        "amount_som": 50_000_000,
        "term_months": 12,
        "collateral_ok": True,
    })
    assert response.status_code == 200
    data = response.json()
    hamkor_matches = [r for r in data["recommendations"] if r["bank"] == "HamkorBank"]
    assert len(hamkor_matches) == 1
    assert hamkor_matches[0]["product_name"] == "Hamkor Avtokredit (new)"


def test_recommend_returns_ranked_list_and_explanation(client, monkeypatch):
    monkeypatch.setattr(
        api_main, "explain_recommendation", lambda criteria, ranked: "test tushuntirish"
    )
    response = client.post("/recommend", json={
        "category": "mikroqarz",
        "amount_som": 50_000_000,
        "term_months": 12,
        "collateral_ok": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["explanation"] == "test tushuntirish"
    assert data["recommendations"][0]["bank"] == "SQB"


def test_list_categories_returns_eleven_entries(client):
    response = client.get("/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 11
    keys = {c["key"] for c in data}
    assert "avtokredit" in keys
    assert "ipoteka_davlat" in keys
    assert data[0]["schema"] == "credit_down_payment"


def test_products_response_includes_new_optional_fields(client):
    response = client.get("/products", params={"category": "mikroqarz"})
    assert response.status_code == 200
    data = response.json()
    assert data[0]["down_payment_pct"] is None
    assert data[0]["grace_period_months"] is None
    assert data[0]["payment_method"] is None
    assert data[0]["special_terms"] is None


def test_list_unavailable_banks_returns_tbc_for_avtokredit(client):
    response = client.get("/unavailable-banks", params={"category": "avtokredit"})
    assert response.status_code == 200
    data = response.json()
    assert data == [{"bank": "TBC Bank", "reason": "Mahsulot mavjud emas"}]


def test_list_unavailable_banks_returns_sqb_for_avtokredit_ikkilamchi(client):
    response = client.get("/unavailable-banks", params={"category": "avtokredit_ikkilamchi"})
    assert response.status_code == 200
    data = response.json()
    assert data == [{"bank": "SQB", "reason": "Vaqtincha to'xtatilgan"}]


def test_list_unavailable_banks_returns_kapitalbank_for_avtokredit_brend_birlamchi(client):
    response = client.get("/unavailable-banks", params={"category": "avtokredit_brend_birlamchi"})
    assert response.status_code == 200
    data = response.json()
    assert data == [
        {"bank": "Kapitalbank", "reason": "Vaqtincha to'xtatilgan"},
        {"bank": "SQB", "reason": "Vaqtincha to'xtatilgan"},
    ]


def test_list_unavailable_banks_returns_empty_for_unlisted_category(client):
    response = client.get("/unavailable-banks", params={"category": "mikroqarz"})
    assert response.status_code == 200
    assert response.json() == []


def test_cors_allows_configured_frontend_origin(client):
    response = client.get(
        "/products",
        params={"category": "mikroqarz"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
