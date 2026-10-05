"""Pydantic request/response models for the API."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

Pincode = Annotated[str, StringConstraints(pattern=r"^\d{6}$")]
Query = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)]
StoreKey = Literal["bigbasket", "jiomart"]


class ProductOut(BaseModel):
    id: int
    store: str
    name: str
    brand: str | None
    image_url: str | None
    url: str
    pack_qty_base: float | None
    pack_kind: str
    category: str | None
    price: float
    mrp: float
    discount_pct: float
    unit_price: float | None
    in_stock: bool
    scraped_at: datetime


class MatchRow(BaseModel):
    match_id: int
    match_score: float
    bigbasket: ProductOut
    jiomart: ProductOut
    cheaper: StoreKey | None
    saving_abs: float
    saving_pct: float


class SearchResponse(BaseModel):
    query: str
    pincode: str
    scraped_at: datetime | None
    warnings: list[str]
    matched: list[MatchRow]
    only_bigbasket: list[ProductOut]
    only_jiomart: list[ProductOut]


class ScrapeRequest(BaseModel):
    query: Query
    pincode: Pincode
    force: bool = False  # true = ignore the 6-hour cache


class ScrapeJob(BaseModel):
    run_id: str
    query: str
    pincode: str
    status: Literal["running", "done", "error"]
    messages: list[str]
    cached: bool = False


class HistoryPoint(BaseModel):
    store: str
    product_id: int
    price: float
    mrp: float
    discount_pct: float
    unit_price: float | None
    in_stock: bool
    pincode: str
    scraped_at: datetime


class PriceStats(BaseModel):
    store: str
    lowest: float
    highest: float
    average: float
    current: float


class HistoryResponse(BaseModel):
    product: ProductOut
    counterpart: ProductOut | None
    match_score: float | None
    history: list[HistoryPoint]
    stats: list[PriceStats]


class BasketItem(BaseModel):
    match_id: int | None = None
    product_ids: list[int] = []
    qty: int = Field(1, ge=1, le=99)

    @model_validator(mode="after")
    def needs_a_product(self) -> "BasketItem":
        if self.match_id is None and not self.product_ids:
            raise ValueError("give match_id or product_ids")
        return self


class BasketRequest(BaseModel):
    items: list[BasketItem] = Field(min_length=1, max_length=100)
    pincode: Pincode


class BasketLine(BaseModel):
    name: str
    qty: int
    bigbasket: float | None  # line total (price x qty); None = not available there
    jiomart: float | None
    best_store: StoreKey | None


class BasketResponse(BaseModel):
    lines: list[BasketLine]
    totals: dict[StoreKey, float]
    missing: dict[StoreKey, int]  # items a store doesn't have (its total is incomplete)
    best_split: dict[StoreKey, list[str]]
    best_split_total: float
    saving_vs_best_single: float | None  # vs the cheapest store that has every item
    saving_vs_worst_single: float | None
