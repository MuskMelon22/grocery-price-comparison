"""/analytics/*: data for the dashboard charts."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)) -> dict:
    return analytics.summary(db)


@router.get("/category-comparison")
def category_comparison(db: Session = Depends(get_db)) -> list[dict]:
    df = analytics.snapshots_df(db)
    return [] if df.empty else analytics.category_comparison(analytics.latest_df(df))


@router.get("/discounts")
def discounts(db: Session = Depends(get_db)) -> dict[str, list[float]]:
    df = analytics.snapshots_df(db)
    return {s: [] for s in analytics.STORES} if df.empty else analytics.discounts(analytics.latest_df(df))
