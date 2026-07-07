# Bank Mahsulotlari Bozor Tahlili — MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python system that scrapes retail credit product data (avtokredit, mikroqarz, kredit karta, iste'mol krediti) from 5 pilot banks' official websites, stores it with history in SQLite, and serves AI-explained recommendations through a FastAPI backend and a Streamlit dashboard.

**Architecture:** Single Python monolith. Per-bank scraper modules produce a common `Product` dataclass; an orchestrator persists results to SQLite via SQLAlchemy with full history; a rule-based scoring engine ranks products against user criteria; OpenAI generates the natural-language "why" explanation; FastAPI exposes `/products` and `/recommend`; Streamlit is the UI; APScheduler re-runs scraping on an interval.

**Tech Stack:** Python 3.11+, `requests` + `beautifulsoup4` (scraping), SQLAlchemy 2.0 + SQLite, FastAPI + Pydantic, Streamlit, APScheduler, `openai` SDK, `pytest`.

## Global Constraints

- Foydalanuvchi: faqat ichki foydalanish (auth/tashqi kirish MVP doirasida emas).
- Segment: faqat jismoniy shaxslar — 4 kategoriya: `avtokredit`, `mikroqarz`, `kredit_karta`, `istemol_krediti`.
- Pilot banklar (aniq shu 5 tasi, boshqasi yo'q): SQB, NBU, Ipoteka Bank, HamkorBank, AgroBank.
- Ma'lumot manbai: avtomatik scraping — qo'lda ma'lumot kiritish yo'q.
- Muhit: avval lokal kompyuterda ishga tushiriladi (cloud MVP doirasida emas).
- Ma'lumotlar bazasi: SQLite + SQLAlchemy; yozuvlar tarixi saqlanadi (eski qatorlar hech qachon o'chirilmaydi/yangilanmaydi, faqat yangi qator qo'shiladi).
- AI: OpenAI API (`OPENAI_API_KEY` muhit o'zgaruvchisidan o'qiladi) — faqat tushuntirish matni uchun; ballash (scoring) qoida-asoslangan.
- Backend: FastAPI. Dashboard: Streamlit. Scheduler: APScheduler.
- Test coverage maqsadi: DB, scoring, orchestrator, API uchun 80%+; scraperlar uchun fixture-asoslangan testlar yetarli.

---

## Task 1: Loyiha skeleti va bog'liqliklar

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `pytest.ini`
- Create: `conftest.py`
- Create: `data/.gitkeep`

**Interfaces:**
- Produces: `conftest.py` ichida `in_memory_engine` va `db_session` pytest fixture'lari — keyingi barcha DB-bog'liq testlar shulardan foydalanadi.

- [ ] **Step 1: `requirements.txt` yozish**

```text
requests==2.32.3
beautifulsoup4==4.12.3
sqlalchemy==2.0.35
fastapi==0.115.0
uvicorn==0.30.6
streamlit==1.38.0
apscheduler==3.10.4
openai==1.51.0
pydantic==2.9.2
pytest==8.3.3
pytest-cov==5.0.0
httpx==0.27.2
```

- [ ] **Step 2: `.gitignore` yozish**

```text
__pycache__/
*.pyc
.venv/
venv/
data/*.db
.env
.pytest_cache/
.coverage
```

- [ ] **Step 3: Virtual environment yaratish va o'rnatish**

Run: `python -m venv .venv && .venv/Scripts/pip install -r requirements.txt` (Windows) yoki `python -m venv .venv && .venv/bin/pip install -r requirements.txt` (Unix)
Expected: barcha paketlar xatosiz o'rnatiladi.

- [ ] **Step 4: `pytest.ini` yozish**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 5: `data/.gitkeep` yaratish (bo'sh fayl)**

Bu `data/` papkasini git'da saqlab qolish uchun (SQLite fayli `.gitignore` orqali chiqarib tashlanadi).

- [ ] **Step 6: `conftest.py` yozish**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base


@pytest.fixture
def in_memory_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(in_memory_engine):
    session_factory = sessionmaker(bind=in_memory_engine)
    session = session_factory()
    yield session
    session.close()
```

Bu fixture Task 2'da yaraladigan `db.models.Base`'ga bog'liq — shuning uchun bu qadam Task 2 tugagach ishlaydi (test hozircha yozilmaydi, faqat fayl tayyorlanadi).

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .gitignore pytest.ini conftest.py data/.gitkeep
git commit -m "chore: project scaffolding and dependencies"
```

---

## Task 2: Ma'lumotlar bazasi modellari

**Files:**
- Create: `db/__init__.py` (bo'sh)
- Create: `db/models.py`
- Create: `db/database.py`
- Test: `tests/db/test_models.py`

**Interfaces:**
- Produces: `db.models.Base`, `db.models.ProductRow`, `db.models.ScrapeRunRow`; `db.database.get_engine(db_path=None)`, `db.database.init_db(engine)`, `db.database.get_session_factory(engine)`.

- [ ] **Step 1: `db/__init__.py` yaratish (bo'sh fayl)**

- [ ] **Step 2: Testni yozish — `tests/db/test_models.py`**

```python
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
```

- [ ] **Step 3: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/db/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'db.models'`

- [ ] **Step 4: `db/models.py` yozish**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProductRow(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bank: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    rate_min: Mapped[float] = mapped_column(Float)
    rate_max: Mapped[float] = mapped_column(Float)
    term_min_months: Mapped[int] = mapped_column(Integer)
    term_max_months: Mapped[int] = mapped_column(Integer)
    amount_max_som: Mapped[int] = mapped_column(Integer)
    requires_collateral: Mapped[bool] = mapped_column(Boolean)
    down_payment_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str] = mapped_column(String(500))
    scraped_at: Mapped[datetime] = mapped_column(DateTime)


class ScrapeRunRow(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bank: Mapped[str] = mapped_column(String(100), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    products_found: Mapped[int] = mapped_column(Integer, default=0)
```

- [ ] **Step 5: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/db/test_models.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: `db/database.py` yozish**

```python
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "bank_products.db"


def get_engine(db_path: Path | None = None):
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def get_session_factory(engine):
    return sessionmaker(bind=engine)
```

- [ ] **Step 7: `tests/db/test_database.py` yozish va ishga tushirish**

```python
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
```

Run: `pytest tests/db/test_database.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add db/ tests/db/
git commit -m "feat: add SQLAlchemy models and database setup"
```

---

## Task 3: Umumiy scraping yordamchi funksiyalari

**Files:**
- Create: `scrapers/__init__.py` (bo'sh)
- Create: `scrapers/utils.py`
- Test: `tests/scrapers/test_utils.py`

**Interfaces:**
- Produces: `scrapers.utils.fetch_html(url, timeout=15) -> str`, `html_to_text(html) -> str`, `extract_section(text, start_heading, end_heading) -> str`, `extract_percentages(text) -> list[float]`, `extract_term_months(text) -> list[int]`, `extract_amount_som(text) -> int | None`, `has_collateral_requirement(text) -> bool`.

- [ ] **Step 1: `scrapers/__init__.py` yaratish (bo'sh fayl)**

- [ ] **Step 2: Testni yozish — `tests/scrapers/test_utils.py`**

```python
from scrapers.utils import (
    extract_amount_som,
    extract_percentages,
    extract_section,
    extract_term_months,
    has_collateral_requirement,
    html_to_text,
)

SAMPLE_HTML = """
<html><body>
<h2>Avtokredit</h2>
<p>Yillik foiz stavkasi: 24.9% dan 27,9% gacha. Muddati: 12 oydan 60 oygacha.
Kredit miqdori: 800 mln.so'mgacha. Boshlang'ich badal: 30%.
Kredit kafolati: Sotib olingan avtomobil garov sifatida olinadi.</p>
<h2>Mikroqarz</h2>
<p>Yillik foiz stavkasi: 28% dan 31% gacha. Muddati: 3 oydan 36 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Mavjud emas.</p>
</body></html>
"""


def test_html_to_text_strips_tags():
    text = html_to_text(SAMPLE_HTML)
    assert "<h2>" not in text
    assert "Avtokredit" in text


def test_extract_section_isolates_category_block():
    text = html_to_text(SAMPLE_HTML)
    section = extract_section(text, "Avtokredit", "Mikroqarz")
    assert "24.9%" in section
    assert "28%" not in section


def test_extract_percentages_finds_all_rates():
    text = "24.9% dan 27,9% gacha, boshlang'ich badal 30%"
    assert extract_percentages(text) == [24.9, 27.9, 30.0]


def test_extract_term_months_finds_range():
    text = "Muddati: 12 oydan 60 oygacha"
    assert extract_term_months(text) == [12, 60]


def test_extract_amount_som_parses_million():
    text = "Kredit miqdori: 800 mln.so'mgacha"
    assert extract_amount_som(text) == 800_000_000


def test_extract_amount_som_parses_billion():
    text = "Kredit miqdori: 5 mlrd.so'mgacha"
    assert extract_amount_som(text) == 5_000_000_000


def test_extract_amount_som_returns_none_when_absent():
    assert extract_amount_som("Bu yerda summa yo'q") is None


def test_has_collateral_requirement_true_when_garov_mentioned():
    assert has_collateral_requirement("Sotib olingan avtomobil garov sifatida olinadi") is True


def test_has_collateral_requirement_false_when_mavjud_emas():
    assert has_collateral_requirement("Kredit kafolati: Mavjud emas") is False
```

- [ ] **Step 3: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/scrapers/test_utils.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scrapers.utils'`

- [ ] **Step 4: `scrapers/utils.py` yozish**

```python
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup


def fetch_html(url: str, timeout: int = 15) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BankAnalizBot/1.0)"}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def extract_section(text: str, start_heading: str, end_heading: str | None) -> str:
    start_idx = text.find(start_heading)
    if start_idx == -1:
        return ""
    start_idx += len(start_heading)
    if end_heading:
        end_idx = text.find(end_heading, start_idx)
        if end_idx == -1:
            end_idx = len(text)
    else:
        end_idx = len(text)
    return text[start_idx:end_idx]


def extract_percentages(text: str) -> list[float]:
    matches = re.findall(r"(\d{1,2}(?:[.,]\d{1,2})?)\s*%", text)
    values = [float(m.replace(",", ".")) for m in matches]
    seen: list[float] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen


def extract_term_months(text: str) -> list[int]:
    matches = re.findall(r"(\d{1,3})\s*oy", text)
    values = sorted({int(m) for m in matches if int(m) <= 120})
    return values


def extract_amount_som(text: str) -> int | None:
    mln_matches = re.findall(r"(\d{1,5})\s*mln\.?\s*so", text, flags=re.IGNORECASE)
    mlrd_matches = re.findall(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*mlrd\.?\s*so", text, flags=re.IGNORECASE)
    amounts = [int(m) * 1_000_000 for m in mln_matches]
    amounts += [int(float(m.replace(",", "."))) * 1_000_000_000 for m in mlrd_matches]
    return max(amounts) if amounts else None


def has_collateral_requirement(text: str) -> bool:
    lowered = text.lower()
    if "mavjud emas" in lowered or "garovsiz" in lowered:
        return False
    return "garov" in lowered
```

- [ ] **Step 5: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/scrapers/test_utils.py -v`
Expected: PASS (9 passed)

- [ ] **Step 6: Commit**

```bash
git add scrapers/__init__.py scrapers/utils.py tests/scrapers/test_utils.py
git commit -m "feat: add text-based scraping extraction utilities"
```

---

## Task 4: Product dataclass va BaseScraper/TextSectionScraper

**Files:**
- Create: `scrapers/base.py`
- Test: `tests/scrapers/test_base.py`

**Interfaces:**
- Consumes: `scrapers.utils.fetch_html`, `html_to_text`, `extract_section`, `extract_percentages`, `extract_term_months`, `extract_amount_som`, `has_collateral_requirement` (Task 3).
- Produces: `scrapers.base.Product` dataclass (fields: `bank, category, product_name, rate_min, rate_max, term_min_months, term_max_months, amount_max_som, requires_collateral, down_payment_pct, source_url, scraped_at`); `scrapers.base.BaseScraper` (abstract, `run() -> list[Product]`, abstract `parse(html) -> list[Product]`); `scrapers.base.TextSectionScraper(BaseScraper)` (concrete `parse`, needs `bank_name: str`, `url: str`, `CATEGORY_HEADINGS: dict[str, tuple[str, str | None]]` class attributes) — every bank scraper (Task 5-9) subclasses this.

- [ ] **Step 1: Testni yozish — `tests/scrapers/test_base.py`**

```python
from unittest.mock import patch

from scrapers.base import Product, TextSectionScraper

SAMPLE_HTML = """
<html><body>
<h2>Avtokredit</h2>
<p>Yillik foiz stavkasi: 24.9% dan 27,9% gacha. Muddati: 12 oydan 60 oygacha.
Kredit miqdori: 800 mln.so'mgacha.
Kredit kafolati: Sotib olingan avtomobil garov sifatida olinadi.</p>
<h2>Mikroqarz</h2>
<p>Yillik foiz stavkasi: 28% dan 31% gacha. Muddati: 3 oydan 36 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Mavjud emas.</p>
</body></html>
"""


class FakeBankScraper(TextSectionScraper):
    bank_name = "FakeBank"
    url = "https://fakebank.uz/kredit"
    CATEGORY_HEADINGS = {
        "avtokredit": ("Avtokredit", "Mikroqarz"),
        "mikroqarz": ("Mikroqarz", None),
    }


def test_parse_returns_one_product_per_category():
    scraper = FakeBankScraper()
    products = scraper.parse(SAMPLE_HTML)

    assert len(products) == 2
    categories = {p.category for p in products}
    assert categories == {"avtokredit", "mikroqarz"}


def test_parse_extracts_correct_fields_for_avtokredit():
    scraper = FakeBankScraper()
    products = scraper.parse(SAMPLE_HTML)
    avtokredit = next(p for p in products if p.category == "avtokredit")

    assert isinstance(avtokredit, Product)
    assert avtokredit.bank == "FakeBank"
    assert avtokredit.rate_min == 24.9
    assert avtokredit.rate_max == 27.9
    assert avtokredit.term_min_months == 12
    assert avtokredit.term_max_months == 60
    assert avtokredit.amount_max_som == 800_000_000
    assert avtokredit.requires_collateral is True


def test_parse_marks_mikroqarz_as_collateral_free():
    scraper = FakeBankScraper()
    products = scraper.parse(SAMPLE_HTML)
    mikroqarz = next(p for p in products if p.category == "mikroqarz")

    assert mikroqarz.requires_collateral is False


def test_run_calls_fetch_html_then_parse():
    scraper = FakeBankScraper()
    with patch("scrapers.base.fetch_html", return_value=SAMPLE_HTML) as mock_fetch:
        products = scraper.run()

    mock_fetch.assert_called_once_with("https://fakebank.uz/kredit")
    assert len(products) == 2


def test_parse_skips_category_when_fields_missing():
    class IncompleteScraper(TextSectionScraper):
        bank_name = "IncompleteBank"
        url = "https://incomplete.uz"
        CATEGORY_HEADINGS = {"kredit_karta": ("Kredit karta", None)}

    products = IncompleteScraper().parse("<html><body><p>Hech qanday mos ma'lumot yo'q</p></body></html>")
    assert products == []
```

- [ ] **Step 2: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/scrapers/test_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scrapers.base'`

- [ ] **Step 3: `scrapers/base.py` yozish**

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from scrapers.utils import (
    extract_amount_som,
    extract_percentages,
    extract_section,
    extract_term_months,
    fetch_html,
    has_collateral_requirement,
    html_to_text,
)


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


class BaseScraper(ABC):
    bank_name: str
    url: str

    def run(self) -> list[Product]:
        html = fetch_html(self.url)
        return self.parse(html)

    @abstractmethod
    def parse(self, html: str) -> list[Product]:
        ...


class TextSectionScraper(BaseScraper):
    """Umumiy parser: HTML'ni matnga aylantirib, sarlavhalar orasidagi
    bo'limlardan foiz stavkasi, muddat, summa va garov ma'lumotini o'qiydi.
    Har bir bank sinfi faqat bank_name, url, CATEGORY_HEADINGS'ni belgilaydi."""

    CATEGORY_HEADINGS: dict[str, tuple[str, str | None]] = {}

    def parse(self, html: str) -> list[Product]:
        text = html_to_text(html)
        now = datetime.now(timezone.utc)
        products: list[Product] = []

        for category, (start_heading, end_heading) in self.CATEGORY_HEADINGS.items():
            section = extract_section(text, start_heading, end_heading)
            if not section.strip():
                continue

            rates = extract_percentages(section)
            terms = extract_term_months(section)
            amount = extract_amount_som(section)
            if not rates or not terms or amount is None:
                continue

            products.append(
                Product(
                    bank=self.bank_name,
                    category=category,
                    product_name=f"{self.bank_name} {start_heading}",
                    rate_min=min(rates),
                    rate_max=max(rates),
                    term_min_months=min(terms),
                    term_max_months=max(terms),
                    amount_max_som=amount,
                    requires_collateral=has_collateral_requirement(section),
                    down_payment_pct=None,
                    source_url=self.url,
                    scraped_at=now,
                )
            )
        return products
```

- [ ] **Step 4: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/scrapers/test_base.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add scrapers/base.py tests/scrapers/test_base.py
git commit -m "feat: add Product dataclass and TextSectionScraper base class"
```

---

## Design Amendment (recorded during Task 5 execution)

Live research during Task 5 found that real bank websites commonly spread retail
credit categories across **separate pages** rather than one page with four
adjacent headings (SQB's avtokredit content, for example, lives at a different
path than its other retail products). `TextSectionScraper` (Task 4) is amended
with an optional `CATEGORY_URLS: dict[str, str] | None` class attribute:

- **Default (`None`):** unchanged single-page behavior — `run()` fetches `self.url`
  once, `parse()` splits it into sections via `CATEGORY_HEADINGS`. Existing Task 4
  tests must keep passing unmodified.
- **When set:** `run()` fetches each category's own URL from `CATEGORY_URLS` instead
  of `self.url`, and applies the matching `CATEGORY_HEADINGS` entry (if present) to
  narrow the fetched page to a section, or uses the whole page text if no heading
  entry exists for that category.

Every bank scraper task (5-9) may set `CATEGORY_URLS` instead of (or alongside)
`CATEGORY_HEADINGS` once research shows categories live on separate pages. This
amendment does not change `Product`, `BaseScraper`, or any other task's interface.

---

## Task 5: SQB scraper

**Files:**
- Create: `scrapers/sqb.py`
- Create: `tests/scrapers/fixtures/sqb_sample.html`
- Test: `tests/scrapers/test_sqb.py`

**Interfaces:**
- Consumes: `scrapers.base.TextSectionScraper`, `Product` (Task 4).
- Produces: `scrapers.sqb.SQBScraper` — subclass foydalaniladi Task 10 registry'da.

- [ ] **Step 1: SQB rasmiy saytini tekshirish**

SQB (`sqb.uz`) saytiga kirib, jismoniy shaxslar uchun avtokredit, mikroqarz, kredit karta va iste'mol krediti mahsulotlari ko'rsatilgan sahifa(lar)ni toping. Har bir kategoriya uchun sahifa manzili (URL) va sahifadagi bo'lim sarlavhalarini (masalan "Avtokredit", "Mikrokredit" va h.k. — sayt aynan qanday nom ishlatishini tekshiring) yozib qo'ying. Agar barcha kategoriyalar bitta sahifada bo'lmasa, `CATEGORY_HEADINGS`o'rniga har bir kategoriya uchun alohida `run()` chaqirig'i kerak bo'ladi — bunday holda shu taskni bajarish paytida `SQBScraper.run()` metodini category-per-URL loop qiladigan qilib override qiling (Step 4'dagi shablonni moslashtiring).

- [ ] **Step 2: Fixture yaratish — `tests/scrapers/fixtures/sqb_sample.html`**

```html
<html><body>
<h2>Avtokredit</h2>
<p>Yillik foiz stavkasi: 24.9% dan 27,9% gacha. Muddati: 12 oydan 60 oygacha.
Kredit miqdori: 800 mln.so'mgacha. Boshlang'ich badal: 30%.
Kredit kafolati: Sotib olingan avtomobil garov sifatida olinadi.</p>
<h2>Mikroqarz</h2>
<p>Yillik foiz stavkasi: 28% dan 31% gacha. Muddati: 3 oydan 36 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Mavjud emas.</p>
<h2>Kredit karta</h2>
<p>Yillik foiz stavkasi: 30%. Muddati: 60 oygacha.
Kredit miqdori: 50 mln.so'mgacha. Kredit kafolati: Mavjud emas.</p>
<h2>Iste'mol krediti</h2>
<p>Yillik foiz stavkasi: 25% dan 27% gacha. Muddati: 12 oydan 60 oygacha.
Kredit miqdori: 200 mln.so'mgacha. Kredit kafolati: Uchunchi shaxs kafolati.</p>
</body></html>
```

- [ ] **Step 3: Testni yozish — `tests/scrapers/test_sqb.py`**

```python
from pathlib import Path

from scrapers.sqb import SQBScraper

FIXTURE = Path(__file__).parent / "fixtures" / "sqb_sample.html"


def test_sqb_scraper_parses_all_four_categories():
    html = FIXTURE.read_text(encoding="utf-8")
    products = SQBScraper().parse(html)

    categories = {p.category for p in products}
    assert categories == {"avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"}
    assert all(p.bank == "SQB" for p in products)
```

- [ ] **Step 4: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/scrapers/test_sqb.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scrapers.sqb'`

- [ ] **Step 5: `scrapers/sqb.py` yozish**

Step 1'da topilgan haqiqiy URL'ni `url` maydoniga qo'ying (quyida vaqtinchalik bosh sahifa URL'i ko'rsatilgan — Step 1 natijasi bilan almashtiring):

```python
from scrapers.base import TextSectionScraper


class SQBScraper(TextSectionScraper):
    bank_name = "SQB"
    url = "https://sqb.uz/uz/individuals/credits/"
    CATEGORY_HEADINGS = {
        "avtokredit": ("Avtokredit", "Mikroqarz"),
        "mikroqarz": ("Mikroqarz", "Kredit karta"),
        "kredit_karta": ("Kredit karta", "Iste'mol krediti"),
        "istemol_krediti": ("Iste'mol krediti", None),
    }
```

- [ ] **Step 6: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/scrapers/test_sqb.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add scrapers/sqb.py tests/scrapers/test_sqb.py tests/scrapers/fixtures/sqb_sample.html
git commit -m "feat: add SQB scraper"
```

---

## Task 6: NBU scraper

**Files:**
- Create: `scrapers/nbu.py`
- Create: `tests/scrapers/fixtures/nbu_sample.html`
- Test: `tests/scrapers/test_nbu.py`

**Interfaces:**
- Consumes: `scrapers.base.TextSectionScraper` (Task 4).
- Produces: `scrapers.nbu.NBUScraper`.

- [ ] **Step 1: NBU rasmiy saytini tekshirish**

NBU saytiga (`nbu.uz`) kirib, jismoniy shaxslar bo'limidan 4 kategoriya sahifasi/bo'limini toping, URL va sarlavha nomlarini yozib qo'ying (Task 5 / Step 1 bilan bir xil jarayon).

- [ ] **Step 2: Fixture yaratish — `tests/scrapers/fixtures/nbu_sample.html`**

```html
<html><body>
<h2>Avtokredit</h2>
<p>Yillik foiz stavkasi: 20.9% dan 23,9% gacha. Muddati: 12 oydan 60 oygacha.
Kredit miqdori: 500 mln.so'mgacha. Kredit kafolati: Sotib olingan avtomobil garov sifatida olinadi.</p>
<h2>Mikroqarz</h2>
<p>Yillik foiz stavkasi: 30% dan 34% gacha. Muddati: 6 oydan 48 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Mavjud emas.</p>
<h2>Kredit karta</h2>
<p>Yillik foiz stavkasi: 25.55% dan 54,75% gacha. Muddati: 48 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Mavjud emas.</p>
<h2>Iste'mol krediti</h2>
<p>Yillik foiz stavkasi: 21.9% dan 24,9% gacha. Muddati: 12 oydan 60 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Ko'chmas mulk garovi.</p>
</body></html>
```

- [ ] **Step 3: Testni yozish — `tests/scrapers/test_nbu.py`**

```python
from pathlib import Path

from scrapers.nbu import NBUScraper

FIXTURE = Path(__file__).parent / "fixtures" / "nbu_sample.html"


def test_nbu_scraper_parses_all_four_categories():
    html = FIXTURE.read_text(encoding="utf-8")
    products = NBUScraper().parse(html)

    categories = {p.category for p in products}
    assert categories == {"avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"}
    assert all(p.bank == "NBU" for p in products)
```

- [ ] **Step 4: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/scrapers/test_nbu.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scrapers.nbu'`

- [ ] **Step 5: `scrapers/nbu.py` yozish (Step 1 natijasidagi haqiqiy URL bilan)**

```python
from scrapers.base import TextSectionScraper


class NBUScraper(TextSectionScraper):
    bank_name = "NBU"
    url = "https://nbu.uz/uz/individuals/credits/"
    CATEGORY_HEADINGS = {
        "avtokredit": ("Avtokredit", "Mikroqarz"),
        "mikroqarz": ("Mikroqarz", "Kredit karta"),
        "kredit_karta": ("Kredit karta", "Iste'mol krediti"),
        "istemol_krediti": ("Iste'mol krediti", None),
    }
```

- [ ] **Step 6: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/scrapers/test_nbu.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add scrapers/nbu.py tests/scrapers/test_nbu.py tests/scrapers/fixtures/nbu_sample.html
git commit -m "feat: add NBU scraper"
```

---

## Task 7: Ipoteka Bank scraper

**Files:**
- Create: `scrapers/ipoteka.py`
- Create: `tests/scrapers/fixtures/ipoteka_sample.html`
- Test: `tests/scrapers/test_ipoteka.py`

**Interfaces:**
- Consumes: `scrapers.base.TextSectionScraper` (Task 4).
- Produces: `scrapers.ipoteka.IpotekaBankScraper`.

- [ ] **Step 1: Ipoteka Bank rasmiy saytini tekshirish**

`ipotekabank.uz` saytidan 4 kategoriya sahifasi/bo'limini toping, URL va sarlavhalarni yozib qo'ying.

- [ ] **Step 2: Fixture yaratish — `tests/scrapers/fixtures/ipoteka_sample.html`**

```html
<html><body>
<h2>Avtokredit</h2>
<p>Yillik foiz stavkasi: 0% dan 18,5% gacha. Muddati: 12 oydan 60 oygacha.
Kredit miqdori: 480 mln.so'mgacha. Kredit kafolati: Sotib olingan avtomobil garov sifatida olinadi.</p>
<h2>Mikroqarz</h2>
<p>Yillik foiz stavkasi: 24% dan 48% gacha. Muddati: 12 oydan 36 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Uchunchi shaxs kafilligi.</p>
<h2>Kredit karta</h2>
<p>Yillik foiz stavkasi: 26.9%. Muddati: 48 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Sug'urta polisi.</p>
<h2>Iste'mol krediti</h2>
<p>Yillik foiz stavkasi: 22.99% dan 26,99% gacha. Muddati: 60 oygacha.
Kredit miqdori: 200 mln.so'mgacha. Kredit kafolati: Uchunchi shaxs kafolati.</p>
</body></html>
```

- [ ] **Step 3: Testni yozish — `tests/scrapers/test_ipoteka.py`**

```python
from pathlib import Path

from scrapers.ipoteka import IpotekaBankScraper

FIXTURE = Path(__file__).parent / "fixtures" / "ipoteka_sample.html"


def test_ipoteka_scraper_parses_all_four_categories():
    html = FIXTURE.read_text(encoding="utf-8")
    products = IpotekaBankScraper().parse(html)

    categories = {p.category for p in products}
    assert categories == {"avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"}
    assert all(p.bank == "Ipoteka Bank" for p in products)
```

- [ ] **Step 4: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/scrapers/test_ipoteka.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scrapers.ipoteka'`

- [ ] **Step 5: `scrapers/ipoteka.py` yozish (Step 1 natijasidagi haqiqiy URL bilan)**

```python
from scrapers.base import TextSectionScraper


class IpotekaBankScraper(TextSectionScraper):
    bank_name = "Ipoteka Bank"
    url = "https://ipotekabank.uz/uz/individuals/credits/"
    CATEGORY_HEADINGS = {
        "avtokredit": ("Avtokredit", "Mikroqarz"),
        "mikroqarz": ("Mikroqarz", "Kredit karta"),
        "kredit_karta": ("Kredit karta", "Iste'mol krediti"),
        "istemol_krediti": ("Iste'mol krediti", None),
    }
```

- [ ] **Step 6: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/scrapers/test_ipoteka.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add scrapers/ipoteka.py tests/scrapers/test_ipoteka.py tests/scrapers/fixtures/ipoteka_sample.html
git commit -m "feat: add Ipoteka Bank scraper"
```

---

## Task 8: HamkorBank scraper

**Files:**
- Create: `scrapers/hamkor.py`
- Create: `tests/scrapers/fixtures/hamkor_sample.html`
- Test: `tests/scrapers/test_hamkor.py`

**Interfaces:**
- Consumes: `scrapers.base.TextSectionScraper` (Task 4).
- Produces: `scrapers.hamkor.HamkorBankScraper`.

- [ ] **Step 1: HamkorBank rasmiy saytini tekshirish**

`hamkorbank.uz` saytidan 4 kategoriya sahifasi/bo'limini toping, URL va sarlavhalarni yozib qo'ying.

- [ ] **Step 2: Fixture yaratish — `tests/scrapers/fixtures/hamkor_sample.html`**

```html
<html><body>
<h2>Avtokredit</h2>
<p>Yillik foiz stavkasi: 25% dan 30% gacha. Muddati: 12 oydan 60 oygacha.
Kredit miqdori: 600 mln.so'mgacha. Kredit kafolati: Sotib olingan avtomobil garov sifatida olinadi.</p>
<h2>Mikroqarz</h2>
<p>Yillik foiz stavkasi: 24.5% dan 46,9% gacha. Muddati: 2 oydan 36 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Mavjud emas.</p>
<h2>Kredit karta</h2>
<p>Yillik foiz stavkasi: 40%. Muddati: 48 oygacha.
Kredit miqdori: 50 mln.so'mgacha. Kredit kafolati: Mavjud emas.</p>
<h2>Iste'mol krediti</h2>
<p>Yillik foiz stavkasi: 27% dan 29% gacha. Muddati: 12 oydan 60 oygacha.
Kredit miqdori: 200 mln.so'mgacha. Kredit kafolati: Uchunchi shaxs kafolati.</p>
</body></html>
```

- [ ] **Step 3: Testni yozish — `tests/scrapers/test_hamkor.py`**

```python
from pathlib import Path

from scrapers.hamkor import HamkorBankScraper

FIXTURE = Path(__file__).parent / "fixtures" / "hamkor_sample.html"


def test_hamkor_scraper_parses_all_four_categories():
    html = FIXTURE.read_text(encoding="utf-8")
    products = HamkorBankScraper().parse(html)

    categories = {p.category for p in products}
    assert categories == {"avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"}
    assert all(p.bank == "HamkorBank" for p in products)
```

- [ ] **Step 4: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/scrapers/test_hamkor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scrapers.hamkor'`

- [ ] **Step 5: `scrapers/hamkor.py` yozish (Step 1 natijasidagi haqiqiy URL bilan)**

```python
from scrapers.base import TextSectionScraper


class HamkorBankScraper(TextSectionScraper):
    bank_name = "HamkorBank"
    url = "https://hamkorbank.uz/uz/individuals/credits/"
    CATEGORY_HEADINGS = {
        "avtokredit": ("Avtokredit", "Mikroqarz"),
        "mikroqarz": ("Mikroqarz", "Kredit karta"),
        "kredit_karta": ("Kredit karta", "Iste'mol krediti"),
        "istemol_krediti": ("Iste'mol krediti", None),
    }
```

- [ ] **Step 6: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/scrapers/test_hamkor.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add scrapers/hamkor.py tests/scrapers/test_hamkor.py tests/scrapers/fixtures/hamkor_sample.html
git commit -m "feat: add HamkorBank scraper"
```

---

## Task 9: AgroBank scraper

**Files:**
- Create: `scrapers/agro.py`
- Create: `tests/scrapers/fixtures/agro_sample.html`
- Test: `tests/scrapers/test_agro.py`

**Interfaces:**
- Consumes: `scrapers.base.TextSectionScraper` (Task 4).
- Produces: `scrapers.agro.AgroBankScraper`.

- [ ] **Step 1: AgroBank rasmiy saytini tekshirish**

`agrobank.uz` saytidan 4 kategoriya sahifasi/bo'limini toping, URL va sarlavhalarni yozib qo'ying.

- [ ] **Step 2: Fixture yaratish — `tests/scrapers/fixtures/agro_sample.html`**

```html
<html><body>
<h2>Avtokredit</h2>
<p>Yillik foiz stavkasi: 23% dan 25% gacha. Muddati: 48 oydan 60 oygacha.
Kredit miqdori: 500 mln.so'mgacha. Kredit kafolati: Sotib olingan avtomobil garov sifatida olinadi.</p>
<h2>Mikroqarz</h2>
<p>Yillik foiz stavkasi: 30.9% dan 40,9% gacha. Muddati: 6 oydan 60 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Sug'urta polisi.</p>
<h2>Kredit karta</h2>
<p>Yillik foiz stavkasi: 35%. Muddati: 48 oygacha.
Kredit miqdori: 50 mln.so'mgacha. Kredit kafolati: Mavjud emas.</p>
<h2>Iste'mol krediti</h2>
<p>Yillik foiz stavkasi: 25% dan 27% gacha. Muddati: 12 oydan 24 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Ko'chmas mulk garovi.</p>
</body></html>
```

- [ ] **Step 3: Testni yozish — `tests/scrapers/test_agro.py`**

```python
from pathlib import Path

from scrapers.agro import AgroBankScraper

FIXTURE = Path(__file__).parent / "fixtures" / "agro_sample.html"


def test_agro_scraper_parses_all_four_categories():
    html = FIXTURE.read_text(encoding="utf-8")
    products = AgroBankScraper().parse(html)

    categories = {p.category for p in products}
    assert categories == {"avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"}
    assert all(p.bank == "AgroBank" for p in products)
```

- [ ] **Step 4: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/scrapers/test_agro.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scrapers.agro'`

- [ ] **Step 5: `scrapers/agro.py` yozish (Step 1 natijasidagi haqiqiy URL bilan)**

```python
from scrapers.base import TextSectionScraper


class AgroBankScraper(TextSectionScraper):
    bank_name = "AgroBank"
    url = "https://agrobank.uz/uz/individuals/credits/"
    CATEGORY_HEADINGS = {
        "avtokredit": ("Avtokredit", "Mikroqarz"),
        "mikroqarz": ("Mikroqarz", "Kredit karta"),
        "kredit_karta": ("Kredit karta", "Iste'mol krediti"),
        "istemol_krediti": ("Iste'mol krediti", None),
    }
```

- [ ] **Step 6: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/scrapers/test_agro.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add scrapers/agro.py tests/scrapers/test_agro.py tests/scrapers/fixtures/agro_sample.html
git commit -m "feat: add AgroBank scraper"
```

---

## Task 10: Scraper registry va orchestrator

**Files:**
- Create: `scrapers/registry.py`
- Create: `scrapers/orchestrator.py`
- Test: `tests/scrapers/test_orchestrator.py`

**Interfaces:**
- Consumes: `SQBScraper, NBUScraper, IpotekaBankScraper, HamkorBankScraper, AgroBankScraper` (Task 5-9); `db.models.ProductRow, ScrapeRunRow` (Task 2).
- Produces: `scrapers.registry.ALL_SCRAPERS` (list of scraper classes); `scrapers.orchestrator.run_all_scrapers(session) -> None` — Task 13 (API) va Task 14 (scheduler) shu funksiyani chaqiradi.

- [ ] **Step 1: `scrapers/registry.py` yozish**

```python
from scrapers.agro import AgroBankScraper
from scrapers.hamkor import HamkorBankScraper
from scrapers.ipoteka import IpotekaBankScraper
from scrapers.nbu import NBUScraper
from scrapers.sqb import SQBScraper

ALL_SCRAPERS = [
    SQBScraper,
    NBUScraper,
    IpotekaBankScraper,
    HamkorBankScraper,
    AgroBankScraper,
]
```

- [ ] **Step 2: Testni yozish — `tests/scrapers/test_orchestrator.py`**

```python
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
```

- [ ] **Step 3: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/scrapers/test_orchestrator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scrapers.orchestrator'`

- [ ] **Step 4: `scrapers/orchestrator.py` yozish**

```python
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from db.models import ProductRow, ScrapeRunRow
from scrapers.registry import ALL_SCRAPERS


def run_all_scrapers(session: Session) -> None:
    for scraper_cls in ALL_SCRAPERS:
        scraper = scraper_cls()
        run = ScrapeRunRow(
            bank=scraper.bank_name,
            started_at=datetime.now(timezone.utc),
            status="running",
        )
        session.add(run)
        session.commit()

        try:
            products = scraper.run()
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            session.commit()
            continue

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

        run.status = "success"
        run.products_found = len(products)
        run.finished_at = datetime.now(timezone.utc)
        session.commit()
```

- [ ] **Step 5: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/scrapers/test_orchestrator.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add scrapers/registry.py scrapers/orchestrator.py tests/scrapers/test_orchestrator.py
git commit -m "feat: add scraper registry and orchestrator with per-bank error isolation"
```

---

## Task 11: Ballash (scoring) mexanizmi

**Files:**
- Create: `recommender/__init__.py` (bo'sh)
- Create: `recommender/scoring.py`
- Test: `tests/recommender/test_scoring.py`

**Interfaces:**
- Produces: `recommender.scoring.Criteria` (fields: `category, amount_som, term_months, collateral_ok`), `recommender.scoring.ScoredProduct` (fields: `bank, product_name, score, rate_min, rate_max`), `recommender.scoring.score_product(criteria, product) -> float | None`, `recommender.scoring.top_recommendations(criteria, products, top_n=3) -> list[ScoredProduct]` — Task 12 va Task 13 shulardan foydalanadi. `product` parametri `category, amount_max_som, term_min_months, term_max_months, requires_collateral, rate_min, rate_max` atributlariga ega har qanday obyekt bo'lishi mumkin (duck typing — `ProductRow` ham, `Product` ham mos keladi).

- [ ] **Step 1: `recommender/__init__.py` yaratish (bo'sh fayl)**

- [ ] **Step 2: Testni yozish — `tests/recommender/test_scoring.py`**

```python
from dataclasses import dataclass

from recommender.scoring import Criteria, score_product, top_recommendations


@dataclass
class FakeProduct:
    bank: str
    category: str
    rate_min: float
    rate_max: float
    term_min_months: int
    term_max_months: int
    amount_max_som: int
    requires_collateral: bool


def test_score_product_returns_none_for_wrong_category():
    criteria = Criteria(category="mikroqarz", amount_som=50_000_000, term_months=12, collateral_ok=False)
    product = FakeProduct("SQB", "avtokredit", 24.0, 27.0, 12, 60, 800_000_000, True)
    assert score_product(criteria, product) is None


def test_score_product_returns_none_when_amount_exceeds_max():
    criteria = Criteria(category="mikroqarz", amount_som=200_000_000, term_months=12, collateral_ok=False)
    product = FakeProduct("SQB", "mikroqarz", 28.0, 31.0, 3, 36, 100_000_000, False)
    assert score_product(criteria, product) is None


def test_score_product_returns_none_when_collateral_required_but_unavailable():
    criteria = Criteria(category="avtokredit", amount_som=100_000_000, term_months=24, collateral_ok=False)
    product = FakeProduct("SQB", "avtokredit", 24.0, 27.0, 12, 60, 800_000_000, True)
    assert score_product(criteria, product) is None


def test_score_product_returns_value_for_matching_product():
    criteria = Criteria(category="mikroqarz", amount_som=50_000_000, term_months=12, collateral_ok=False)
    product = FakeProduct("SQB", "mikroqarz", 28.0, 31.0, 3, 36, 100_000_000, False)
    score = score_product(criteria, product)
    assert score is not None
    assert 0.0 < score <= 1.0


def test_top_recommendations_ranks_lower_rate_higher():
    criteria = Criteria(category="mikroqarz", amount_som=50_000_000, term_months=12, collateral_ok=True)
    cheap = FakeProduct("CheapBank", "mikroqarz", 20.0, 22.0, 3, 36, 100_000_000, False)
    expensive = FakeProduct("ExpensiveBank", "mikroqarz", 40.0, 45.0, 3, 36, 100_000_000, False)

    ranked = top_recommendations(criteria, [expensive, cheap], top_n=2)

    assert [item.bank for item in ranked] == ["CheapBank", "ExpensiveBank"]


def test_top_recommendations_respects_top_n():
    criteria = Criteria(category="mikroqarz", amount_som=50_000_000, term_months=12, collateral_ok=True)
    products = [
        FakeProduct(f"Bank{i}", "mikroqarz", 20.0 + i, 25.0 + i, 3, 36, 100_000_000, False)
        for i in range(5)
    ]
    ranked = top_recommendations(criteria, products, top_n=3)
    assert len(ranked) == 3
```

- [ ] **Step 3: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/recommender/test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'recommender.scoring'`

- [ ] **Step 4: `recommender/scoring.py` yozish**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Criteria:
    category: str
    amount_som: int
    term_months: int
    collateral_ok: bool


@dataclass
class ScoredProduct:
    bank: str
    product_name: str
    score: float
    rate_min: float
    rate_max: float


class _ScorableProduct(Protocol):
    bank: str
    category: str
    rate_min: float
    rate_max: float
    term_min_months: int
    term_max_months: int
    amount_max_som: int
    requires_collateral: bool


def score_product(criteria: Criteria, product: _ScorableProduct) -> float | None:
    if product.category != criteria.category:
        return None
    if product.amount_max_som < criteria.amount_som:
        return None
    if criteria.term_months < product.term_min_months or criteria.term_months > product.term_max_months:
        return None
    if product.requires_collateral and not criteria.collateral_ok:
        return None

    rate_score = max(0.0, 1 - (product.rate_min / 60))
    collateral_score = 1.0 if not product.requires_collateral else 0.6
    term_span = product.term_max_months - product.term_min_months
    term_score = min(1.0, term_span / 60)
    amount_headroom = min(1.0, product.amount_max_som / max(criteria.amount_som, 1) / 5)

    return round(
        rate_score * 0.40
        + collateral_score * 0.25
        + term_score * 0.20
        + amount_headroom * 0.15,
        4,
    )


def top_recommendations(
    criteria: Criteria, products: list[_ScorableProduct], top_n: int = 3
) -> list[ScoredProduct]:
    scored: list[ScoredProduct] = []
    for product in products:
        score = score_product(criteria, product)
        if score is None:
            continue
        scored.append(
            ScoredProduct(
                bank=product.bank,
                product_name=getattr(product, "product_name", product.bank),
                score=score,
                rate_min=product.rate_min,
                rate_max=product.rate_max,
            )
        )
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:top_n]
```

- [ ] **Step 5: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/recommender/test_scoring.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add recommender/__init__.py recommender/scoring.py tests/recommender/test_scoring.py
git commit -m "feat: add rule-based product scoring engine"
```

---

## Task 12: OpenAI tushuntirish generatori

**Files:**
- Create: `recommender/explain.py`
- Test: `tests/recommender/test_explain.py`

**Interfaces:**
- Consumes: `recommender.scoring.Criteria, ScoredProduct` (Task 11).
- Produces: `recommender.explain.explain_recommendation(criteria, ranked) -> str` — Task 13 (API) shuni chaqiradi.

- [ ] **Step 1: Testni yozish — `tests/recommender/test_explain.py`**

```python
from unittest.mock import MagicMock, patch

from recommender.explain import explain_recommendation
from recommender.scoring import Criteria, ScoredProduct


def make_criteria():
    return Criteria(category="mikroqarz", amount_som=50_000_000, term_months=12, collateral_ok=False)


def make_ranked():
    return [
        ScoredProduct(bank="SQB", product_name="SQB Mikroqarz", score=0.82, rate_min=28.0, rate_max=31.0),
        ScoredProduct(bank="NBU", product_name="NBU Mikroqarz", score=0.71, rate_min=30.0, rate_max=34.0),
    ]


def test_explain_recommendation_returns_fallback_text_when_no_ranked():
    result = explain_recommendation(make_criteria(), [])
    assert "topilmadi" in result.lower()


def test_explain_recommendation_calls_openai_and_returns_content():
    fake_response = MagicMock()
    fake_response.choices[0].message.content = "SQB tavsiya etiladi, chunki eng past stavkaga ega."

    with patch("recommender.explain.get_client") as mock_get_client:
        mock_get_client.return_value.chat.completions.create.return_value = fake_response
        result = explain_recommendation(make_criteria(), make_ranked())

    assert result == "SQB tavsiya etiladi, chunki eng past stavkaga ega."


def test_explain_recommendation_falls_back_to_score_list_on_api_error():
    with patch("recommender.explain.get_client") as mock_get_client:
        mock_get_client.return_value.chat.completions.create.side_effect = RuntimeError("API xatosi")
        result = explain_recommendation(make_criteria(), make_ranked())

    assert "SQB" in result
    assert "NBU" in result
```

- [ ] **Step 2: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/recommender/test_explain.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'recommender.explain'`

- [ ] **Step 3: `recommender/explain.py` yozish**

```python
from __future__ import annotations

import os

from openai import OpenAI

from recommender.scoring import Criteria, ScoredProduct

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def _format_ranking_lines(ranked: list[ScoredProduct]) -> list[str]:
    return [
        f"{i + 1}. {item.bank} — {item.product_name} "
        f"(stavka {item.rate_min}%-{item.rate_max}%, ball: {item.score})"
        for i, item in enumerate(ranked)
    ]


def explain_recommendation(criteria: Criteria, ranked: list[ScoredProduct]) -> str:
    if not ranked:
        return "Berilgan mezonlarga mos mahsulot topilmadi."

    lines = _format_ranking_lines(ranked)
    prompt = (
        f"Foydalanuvchi {criteria.category} kategoriyasida {criteria.amount_som} so'm, "
        f"{criteria.term_months} oy muddatga kredit izlamoqda. "
        "Quyidagi banklar ballash bo'yicha saralangan:\n" + "\n".join(lines) +
        "\nO'zbek tilida, 3-4 gapda, nima uchun birinchi o'rindagi bank tavsiya "
        "etilishini tushuntir."
    )

    try:
        response = get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            timeout=10,
        )
        return response.choices[0].message.content
    except Exception:
        return "\n".join(lines)
```

- [ ] **Step 4: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/recommender/test_explain.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add recommender/explain.py tests/recommender/test_explain.py
git commit -m "feat: add OpenAI-based recommendation explanation with fallback"
```

---

## Task 13: FastAPI backend

**Files:**
- Create: `api/__init__.py` (bo'sh)
- Create: `api/main.py`
- Test: `tests/api/test_main.py`

**Interfaces:**
- Consumes: `db.database.get_engine, get_session_factory, init_db` (Task 2); `db.models.ProductRow` (Task 2); `recommender.scoring.Criteria, top_recommendations` (Task 11); `recommender.explain.explain_recommendation` (Task 12).
- Produces: `api.main.app` (FastAPI instance) — Task 16 (README/ishga tushirish) shu orqali `uvicorn api.main:app` bilan ishga tushiriladi; Task 15 (dashboard) shu API'ga HTTP so'rov yuboradi.

- [ ] **Step 1: `api/__init__.py` yaratish (bo'sh fayl)**

- [ ] **Step 2: Testni yozish — `tests/api/test_main.py`**

```python
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
```

- [ ] **Step 3: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/api/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.main'`

- [ ] **Step 4: `api/main.py` yozish**

```python
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import select

from db.database import get_engine, get_session_factory, init_db
from db.models import ProductRow
from recommender.explain import explain_recommendation
from recommender.scoring import Criteria, top_recommendations

app = FastAPI(title="Bank Mahsulot Tahlili API")

_engine = get_engine()
init_db(_engine)
SessionLocal = get_session_factory(_engine)


class RecommendRequest(BaseModel):
    category: str
    amount_som: int
    term_months: int
    collateral_ok: bool


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


@app.get("/products")
def list_products(category: str | None = None, bank: str | None = None):
    with SessionLocal() as session:
        query = select(ProductRow)
        if category:
            query = query.where(ProductRow.category == category)
        if bank:
            query = query.where(ProductRow.bank == bank)
        rows = session.execute(query).scalars().all()
        return [_row_to_dict(row) for row in rows]


@app.post("/recommend")
def recommend(request: RecommendRequest):
    criteria = Criteria(
        category=request.category,
        amount_som=request.amount_som,
        term_months=request.term_months,
        collateral_ok=request.collateral_ok,
    )
    with SessionLocal() as session:
        rows = session.execute(
            select(ProductRow).where(ProductRow.category == request.category)
        ).scalars().all()

    ranked = top_recommendations(criteria, rows)
    explanation = explain_recommendation(criteria, ranked)
    return {
        "recommendations": [
            {"bank": item.bank, "product_name": item.product_name, "score": item.score}
            for item in ranked
        ],
        "explanation": explanation,
    }
```

- [ ] **Step 5: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/api/test_main.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add api/ tests/api/
git commit -m "feat: add FastAPI endpoints for products listing and recommendations"
```

---

## Task 14: Scheduler

**Files:**
- Create: `scheduler.py`
- Test: `tests/test_scheduler.py`

**Interfaces:**
- Consumes: `db.database.get_engine, get_session_factory, init_db` (Task 2); `scrapers.orchestrator.run_all_scrapers` (Task 10).
- Produces: `scheduler.build_scheduler(session_factory, interval_hours=24) -> BlockingScheduler`.

- [ ] **Step 1: Testni yozish — `tests/test_scheduler.py`**

```python
from unittest.mock import MagicMock, patch

from scheduler import build_scheduler


def test_build_scheduler_registers_one_interval_job():
    fake_session_factory = MagicMock()
    scheduler = build_scheduler(fake_session_factory, interval_hours=6)

    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].trigger.interval.total_seconds() == 6 * 3600


def test_scheduled_job_calls_run_all_scrapers_with_session():
    fake_session = MagicMock()
    fake_session_factory = MagicMock()
    fake_session_factory.return_value.__enter__.return_value = fake_session

    scheduler = build_scheduler(fake_session_factory, interval_hours=1)
    job_func = scheduler.get_jobs()[0].func

    with patch("scheduler.run_all_scrapers") as mock_run_all:
        job_func()

    mock_run_all.assert_called_once_with(fake_session)
```

- [ ] **Step 2: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/test_scheduler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scheduler'`

- [ ] **Step 3: `scheduler.py` yozish**

```python
from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler

from db.database import get_engine, get_session_factory, init_db
from scrapers.orchestrator import run_all_scrapers


def build_scheduler(session_factory, interval_hours: int = 24) -> BlockingScheduler:
    scheduler = BlockingScheduler()

    def job() -> None:
        with session_factory() as session:
            run_all_scrapers(session)

    scheduler.add_job(job, "interval", hours=interval_hours)
    return scheduler


if __name__ == "__main__":
    engine = get_engine()
    init_db(engine)
    factory = get_session_factory(engine)
    build_scheduler(factory, interval_hours=24).start()
```

- [ ] **Step 4: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/test_scheduler.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scheduler.py tests/test_scheduler.py
git commit -m "feat: add APScheduler-based periodic scraping job"
```

---

## Task 15: Streamlit dashboard

**Files:**
- Create: `dashboard/__init__.py` (bo'sh)
- Create: `dashboard/app.py`
- Test: `tests/dashboard/test_app.py`

**Interfaces:**
- Consumes: `api.main` orqali ishlaydigan HTTP API (`GET /products`, `POST /recommend`) — dashboard mustaqil jarayon sifatida ishga tushiriladi va API'ga `requests` orqali murojaat qiladi.
- Produces: `dashboard/app.py` — `streamlit run dashboard/app.py` bilan ishga tushiriladi.

- [ ] **Step 1: `dashboard/__init__.py` yaratish (bo'sh fayl)**

- [ ] **Step 2: Testni yozish — `tests/dashboard/test_app.py`**

`streamlit.testing.v1.AppTest` yordamida dashboard xatosiz ishga tushishini va asosiy elementlar mavjudligini tekshiradigan smoke test:

```python
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


def test_dashboard_renders_without_exception():
    with patch("dashboard.app.fetch_products", return_value=[]):
        at = AppTest.from_file("dashboard/app.py")
        at.run(timeout=10)

    assert not at.exception


def test_dashboard_shows_category_selectbox():
    with patch("dashboard.app.fetch_products", return_value=[]):
        at = AppTest.from_file("dashboard/app.py")
        at.run(timeout=10)

    assert len(at.selectbox) >= 1
    assert at.selectbox[0].label == "Kategoriya"
```

- [ ] **Step 3: Testni ishga tushirib, muvaffaqiyatsizlikni tasdiqlash**

Run: `pytest tests/dashboard/test_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dashboard.app'`

- [ ] **Step 4: `dashboard/app.py` yozish**

```python
from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000"
CATEGORIES = ["avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"]


def fetch_products(category: str) -> list[dict]:
    response = requests.get(f"{API_BASE_URL}/products", params={"category": category}, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_recommendation(category: str, amount_som: int, term_months: int, collateral_ok: bool) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/recommend",
        json={
            "category": category,
            "amount_som": amount_som,
            "term_months": term_months,
            "collateral_ok": collateral_ok,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


st.title("Bank Mahsulotlari Bozor Tahlili")

category = st.selectbox("Kategoriya", CATEGORIES)

st.subheader("Mavjud mahsulotlar")
products = fetch_products(category)
if products:
    st.dataframe(products)
else:
    st.info("Bu kategoriya uchun hozircha ma'lumot yo'q.")

st.subheader("Tavsiya olish")
with st.form("recommend_form"):
    amount_som = st.number_input("Summa (so'm)", min_value=1_000_000, step=1_000_000, value=50_000_000)
    term_months = st.number_input("Muddat (oy)", min_value=1, max_value=120, value=12)
    collateral_ok = st.checkbox("Garov taqdim eta olaman", value=False)
    submitted = st.form_submit_button("Tavsiya olish")

if submitted:
    result = fetch_recommendation(category, int(amount_som), int(term_months), collateral_ok)
    for item in result["recommendations"]:
        st.write(f"**{item['bank']}** — {item['product_name']} (ball: {item['score']})")
    st.write(result["explanation"])
```

- [ ] **Step 5: Testni qayta ishga tushirib, o'tishini tasdiqlash**

Run: `pytest tests/dashboard/test_app.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add dashboard/ tests/dashboard/
git commit -m "feat: add Streamlit dashboard for product comparison and recommendations"
```

---

## Task 16: README va qo'lda end-to-end tekshiruv

**Files:**
- Create: `README.md`

**Interfaces:**
- Yo'q (hujjatlashtirish vazifasi).

- [ ] **Step 1: `README.md` yozish**

```markdown
# Bank Mahsulotlari Bozor Tahlili (MVP)

## O'rnatish

\`\`\`bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt  # Windows
# yoki: .venv/bin/pip install -r requirements.txt (Unix)
\`\`\`

`OPENAI_API_KEY` muhit o'zgaruvchisini o'rnating:

\`\`\`bash
set OPENAI_API_KEY=sk-...       # Windows cmd
$env:OPENAI_API_KEY = "sk-..."  # PowerShell
\`\`\`

## Testlarni ishga tushirish

\`\`\`bash
pytest --cov=. --cov-report=term-missing
\`\`\`

## Ma'lumotlarni scraping qilish (bir martalik)

\`\`\`python
from db.database import get_engine, get_session_factory, init_db
from scrapers.orchestrator import run_all_scrapers

engine = get_engine()
init_db(engine)
with get_session_factory(engine)() as session:
    run_all_scrapers(session)
\`\`\`

## API'ni ishga tushirish

\`\`\`bash
uvicorn api.main:app --reload
\`\`\`

## Dashboard'ni ishga tushirish (API ishlab turganida, alohida terminalda)

\`\`\`bash
streamlit run dashboard/app.py
\`\`\`

## Scheduler'ni ishga tushirish (muntazam scraping uchun)

\`\`\`bash
python scheduler.py
\`\`\`
```

- [ ] **Step 2: To'liq test suite'ni ishga tushirish va coverage tekshirish**

Run: `pytest --cov=. --cov-report=term-missing`
Expected: barcha testlar PASS; `db/`, `recommender/`, `scrapers/orchestrator.py`, `api/` uchun coverage 80%+.

- [ ] **Step 3: Qo'lda end-to-end tekshiruv**

1. `python -c "from db.database import get_engine, get_session_factory, init_db; from scrapers.orchestrator import run_all_scrapers; e=get_engine(); init_db(e); s=get_session_factory(e)(); run_all_scrapers(s)"` — scraping ishga tushirish (Task 5-9'dagi haqiqiy URL'lar sozlangan bo'lishi kerak).
2. `uvicorn api.main:app --reload` — API'ni ishga tushirish, brauzerda `http://localhost:8000/docs` orqali `/products` va `/recommend` endpointlarini qo'lda sinash.
3. `streamlit run dashboard/app.py` — dashboard ochilib, kategoriya tanlab, mahsulotlar jadvali va tavsiya formasi ishlashini tekshirish.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add setup and usage instructions"
```

---

## Reja bo'yicha o'z-o'zini tekshirish (bajarildi)

- **Spec qamrovi:** Barcha spec bo'limlari (MVP ko'lami, arxitektura, komponentlar, ma'lumotlar oqimi, xatolarni boshqarish, testlash) Task 1-16 orqali qoplandi.
- **Placeholder skanerlash:** "TBD"/"TODO" yo'q; har bir bank scraperining URL'ini "Step 1: saytni tekshirish" harakati orqali aniq belgilash so'raladi (bu — bajariladigan tadqiqot qadami, kodsiz bo'sh joy emas).
- **Tur izchilligi:** `Product` (Task 4), `ProductRow` (Task 2), `Criteria`/`ScoredProduct` (Task 11) maydonlari barcha keyingi tasklarda bir xil nomlar bilan ishlatildi (`category`, `amount_max_som`, `term_min_months`/`term_max_months`, `requires_collateral`, `rate_min`/`rate_max`).
- **Ko'lam:** Bitta MVP sifatida izchil — barcha tasklar bitta ishlaydigan tizimni quradi, mustaqil kichik loyihalarga bo'linishga hojat yo'q.