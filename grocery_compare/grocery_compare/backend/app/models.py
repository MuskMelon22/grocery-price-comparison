"""ORM models (plan section 5)."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

STORES = {"BigBasket": "https://www.bigbasket.com", "JioMart": "https://www.jiomart.com"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # stored naive, always UTC


class Store(Base):
    __tablename__ = "stores"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    base_url: Mapped[str] = mapped_column(String(200))


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    query: Mapped[str] = mapped_column(String(60), index=True)
    pincode: Mapped[str] = mapped_column(String(6))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(10))  # success | partial | failed | blocked
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)

    store: Mapped[Store] = relationship()


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    store_product_url: Mapped[str] = mapped_column(String(500), unique=True)
    name: Mapped[str] = mapped_column(String(300))
    brand: Mapped[str | None] = mapped_column(String(60))
    image_url: Mapped[str | None] = mapped_column(String(500))
    pack_qty_base: Mapped[float | None] = mapped_column(Float)  # grams, ml or item count
    pack_kind: Mapped[str] = mapped_column(String(10), default="unknown")  # weight|volume|count|unknown
    category: Mapped[str | None] = mapped_column(String(40))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    store: Mapped[Store] = relationship()
    __table_args__ = (Index("ix_products_store_name", "store_id", "name"),)


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs.id"), index=True)
    pincode: Mapped[str] = mapped_column(String(6), index=True)
    price: Mapped[float] = mapped_column(Float)
    mrp: Mapped[float] = mapped_column(Float)
    discount_pct: Mapped[float] = mapped_column(Float, default=0)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    unit_price: Mapped[float | None] = mapped_column(Float)  # ₹ per 100 g / 100 ml / item
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    product: Mapped[Product] = relationship()
    scrape_run: Mapped[ScrapeRun] = relationship()
    __table_args__ = (Index("ix_snapshots_product_time", "product_id", "scraped_at"),)


class ProductMatch(Base):
    __tablename__ = "product_matches"
    id: Mapped[int] = mapped_column(primary_key=True)
    bigbasket_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), unique=True)
    jiomart_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), unique=True)
    match_score: Mapped[float] = mapped_column(Float)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
