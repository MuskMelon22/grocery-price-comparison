"""POST /basket/compare: basket total per store and the cheapest split."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PriceSnapshot, Product, ProductMatch
from app.schemas import BasketItem, BasketRequest, BasketResponse
from app.services.search import STORE_KEYS

router = APIRouter(tags=["basket"])


def _price(db: Session, product: Product, pincode: str) -> float | None:
    """Latest price for this pincode (falls back to any pincode if never scraped there)."""
    base = select(PriceSnapshot.price).where(PriceSnapshot.product_id == product.id)
    newest = PriceSnapshot.scraped_at.desc()
    return (db.scalar(base.where(PriceSnapshot.pincode == pincode).order_by(newest).limit(1))
            or db.scalar(base.order_by(newest).limit(1)))


def _products(db: Session, item: BasketItem) -> dict[str, Product]:
    """Store key -> product for one basket item (a match gives both stores)."""
    ids = list(item.product_ids)
    if item.match_id is not None:
        m = db.get(ProductMatch, item.match_id)
        if m is None:
            raise HTTPException(404, f"Match {item.match_id} not found")
        ids += [m.bigbasket_product_id, m.jiomart_product_id]
    else:  # a single product may still have a match on the other store
        for m in db.scalars(select(ProductMatch).where(or_(
                ProductMatch.bigbasket_product_id.in_(ids), ProductMatch.jiomart_product_id.in_(ids)))):
            ids += [m.bigbasket_product_id, m.jiomart_product_id]
    out: dict[str, Product] = {}
    for pid in ids:
        p = db.get(Product, pid)
        if p is None:
            raise HTTPException(404, f"Product {pid} not found")
        out.setdefault(STORE_KEYS[p.store.name], p)
    return out


@router.post("/basket/compare", response_model=BasketResponse)
def compare(req: BasketRequest, db: Session = Depends(get_db)) -> dict:
    keys = list(STORE_KEYS.values())
    lines, totals = [], dict.fromkeys(keys, 0.0)
    missing, split = dict.fromkeys(keys, 0), {k: [] for k in keys}
    for item in req.items:
        products = _products(db, item)
        line = {k: None for k in keys}
        for k, p in products.items():
            price = _price(db, p, req.pincode)
            line[k] = round(price * item.qty, 2) if price is not None else None
        available = {k: v for k, v in line.items() if v is not None}
        best = min(available, key=available.get) if available else None
        name = next(iter(products.values())).name
        for k in keys:
            if line[k] is None:
                missing[k] += 1
            else:
                totals[k] += line[k]
        if best:
            split[best].append(name)
        lines.append({"name": name, "qty": item.qty, **line, "best_store": best})

    split_total = round(sum(min(v for k, v in ln.items() if k in keys and v is not None)
                            for ln in lines if ln["best_store"]), 2)
    complete = [totals[k] for k in keys if missing[k] == 0]  # only stores that have every item
    return {
        "lines": lines, "totals": {k: round(v, 2) for k, v in totals.items()}, "missing": missing,
        "best_split": split, "best_split_total": split_total,
        "saving_vs_best_single": round(min(complete) - split_total, 2) if complete else None,
        "saving_vs_worst_single": round(max(complete) - split_total, 2) if complete else None,
    }
