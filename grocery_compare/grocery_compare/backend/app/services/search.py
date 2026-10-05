"""Scrape both stores, save snapshots, match products, and build search results from the DB."""
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import PriceSnapshot, Product, ProductMatch, ScrapeRun, Store, utcnow
from app.scrapers.base import ScrapeResult
from app.scrapers.bigbasket import BigBasketScraper
from app.scrapers.jiomart import JioMartScraper
from app.services import matcher
from app.services.normalizer import category_for, discount_pct, extract_brand, parse_pack, unit_price

log = logging.getLogger(__name__)
SCRAPERS = (BigBasketScraper, JioMartScraper)
STORE_KEYS = {"BigBasket": "bigbasket", "JioMart": "jiomart"}


def clean_query(query: str) -> str:
    return " ".join(query.lower().split())


# --- scraping + saving -------------------------------------------------------
def scrape_and_store(query: str, pincode: str, progress: Callable[[str], None] = lambda _: None) -> None:
    """Live-scrape both stores in parallel threads, then save and match. Never raises for store errors."""
    query = clean_query(query)
    progress("Searching BigBasket and JioMart...")

    def run(cls) -> tuple[ScrapeResult, datetime]:
        started = utcnow()
        result = cls().search(query, pincode)
        progress(f"{result.store}: {result.status}, {len(result.products)} products")
        return result, started

    with ThreadPoolExecutor(len(SCRAPERS)) as pool:
        results = list(pool.map(run, SCRAPERS))
    progress("Matching products...")
    with SessionLocal() as db:
        saved = {r.store: _save(db, r, started, query, pincode) for r, started in results}
        _match(db, saved.get("BigBasket", []), saved.get("JioMart", []))
        db.commit()


def _save(db: Session, result: ScrapeResult, started: datetime, query: str, pincode: str) -> list[Product]:
    store = db.scalar(select(Store).filter_by(name=result.store))
    run = ScrapeRun(store=store, query=query, pincode=pincode, started_at=started,
                    finished_at=utcnow(), status=result.status, items_found=len(result.products),
                    error_message="; ".join(result.warnings) or None)
    db.add(run)
    products = []
    for raw in result.products:
        product = db.scalar(select(Product).filter_by(store_product_url=raw.url))
        if product is None:
            product = Product(store=store, store_product_url=raw.url, category=category_for(query))
            db.add(product)
        # re-derived every time so normalizer fixes apply to existing rows too
        product.pack_qty_base, product.pack_kind = parse_pack(raw.name)
        product.name, product.brand = raw.name, extract_brand(raw.name)
        product.image_url = raw.image_url or product.image_url
        db.add(PriceSnapshot(product=product, scrape_run=run, pincode=pincode, price=raw.price,
                             mrp=raw.mrp, discount_pct=discount_pct(raw.price, raw.mrp),
                             in_stock=raw.in_stock, scraped_at=run.finished_at,
                             unit_price=unit_price(raw.price, product.pack_qty_base, product.pack_kind)))
        products.append(product)
    db.flush()  # assign ids
    return products


def _match(db: Session, bigbasket: list[Product], jiomart: list[Product]) -> None:
    if not bigbasket or not jiomart:
        return  # keep matches from earlier runs (e.g. BigBasket blocked this time)
    items = lambda ps: [matcher.Item(p.id, p.name, p.brand, p.pack_kind, p.pack_qty_base) for p in ps]  # noqa: E731
    for bb_id, jm_id, score in matcher.match(items(bigbasket), items(jiomart)):
        for old in db.scalars(select(ProductMatch).where(or_(
                ProductMatch.bigbasket_product_id == bb_id, ProductMatch.jiomart_product_id == jm_id))):
            db.delete(old)
        db.flush()
        db.add(ProductMatch(bigbasket_product_id=bb_id, jiomart_product_id=jm_id, match_score=score))


# --- reading results -----------------------------------------------------------
def _latest_run(db: Session, store: str, query: str, pincode: str, ok_only: bool) -> ScrapeRun | None:
    stmt = (select(ScrapeRun).join(Store).where(Store.name == store, ScrapeRun.query == query,
                                               ScrapeRun.pincode == pincode))
    if ok_only:
        stmt = stmt.where(ScrapeRun.status.in_(("success", "partial")))
    return db.scalar(stmt.order_by(ScrapeRun.id.desc()).limit(1))


def is_fresh(db: Session, query: str, pincode: str) -> bool:
    """Cache hit if every store was tried (and didn't simply fail) within CACHE_HOURS.

    A recent `blocked` run counts as fresh on purpose: retrying a store that just blocked us
    would only hammer it.
    """
    cutoff = utcnow() - timedelta(hours=settings.cache_hours)
    for store in STORE_KEYS:
        run = _latest_run(db, store, clean_query(query), pincode, ok_only=False)
        if run is None or run.started_at < cutoff or run.status == "failed":
            return False
    return True


def product_dict(p: Product, s: PriceSnapshot) -> dict:
    return {
        "id": p.id, "store": p.store.name, "name": p.name, "brand": p.brand, "image_url": p.image_url,
        "url": p.store_product_url, "pack_qty_base": p.pack_qty_base, "pack_kind": p.pack_kind,
        "category": p.category, "price": s.price, "mrp": s.mrp, "discount_pct": s.discount_pct,
        "unit_price": s.unit_price, "in_stock": s.in_stock, "scraped_at": s.scraped_at,
    }


def _warnings(db: Session, query: str, pincode: str) -> tuple[list[str], datetime | None]:
    warnings, newest = [], None
    for store in STORE_KEYS:
        last = _latest_run(db, store, query, pincode, ok_only=False)
        good = _latest_run(db, store, query, pincode, ok_only=True)
        if good and (newest is None or good.finished_at > newest):
            newest = good.finished_at
        if last is None or last.status in ("success", "partial"):
            if last and last.status == "partial" and last.error_message:
                warnings.append(last.error_message)
            continue
        verb = "blocked the request" if last.status == "blocked" else "failed"
        if good:
            warnings.append(f"{store} {verb}; showing its prices from {good.finished_at:%d %b %H:%M} UTC.")
        else:
            other = next(s for s in STORE_KEYS if s != store)
            warnings.append(f"{store} {verb}, showing {other} only.")
    return warnings, newest


def get_results(db: Session, query: str, pincode: str) -> dict:
    """Latest good scrape per store for this query+pincode, split into matched / only-on-X rows."""
    query = clean_query(query)
    per_store: dict[str, dict[int, dict]] = {}
    for store, key in STORE_KEYS.items():
        run = _latest_run(db, store, query, pincode, ok_only=True)
        snaps = db.scalars(select(PriceSnapshot).where(PriceSnapshot.scrape_run_id == run.id)).all() if run else []
        per_store[key] = {s.product_id: product_dict(s.product, s) for s in snaps}

    bb, jm = per_store["bigbasket"], per_store["jiomart"]
    matches = db.scalars(select(ProductMatch).where(
        ProductMatch.bigbasket_product_id.in_(bb), ProductMatch.jiomart_product_id.in_(jm))).all()
    matched = [match_row(m, bb[m.bigbasket_product_id], jm[m.jiomart_product_id]) for m in matches]
    used_bb = {m.bigbasket_product_id for m in matches}
    used_jm = {m.jiomart_product_id for m in matches}
    warnings, scraped_at = _warnings(db, query, pincode)
    return {
        "query": query, "pincode": pincode, "scraped_at": scraped_at, "warnings": warnings,
        "matched": matched,
        "only_bigbasket": [p for pid, p in bb.items() if pid not in used_bb],
        "only_jiomart": [p for pid, p in jm.items() if pid not in used_jm],
    }


def match_row(m: ProductMatch, bb: dict, jm: dict) -> dict:
    cheap, dear = (bb, jm) if bb["price"] <= jm["price"] else (jm, bb)
    saving = round(dear["price"] - cheap["price"], 2)
    return {
        "match_id": m.id, "match_score": m.match_score, "bigbasket": bb, "jiomart": jm,
        "cheaper": None if saving == 0 else STORE_KEYS[cheap["store"]],
        "saving_abs": saving, "saving_pct": round(saving / dear["price"] * 100, 1) if dear["price"] else 0,
    }


def apply_filters(results: dict, sort: str = "cheapest", store: str | None = None,
                  min_price: float | None = None, max_price: float | None = None) -> dict:
    """Server-side sort/filter for API users (the frontend also filters client-side)."""
    def price_ok(p: float) -> bool:
        return (min_price is None or p >= min_price) and (max_price is None or p <= max_price)

    def best(row: dict) -> float:
        return min(row["bigbasket"]["price"], row["jiomart"]["price"])

    keys = {
        "cheapest": (lambda r: best(r), lambda p: p["price"]),
        "saving": (lambda r: -r["saving_abs"], lambda p: p["price"]),
        "unit_price": (lambda r: r["bigbasket"]["unit_price"] or 1e9, lambda p: p["unit_price"] or 1e9),
        "name": (lambda r: r["bigbasket"]["name"].lower(), lambda p: p["name"].lower()),
    }
    row_key, prod_key = keys.get(sort, keys["cheapest"])
    out = dict(results)
    out["matched"] = sorted((r for r in results["matched"] if price_ok(best(r))), key=row_key)
    for key in ("bigbasket", "jiomart"):
        lst = [] if store and store != key else results[f"only_{key}"]
        out[f"only_{key}"] = sorted((p for p in lst if price_ok(p["price"])), key=prod_key)
    return out
