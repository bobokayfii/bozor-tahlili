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
