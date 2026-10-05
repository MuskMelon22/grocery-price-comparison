"""/products/{id} and /products/{id}/history."""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PriceSnapshot, Product, ProductMatch, utcnow
from app.schemas import HistoryResponse, ProductOut
from app.services.search import product_dict

router = APIRouter(tags=["products"])


def _latest(db: Session, product: Product) -> dict:
    snap = db.scalar(select(PriceSnapshot).where(PriceSnapshot.product_id == product.id)
                     .order_by(PriceSnapshot.scraped_at.desc()).limit(1))
    return product_dict(product, snap)


def _get(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    return product


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)) -> dict:
    return _latest(db, _get(db, product_id))


@router.get("/products/{product_id}/history", response_model=HistoryResponse)
def history(product_id: int, days: Annotated[int, Query(ge=1, le=365)] = 30,
            db: Session = Depends(get_db)) -> dict:
    """Price history of this product and of its matched product on the other store."""
    product = _get(db, product_id)
    match = db.scalar(select(ProductMatch).where(or_(
        ProductMatch.bigbasket_product_id == product_id, ProductMatch.jiomart_product_id == product_id)))
    other = None
    if match:
        other_id = match.jiomart_product_id if match.bigbasket_product_id == product_id else match.bigbasket_product_id
        other = db.get(Product, other_id)

    ids = [product.id] + ([other.id] if other else [])
    snaps = db.scalars(select(PriceSnapshot).where(
        PriceSnapshot.product_id.in_(ids), PriceSnapshot.scraped_at >= utcnow() - timedelta(days=days))
        .order_by(PriceSnapshot.scraped_at)).all()
    points = [{"store": s.product.store.name, "product_id": s.product_id, "price": s.price, "mrp": s.mrp,
               "discount_pct": s.discount_pct, "unit_price": s.unit_price, "in_stock": s.in_stock,
               "pincode": s.pincode, "scraped_at": s.scraped_at} for s in snaps]

    stats = []
    for p in filter(None, (product, other)):
        prices = [pt["price"] for pt in points if pt["product_id"] == p.id]
        if prices:
            stats.append({"store": p.store.name, "lowest": min(prices), "highest": max(prices),
                          "average": round(sum(prices) / len(prices), 2), "current": prices[-1]})
    return {"product": _latest(db, product), "counterpart": _latest(db, other) if other else None,
            "match_score": match.match_score if match else None, "history": points, "stats": stats}
