# Mahsulot taksonomiyasi kengaytirish va React frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the product category taxonomy from 4 to 11 credit-type categories, add the missing comparison fields (grace period, payment method, special terms) to the data model, and replace the Streamlit dashboard with a React/Vite/TypeScript frontend styled per the approved visual design.

**Architecture:** Backend stays a Python monolith (FastAPI + SQLAlchemy + SQLite), gains a new `categories.py` registry module as the single source of truth for category metadata, exposed to the frontend via a new `GET /categories` endpoint. The frontend is a separate `frontend/` Vite project that talks to the existing FastAPI backend over `fetch`, replacing `dashboard/` entirely.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, SQLite, pytest; React 18 + TypeScript + Vite, Vitest + React Testing Library, Playwright.

## Global Constraints

- Existing category keys (`avtokredit`, `mikroqarz`, `kredit_karta`, `istemol_krediti`) must not change — breaking them breaks currently-scraped data.
- New `ProductRow` fields must be nullable/optional — existing rows in `data/bank_products.db` have no values for them and must not break.
- Visual design tokens (exact, from the approved mockup): navy `#0e2c56` primary, accent `#d9455f` used only for the active sidebar indicator and the recommend CTA (never as a fill/background), heading font Fraunces (500/600), body/data font Inter (400–700), rate figures use `font-variant-numeric: tabular-nums`.
- Backend test coverage target: 80%+ for `db/`, `recommender/`, `scrapers/orchestrator.py`, `api/` (per `README.md`).
- Out of scope for this plan (per spec section 2): omonat/plastik-karta/xalqaro-o'tkazma categories, banks beyond the current 5, real scrapers for the 7 new empty categories, redesigning the recommend/AI flow.

---

### Task 1: Category registry module

**Files:**
- Create: `categories.py`
- Test: `tests/test_categories.py`

**Interfaces:**
- Produces: `Category` (frozen dataclass: `key: str`, `label_uz: str`, `schema: str = "credit"`), `CATEGORIES: list[Category]`, `category_keys() -> list[str]`. Task 4 (API) and Task 6 (frontend types, indirectly via the `/categories` endpoint) depend on this shape.

- [ ] **Step 1: Write the failing test**

Create `tests/test_categories.py`:

```python
from categories import CATEGORIES, category_keys


def test_categories_contains_eleven_entries():
    assert len(CATEGORIES) == 11


def test_all_category_keys_are_unique():
    keys = category_keys()
    assert len(keys) == len(set(keys))


def test_existing_categories_keep_original_keys():
    keys = category_keys()
    for legacy_key in ["avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"]:
        assert legacy_key in keys


def test_all_categories_use_credit_schema():
    assert all(c.schema == "credit" for c in CATEGORIES)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_categories.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'categories'`

- [ ] **Step 3: Write the implementation**

Create `categories.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    key: str
    label_uz: str
    schema: str = "credit"


CATEGORIES: list[Category] = [
    Category(key="avtokredit", label_uz="Avtokredit (birlamchi bozor)"),
    Category(key="avtokredit_ikkilamchi", label_uz="Avtokredit (ikkilamchi bozor)"),
    Category(
        key="avtokredit_brend_birlamchi",
        label_uz="Brendli avtokredit — birlamchi (GM, BYD, KIA, Hyundai, Renault, LADA, Volkswagen, Skoda, Chery)",
    ),
    Category(
        key="avtokredit_brend_ikkilamchi",
        label_uz="Brendli avtokredit — ikkilamchi (GM, BYD, KIA, Hyundai, Renault, LADA, Volkswagen, Skoda, Chery)",
    ),
    Category(key="avtokredit_elektro", label_uz="Elektromobil avtokrediti"),
    Category(key="mikroqarz", label_uz="Mikroqarz (oflayn)"),
    Category(key="mikroqarz_onlayn", label_uz="Mikroqarz (onlayn)"),
    Category(key="kredit_karta", label_uz="Kredit kartalari"),
    Category(key="istemol_krediti", label_uz="Iste'mol krediti"),
    Category(key="ipoteka_tijorat", label_uz="Ipoteka krediti (tijorat)"),
    Category(
        key="ipoteka_davlat",
        label_uz="Ipoteka krediti (Iqtisodiyot va moliya vazirligi mablag'lari hisobidan)",
    ),
]


def category_keys() -> list[str]:
    return [c.key for c in CATEGORIES]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_categories.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add categories.py tests/test_categories.py
git commit -m "feat: add centralized category taxonomy registry"
```

---

### Task 2: New `ProductRow`/`Product` fields + DB migration

**Files:**
- Modify: `db/models.py`
- Modify: `db/database.py`
- Modify: `scrapers/base.py`
- Test: `tests/db/test_models.py`
- Test: `tests/db/test_database.py`

**Interfaces:**
- Consumes: none new.
- Produces: `ProductRow.grace_period_months: int | None`, `ProductRow.payment_method: str | None`, `ProductRow.special_terms: str | None`; `Product.grace_period_months: int | None = None`, `Product.payment_method: str | None = None`, `Product.special_terms: str | None = None`. Task 3 (orchestrator) and Task 4 (API `_row_to_dict`) depend on these exact names.

- [ ] **Step 1: Write the failing tests**

Add to `tests/db/test_models.py` (append at end of file):

```python
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
```

Add to `tests/db/test_database.py` (append at end of file):

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/db/test_models.py tests/db/test_database.py -v`
Expected: the 3 new tests FAIL (`AttributeError` for the model tests, `AssertionError` for the migration test since the columns don't exist yet)

- [ ] **Step 3: Add the new columns to `ProductRow`**

In `db/models.py`, add imports and fields. Current end of `ProductRow` (`db/models.py:24-26`):

```python
    down_payment_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str] = mapped_column(String(500))
    scraped_at: Mapped[datetime] = mapped_column(DateTime)
```

Replace with:

```python
    down_payment_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str] = mapped_column(String(500))
    scraped_at: Mapped[datetime] = mapped_column(DateTime)
    grace_period_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    special_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
```

(`Integer`, `String`, `Text` are already imported at the top of `db/models.py`; no import changes needed.)

- [ ] **Step 4: Add the same fields to the `Product` dataclass**

In `scrapers/base.py`, current `Product` dataclass (`scrapers/base.py:18-31`):

```python
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
```

Replace with:

```python
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
    grace_period_months: int | None = None
    payment_method: str | None = None
    special_terms: str | None = None
```

(Defaults mean every existing `Product(...)` construction site — only `_build_product` in this same file — keeps working unchanged.)

- [ ] **Step 5: Add the migration helper to `db/database.py`**

Replace the full contents of `db/database.py` with:

```python
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from db.models import Base

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "bank_products.db"

_NEW_PRODUCT_COLUMNS = {
    "grace_period_months": "INTEGER",
    "payment_method": "VARCHAR(50)",
    "special_terms": "TEXT",
}


def get_engine(db_path: Path | None = None):
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")


def _ensure_product_columns(engine) -> None:
    """SQLAlchemy's create_all() only creates missing tables, not missing
    columns on tables that already exist. Since data/bank_products.db is a
    real append-only local file (not managed by a migration tool), new
    nullable ProductRow columns are added here via ALTER TABLE so existing
    databases pick them up without losing scraped history."""
    inspector = inspect(engine)
    if "products" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("products")}
    missing = {name: sql_type for name, sql_type in _NEW_PRODUCT_COLUMNS.items() if name not in existing}
    if not missing:
        return
    with engine.begin() as conn:
        for name, sql_type in missing.items():
            conn.execute(text(f"ALTER TABLE products ADD COLUMN {name} {sql_type}"))


def init_db(engine) -> None:
    Base.metadata.create_all(engine)
    _ensure_product_columns(engine)


def get_session_factory(engine):
    return sessionmaker(bind=engine)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/db/test_models.py tests/db/test_database.py -v`
Expected: all passed

- [ ] **Step 7: Run the full test suite to check for regressions**

Run: `.venv/Scripts/python.exe -m pytest --cov=. --cov-report=term-missing`
Expected: all existing tests still pass (new columns are nullable, so no existing fixture breaks)

- [ ] **Step 8: Commit**

```bash
git add db/models.py db/database.py scrapers/base.py tests/db/test_models.py tests/db/test_database.py
git commit -m "feat: add grace period, payment method, special terms fields with migration"
```

---

### Task 3: Orchestrator persists the new fields

**Files:**
- Modify: `scrapers/orchestrator.py`
- Test: `tests/scrapers/test_orchestrator.py`

**Interfaces:**
- Consumes: `Product.grace_period_months`, `Product.payment_method`, `Product.special_terms` (Task 2).
- Produces: no new public interface — `run_all_scrapers` behavior is extended, signature unchanged.

- [ ] **Step 1: Write the failing test**

Append to `tests/scrapers/test_orchestrator.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/scrapers/test_orchestrator.py::test_run_all_scrapers_persists_new_optional_fields -v`
Expected: FAIL — `product.grace_period_months` is `None` instead of `6` (orchestrator doesn't copy the field yet)

- [ ] **Step 3: Update the ProductRow construction**

In `scrapers/orchestrator.py`, current block (`scrapers/orchestrator.py:24-39`):

```python
            for product in products:
                session.add(
                    ProductRow(
                        bank=product.bank,
                        category=product.category,
                        product_name=product.product_name,
                        rate_min=product.rate_min,
                        rate_max=product.rate_max,
                        term_min_months=product.term_min_months,
                        term_max_months=product.term_max_months,
                        amount_max_som=product.amount_max_som,
                        requires_collateral=product.requires_collateral,
                        down_payment_pct=product.down_payment_pct,
                        source_url=product.source_url,
                        scraped_at=product.scraped_at,
                    )
                )
```

Replace with:

```python
            for product in products:
                session.add(
                    ProductRow(
                        bank=product.bank,
                        category=product.category,
                        product_name=product.product_name,
                        rate_min=product.rate_min,
                        rate_max=product.rate_max,
                        term_min_months=product.term_min_months,
                        term_max_months=product.term_max_months,
                        amount_max_som=product.amount_max_som,
                        requires_collateral=product.requires_collateral,
                        down_payment_pct=product.down_payment_pct,
                        source_url=product.source_url,
                        scraped_at=product.scraped_at,
                        grace_period_months=product.grace_period_months,
                        payment_method=product.payment_method,
                        special_terms=product.special_terms,
                    )
                )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/scrapers/test_orchestrator.py -v`
Expected: all passed (including the 4 pre-existing tests in this file)

- [ ] **Step 5: Commit**

```bash
git add scrapers/orchestrator.py tests/scrapers/test_orchestrator.py
git commit -m "feat: persist grace period, payment method, special terms during scraping"
```

---

### Task 4: API — CORS, `/categories` endpoint, new fields in `/products`

**Files:**
- Modify: `api/main.py`
- Test: `tests/api/test_main.py`

**Interfaces:**
- Consumes: `categories.CATEGORIES` (Task 1), `ProductRow.grace_period_months/payment_method/special_terms` (Task 2).
- Produces: `GET /categories` → `list[{"key": str, "label": str, "schema": str}]`. Task 6 (frontend `lib/api.ts`) depends on this exact shape and endpoint path.

- [ ] **Step 1: Write the failing tests**

Append to `tests/api/test_main.py`:

```python
def test_list_categories_returns_eleven_entries(client):
    response = client.get("/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 11
    keys = {c["key"] for c in data}
    assert "avtokredit" in keys
    assert "ipoteka_davlat" in keys
    assert data[0]["schema"] == "credit"


def test_products_response_includes_new_optional_fields(client):
    response = client.get("/products", params={"category": "mikroqarz"})
    assert response.status_code == 200
    data = response.json()
    assert data[0]["grace_period_months"] is None
    assert data[0]["payment_method"] is None
    assert data[0]["special_terms"] is None


def test_cors_allows_configured_frontend_origin(client):
    response = client.get(
        "/products",
        params={"category": "mikroqarz"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/api/test_main.py -v`
Expected: the 3 new tests FAIL (`/categories` is 404, new fields missing from response, no CORS header)

- [ ] **Step 3: Add CORS middleware, `/categories` endpoint, and new response fields**

In `api/main.py`, current imports and app setup (`api/main.py:1-16`):

```python
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import func, select

from db.database import get_engine, get_session_factory, init_db
from db.models import ProductRow
from recommender.explain import explain_recommendation
from recommender.scoring import Criteria, top_recommendations

app = FastAPI(title="Bank Mahsulot Tahlili API")

_engine = get_engine()
init_db(_engine)
SessionLocal = get_session_factory(_engine)
```

Replace with:

```python
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, select

from categories import CATEGORIES
from db.database import get_engine, get_session_factory, init_db
from db.models import ProductRow
from recommender.explain import explain_recommendation
from recommender.scoring import Criteria, top_recommendations

app = FastAPI(title="Bank Mahsulot Tahlili API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_engine = get_engine()
init_db(_engine)
SessionLocal = get_session_factory(_engine)
```

Current `_row_to_dict` (`api/main.py:26-38`):

```python
def _row_to_dict(row: ProductRow) -> dict:
    return {
        "bank": row.bank,
        "category": row.category,
        "product_name": row.product_name,
        "rate_min": row.rate_min,
        "rate_max": row.rate_max,
        "term_min_months": row.term_min_months,
        "term_max_months": row.term_max_months,
        "amount_max_som": row.amount_max_som,
        "requires_collateral": row.requires_collateral,
        "scraped_at": row.scraped_at.isoformat(),
    }
```

Replace with:

```python
def _row_to_dict(row: ProductRow) -> dict:
    return {
        "bank": row.bank,
        "category": row.category,
        "product_name": row.product_name,
        "rate_min": row.rate_min,
        "rate_max": row.rate_max,
        "term_min_months": row.term_min_months,
        "term_max_months": row.term_max_months,
        "amount_max_som": row.amount_max_som,
        "requires_collateral": row.requires_collateral,
        "grace_period_months": row.grace_period_months,
        "payment_method": row.payment_method,
        "special_terms": row.special_terms,
        "scraped_at": row.scraped_at.isoformat(),
    }
```

Add a new endpoint right after the `list_products` function (`api/main.py`, after the existing `/products` route):

```python
@app.get("/categories")
def list_categories():
    return [{"key": c.key, "label": c.label_uz, "schema": c.schema} for c in CATEGORIES]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/api/test_main.py -v`
Expected: all passed

- [ ] **Step 5: Run the full backend suite with coverage**

Run: `.venv/Scripts/python.exe -m pytest --cov=. --cov-report=term-missing`
Expected: all passed, `db/`, `recommender/`, `scrapers/orchestrator.py`, `api/` at 80%+

- [ ] **Step 6: Commit**

```bash
git add api/main.py tests/api/test_main.py
git commit -m "feat: add /categories endpoint, CORS, and new fields to /products response"
```

---

### Task 5: Scaffold the React/Vite/TypeScript frontend project

**Files:**
- Create: `frontend/` (via `npm create vite`)
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/vitest.setup.ts`
- Create: `frontend/playwright.config.ts`
- Modify: `frontend/index.html`

**Interfaces:**
- Produces: a runnable Vite dev server on port 5173, `npm test` (Vitest), `npm run test:e2e` (Playwright). Tasks 6–9 add source files inside this scaffold.

- [ ] **Step 1: Scaffold the project**

Run from the repo root:

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

- [ ] **Step 2: Add test tooling**

Run from `frontend/`:

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @playwright/test
npx playwright install chromium
```

- [ ] **Step 3: Configure Vitest**

Overwrite `frontend/vite.config.ts` with:

```ts
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './vitest.setup.ts',
  },
})
```

Create `frontend/vitest.setup.ts`:

```ts
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 4: Configure Playwright**

Create `frontend/playwright.config.ts`:

```ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
  },
  use: {
    baseURL: 'http://localhost:5173',
  },
})
```

- [ ] **Step 5: Add npm scripts**

Edit `frontend/package.json` — replace the `"scripts"` block (generated by `create vite`, currently `dev`/`build`/`lint`/`preview`) with:

```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "preview": "vite preview",
  "lint": "eslint .",
  "test": "vitest run",
  "test:e2e": "playwright test"
}
```

- [ ] **Step 6: Set the page title and fonts**

Overwrite `frontend/index.html` with:

```html
<!doctype html>
<html lang="uz">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link
      href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600&family=Inter:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    />
    <title>Bozor Tahlili</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Verify the dev server starts**

Run: `npm run dev` (from `frontend/`), then in another terminal: `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173`
Expected: `200`. Stop the dev server (Ctrl+C) after confirming.

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/vitest.setup.ts frontend/playwright.config.ts frontend/index.html frontend/tsconfig*.json frontend/src frontend/public frontend/.gitignore frontend/eslint.config.js
git commit -m "chore: scaffold React/Vite/TypeScript frontend with Vitest and Playwright"
```

---

### Task 6: API client and shared types

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/api.test.ts`

**Interfaces:**
- Consumes: backend `GET /categories`, `GET /products?category=`, `POST /recommend` (Task 4).
- Produces: `Category`, `Product`, `Recommendation`, `RecommendResponse` types; `fetchCategories()`, `fetchProducts(category: string)`, `fetchRecommendation(category, amountSom, termMonths, collateralOk)`. Tasks 7–9 (components) depend on these exact names and types.

- [ ] **Step 1: Create the shared types**

Create `frontend/src/lib/types.ts`:

```ts
export interface Category {
  key: string
  label: string
  schema: string
}

export interface Product {
  bank: string
  category: string
  product_name: string
  rate_min: number
  rate_max: number
  term_min_months: number
  term_max_months: number
  amount_max_som: number
  requires_collateral: boolean
  grace_period_months: number | null
  payment_method: string | null
  special_terms: string | null
  scraped_at: string
}

export interface Recommendation {
  bank: string
  product_name: string
  score: number
}

export interface RecommendResponse {
  recommendations: Recommendation[]
  explanation: string
}
```

- [ ] **Step 2: Write the failing tests for the API client**

Create `frontend/src/lib/api.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchCategories, fetchProducts, fetchRecommendation } from './api'

describe('api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetchCategories returns parsed JSON on success', async () => {
    const mockCategories = [{ key: 'avtokredit', label: 'Avtokredit', schema: 'credit' }]
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockCategories }),
    )

    const result = await fetchCategories()
    expect(result).toEqual(mockCategories)
  })

  it('fetchProducts throws with the status code when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))

    await expect(fetchProducts('avtokredit')).rejects.toThrow("Mahsulotlarni yuklab bo'lmadi: 500")
  })

  it('fetchProducts requests the given category as a query param', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] })
    vi.stubGlobal('fetch', fetchMock)

    await fetchProducts('mikroqarz')

    const calledUrl = fetchMock.mock.calls[0][0] as URL
    expect(calledUrl.toString()).toBe('http://localhost:8000/products?category=mikroqarz')
  })

  it('fetchRecommendation posts criteria as a JSON body', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ recommendations: [], explanation: 'test' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchRecommendation('avtokredit', 50_000_000, 12, true)

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/recommend')
    expect(JSON.parse(options.body)).toEqual({
      category: 'avtokredit',
      amount_som: 50_000_000,
      term_months: 12,
      collateral_ok: true,
    })
  })
})
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `npm test` (from `frontend/`)
Expected: FAIL — `Failed to resolve import "./api"`

- [ ] **Step 4: Implement the API client**

Create `frontend/src/lib/api.ts`:

```ts
import type { Category, Product, RecommendResponse } from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchCategories(): Promise<Category[]> {
  const response = await fetch(`${API_BASE_URL}/categories`)
  if (!response.ok) {
    throw new Error(`Kategoriyalarni yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchProducts(category: string): Promise<Product[]> {
  const url = new URL(`${API_BASE_URL}/products`)
  url.searchParams.set('category', category)
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Mahsulotlarni yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchRecommendation(
  category: string,
  amountSom: number,
  termMonths: number,
  collateralOk: boolean,
): Promise<RecommendResponse> {
  const response = await fetch(`${API_BASE_URL}/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      category,
      amount_som: amountSom,
      term_months: termMonths,
      collateral_ok: collateralOk,
    }),
  })
  if (!response.ok) {
    throw new Error(`Tavsiya olinmadi: ${response.status}`)
  }
  return response.json()
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npm test` (from `frontend/`)
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib
git commit -m "feat: add frontend API client and shared types"
```

---

### Task 7: Sidebar component

**Files:**
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/components/Sidebar.test.tsx`

**Interfaces:**
- Consumes: `Category` (Task 6).
- Produces: `Sidebar({ categories, activeCategory, onSelect })` React component. Task 9 (`App.tsx`) depends on this exact prop shape.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/Sidebar.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { Sidebar } from './Sidebar'

const categories = [
  { key: 'avtokredit', label: 'Avtokredit', schema: 'credit' },
  { key: 'mikroqarz', label: 'Mikroqarz', schema: 'credit' },
]

describe('Sidebar', () => {
  it('renders a button for each category', () => {
    render(<Sidebar categories={categories} activeCategory="avtokredit" onSelect={() => {}} />)

    expect(screen.getByRole('button', { name: 'Avtokredit' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mikroqarz' })).toBeInTheDocument()
  })

  it('marks the active category button', () => {
    render(<Sidebar categories={categories} activeCategory="mikroqarz" onSelect={() => {}} />)

    expect(screen.getByRole('button', { name: 'Mikroqarz' })).toHaveClass('active')
    expect(screen.getByRole('button', { name: 'Avtokredit' })).not.toHaveClass('active')
  })

  it('calls onSelect with the clicked category key', async () => {
    const onSelect = vi.fn()
    render(<Sidebar categories={categories} activeCategory="avtokredit" onSelect={onSelect} />)

    await userEvent.click(screen.getByRole('button', { name: 'Mikroqarz' }))

    expect(onSelect).toHaveBeenCalledWith('mikroqarz')
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test` (from `frontend/`)
Expected: FAIL — `Failed to resolve import "./Sidebar"`

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/Sidebar.tsx`:

```tsx
import type { Category } from '../lib/types'

interface SidebarProps {
  categories: Category[]
  activeCategory: string | null
  onSelect: (categoryKey: string) => void
}

export function Sidebar({ categories, activeCategory, onSelect }: SidebarProps) {
  return (
    <nav className="sidebar" aria-label="Mahsulot kategoriyalari">
      <div className="sidebar-brand">Bozor Tahlili</div>
      <ul>
        {categories.map((category) => (
          <li key={category.key}>
            <button
              type="button"
              className={category.key === activeCategory ? 'sidebar-item active' : 'sidebar-item'}
              onClick={() => onSelect(category.key)}
            >
              {category.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test` (from `frontend/`)
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Sidebar.tsx frontend/src/components/Sidebar.test.tsx
git commit -m "feat: add category Sidebar component"
```

---

### Task 8: ProductTable component

**Files:**
- Create: `frontend/src/components/ProductTable.tsx`
- Create: `frontend/src/components/ProductTable.test.tsx`

**Interfaces:**
- Consumes: `Product` (Task 6).
- Produces: `ProductTable({ products })` React component. Task 9 (`App.tsx`) depends on this exact prop shape.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/ProductTable.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ProductTable } from './ProductTable'
import type { Product } from '../lib/types'

const sampleProduct: Product = {
  bank: 'SQB',
  category: 'avtokredit',
  product_name: 'SQB Avtokredit',
  rate_min: 24.9,
  rate_max: 27.9,
  term_min_months: 12,
  term_max_months: 60,
  amount_max_som: 800_000_000,
  requires_collateral: true,
  grace_period_months: null,
  payment_method: null,
  special_terms: null,
  scraped_at: '2026-07-08T10:00:00Z',
}

describe('ProductTable', () => {
  it('shows the empty-state message when there are no products', () => {
    render(<ProductTable products={[]} />)
    expect(screen.getByText("Bu kategoriya uchun hozircha ma'lumot yo'q.")).toBeInTheDocument()
  })

  it('renders one row per product with bank and rate range', () => {
    render(<ProductTable products={[sampleProduct]} />)
    expect(screen.getByText('SQB')).toBeInTheDocument()
    expect(screen.getByText('24.9% – 27.9%')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test` (from `frontend/`)
Expected: FAIL — `Failed to resolve import "./ProductTable"`

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ProductTable.tsx`:

```tsx
import type { Product } from '../lib/types'

interface ProductTableProps {
  products: Product[]
}

export function ProductTable({ products }: ProductTableProps) {
  if (products.length === 0) {
    return <p className="empty-state">Bu kategoriya uchun hozircha ma'lumot yo'q.</p>
  }

  return (
    <table className="product-table">
      <thead>
        <tr>
          <th>Bank</th>
          <th>Mahsulot</th>
          <th>Stavka</th>
          <th>Muddat</th>
        </tr>
      </thead>
      <tbody>
        {products.map((product, index) => (
          <tr key={`${product.bank}-${product.product_name}-${index}`}>
            <td>{product.bank}</td>
            <td>{product.product_name}</td>
            <td>
              {product.rate_min}% – {product.rate_max}%
            </td>
            <td>
              {product.term_min_months}–{product.term_max_months} oy
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test` (from `frontend/`)
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ProductTable.tsx frontend/src/components/ProductTable.test.tsx
git commit -m "feat: add ProductTable comparison component"
```

---

### Task 9: App shell, RecommendPanel, design tokens, and Playwright smoke test

**Files:**
- Create: `frontend/src/components/RecommendPanel.tsx`
- Create: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`
- Delete: `frontend/src/App.css` (scaffold default, superseded by `tokens.css`)
- Create: `frontend/e2e/dashboard.spec.ts`

**Interfaces:**
- Consumes: `Sidebar` (Task 7), `ProductTable` (Task 8), `fetchCategories`/`fetchProducts`/`fetchRecommendation` (Task 6).
- Produces: the assembled app. Nothing downstream depends on this task.

- [ ] **Step 1: Implement the RecommendPanel component**

Create `frontend/src/components/RecommendPanel.tsx`:

```tsx
import { useState, type FormEvent } from 'react'
import { fetchRecommendation } from '../lib/api'
import type { RecommendResponse } from '../lib/types'

interface RecommendPanelProps {
  category: string
}

export function RecommendPanel({ category }: RecommendPanelProps) {
  const [amountSom, setAmountSom] = useState(50_000_000)
  const [termMonths, setTermMonths] = useState(12)
  const [collateralOk, setCollateralOk] = useState(false)
  const [result, setResult] = useState<RecommendResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      const response = await fetchRecommendation(category, amountSom, termMonths, collateralOk)
      setResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Xatolik yuz berdi')
    }
  }

  return (
    <section className="recommend-panel">
      <h3>Tavsiya olish</h3>
      <form onSubmit={handleSubmit}>
        <label>
          Summa (so'm)
          <input
            type="number"
            min={1_000_000}
            step={1_000_000}
            value={amountSom}
            onChange={(e) => setAmountSom(Number(e.target.value))}
          />
        </label>
        <label>
          Muddat (oy)
          <input
            type="number"
            min={1}
            max={120}
            value={termMonths}
            onChange={(e) => setTermMonths(Number(e.target.value))}
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={collateralOk}
            onChange={(e) => setCollateralOk(e.target.checked)}
          />
          Garov taqdim eta olaman
        </label>
        <button type="submit">Tavsiya olish</button>
      </form>
      {error && <p className="error-state">{error}</p>}
      {result && (
        <div className="recommend-result">
          {result.recommendations.map((item) => (
            <p key={`${item.bank}-${item.product_name}`}>
              <strong>{item.bank}</strong> — {item.product_name} (ball: {item.score})
            </p>
          ))}
          <p>{result.explanation}</p>
        </div>
      )}
    </section>
  )
}
```

(No dedicated unit test for this component — per the design spec, the recommend/AI flow is a deprioritized second-tier block in this phase. It's exercised end-to-end by the Playwright smoke test in Step 5.)

- [ ] **Step 2: Add the design tokens stylesheet**

Create `frontend/src/styles/tokens.css`:

```css
:root {
  --color-navy: #0e2c56;
  --color-navy-light: rgba(255, 255, 255, 0.04);
  --color-accent: #d9455f;
  --color-text-muted: #a9b6cf;
  --color-border: #eceef3;
  --color-positive: #1a7f4a;
  --font-heading: 'Fraunces', serif;
  --font-body: 'Inter', sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: var(--font-body);
  color: #1a1a2e;
}

.app-shell {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 240px;
  background: var(--color-navy);
  color: #f4f6fb;
  padding: 22px 0;
}

.sidebar-brand {
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 19px;
  padding: 0 20px 22px;
}

.sidebar ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.sidebar-item {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  border-left: 3px solid transparent;
  color: var(--color-text-muted);
  padding: 11px 20px;
  font-family: var(--font-body);
  font-size: 14px;
  cursor: pointer;
}

.sidebar-item.active {
  border-left-color: var(--color-accent);
  color: #fff;
  font-weight: 600;
  background: var(--color-navy-light);
}

.main-content {
  flex: 1;
  padding: 28px 30px;
  background: #fff;
}

.main-content h1 {
  font-family: var(--font-heading);
  font-size: 24px;
  color: var(--color-navy);
}

.product-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.product-table th {
  text-align: left;
  color: #8891a5;
  font-weight: 500;
  border-bottom: 1px solid var(--color-border);
  padding: 8px 0;
}

.product-table td {
  padding: 10px 0;
  border-bottom: 1px solid #f4f5f8;
  font-variant-numeric: tabular-nums;
}

.empty-state {
  color: #8891a5;
}

.recommend-panel button[type='submit'] {
  border: 1.5px solid var(--color-accent);
  color: var(--color-accent);
  background: none;
  font-weight: 600;
  padding: 9px 18px;
  border-radius: 6px;
  cursor: pointer;
}
```

- [ ] **Step 3: Wire up the App shell**

Delete `frontend/src/App.css` (scaffold default, unused).

Overwrite `frontend/src/App.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { ProductTable } from './components/ProductTable'
import { RecommendPanel } from './components/RecommendPanel'
import { fetchCategories, fetchProducts } from './lib/api'
import type { Category, Product } from './lib/types'

export function App() {
  const [categories, setCategories] = useState<Category[]>([])
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [products, setProducts] = useState<Product[]>([])

  useEffect(() => {
    fetchCategories().then((data) => {
      setCategories(data)
      if (data.length > 0) {
        setActiveCategory(data[0].key)
      }
    })
  }, [])

  useEffect(() => {
    if (!activeCategory) return
    fetchProducts(activeCategory).then(setProducts)
  }, [activeCategory])

  const activeLabel = categories.find((c) => c.key === activeCategory)?.label ?? 'Bozor Tahlili'

  return (
    <div className="app-shell">
      <Sidebar categories={categories} activeCategory={activeCategory} onSelect={setActiveCategory} />
      <main className="main-content">
        <h1>{activeLabel}</h1>
        <ProductTable products={products} />
        {activeCategory && <RecommendPanel category={activeCategory} />}
      </main>
    </div>
  )
}
```

Overwrite `frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './styles/tokens.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 4: Verify the app builds and unit tests still pass**

Run (from `frontend/`): `npm test`
Expected: all passed (Sidebar, ProductTable, api client tests from Tasks 6–8)

Run: `npm run build`
Expected: builds without TypeScript errors

- [ ] **Step 5: Write the Playwright smoke test**

Create `frontend/e2e/dashboard.spec.ts`:

```ts
import { test, expect } from '@playwright/test'

test('selecting a sidebar category updates the product table heading', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('button', { name: 'Mikroqarz (oflayn)' })).toBeVisible()

  await page.getByRole('button', { name: 'Mikroqarz (oflayn)' }).click()

  await expect(page.getByRole('heading', { name: 'Mikroqarz (oflayn)' })).toBeVisible()
})
```

**Precondition (documented, not automated):** this test calls the real backend, so the FastAPI server must already be running on `http://localhost:8000` before running it — start it with `.venv\Scripts\python.exe -m uvicorn api.main:app --reload` from the repo root in a separate terminal, matching the existing manual E2E steps in `README.md`.

Run (from `frontend/`, with the backend already running): `npm run test:e2e`
Expected: 1 passed

- [ ] **Step 6: Commit**

```bash
git add frontend/src frontend/e2e
git commit -m "feat: wire up App shell with RecommendPanel and design tokens"
```

---

### Task 10: Remove the Streamlit dashboard and update docs

**Files:**
- Delete: `dashboard/app.py`, `dashboard/__init__.py`, `dashboard/__pycache__/`
- Delete: `tests/dashboard/test_app.py`, `tests/dashboard/__init__.py`
- Modify: `requirements.txt`
- Modify: `README.md`

**Interfaces:** none — this task only removes superseded code and updates documentation.

- [ ] **Step 1: Remove the Streamlit dashboard and its tests**

```bash
git rm -r dashboard tests/dashboard
```

- [ ] **Step 2: Remove the `streamlit` dependency**

In `requirements.txt`, remove the line `streamlit==1.38.0`.

- [ ] **Step 3: Update `README.md`**

Replace the "## Dashboard'ni ishga tushirish" section (currently instructing `streamlit run dashboard/app.py`) with:

```markdown
## Frontend'ni ishga tushirish

API alohida terminalda ishlab turgan holda:

```bash
cd frontend
npm install   # birinchi marta
npm run dev
```

Brauzerda `http://localhost:5173` ochiladi. Kategoriya sidebar'da tanlanadi,
taqqoslash jadvali va "Tavsiya olish" bo'limi asosiy panelda ko'rsatiladi.
```

Also update the "Loyiha tuzilishi" section's `dashboard/` line to `frontend/` with a matching description ("React/Vite/TypeScript UI").

- [ ] **Step 4: Run the full backend test suite to confirm no leftover references**

Run: `.venv/Scripts/python.exe -m pytest --cov=. --cov-report=term-missing`
Expected: all passed, no `dashboard` import errors

- [ ] **Step 5: Commit**

```bash
git add requirements.txt README.md
git commit -m "chore: remove Streamlit dashboard in favor of the React frontend"
```

---

## Final Verification

After all 10 tasks:

1. Backend: `.venv/Scripts/python.exe -m pytest --cov=. --cov-report=term-missing` — all pass, 80%+ on `db/`, `recommender/`, `scrapers/orchestrator.py`, `api/`.
2. Frontend unit/component tests: `cd frontend && npm test` — all pass.
3. Manual smoke check: start the API (`uvicorn api.main:app --reload`) and the frontend (`npm run dev`), open `http://localhost:5173`, confirm the sidebar shows all 11 categories, the 4 categories with existing scraped data render a comparison table, and the 7 new categories show the "hozircha ma'lumot yo'q" empty state.
4. `cd frontend && npm run test:e2e` (with the API running) — 1 passed.
