"""Dashboard statistics with Pandas + NumPy (plan section 10)."""
import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import PriceSnapshot, Product, ProductMatch, ScrapeRun, Store

STORES = ("BigBasket", "JioMart")


def snapshots_df(db: Session) -> pd.DataFrame:
    """Every price snapshot joined with its product and store, one row each."""
    stmt = (select(PriceSnapshot.product_id, PriceSnapshot.price, PriceSnapshot.mrp,
                   PriceSnapshot.discount_pct, PriceSnapshot.unit_price, PriceSnapshot.scraped_at,
                   Product.name, Product.category, Store.name.label("store"))
            .join(Product, PriceSnapshot.product_id == Product.id).join(Store, Product.store_id == Store.id))
    return pd.DataFrame(db.execute(stmt).all(), columns=[
        "product_id", "price", "mrp", "discount_pct", "unit_price", "scraped_at", "name", "category", "store"])


def latest_df(df: pd.DataFrame) -> pd.DataFrame:
    """Only the newest snapshot of each product."""
    return df.sort_values("scraped_at").groupby("product_id").tail(1).set_index("product_id")


def _pairs(db: Session, latest: pd.DataFrame) -> pd.DataFrame:
    """Matched products with both current prices."""
    m = pd.DataFrame(db.execute(select(ProductMatch.bigbasket_product_id, ProductMatch.jiomart_product_id)).all(),
                     columns=["bb", "jm"])
    m = m[m.bb.isin(latest.index) & m.jm.isin(latest.index)]
    return pd.DataFrame({
        "name": latest.loc[m.bb, "name"].to_numpy(),
        "bb_price": latest.loc[m.bb, "price"].to_numpy(),
        "jm_price": latest.loc[m.jm, "price"].to_numpy(),
        "bb_id": m.bb.to_numpy(), "jm_id": m.jm.to_numpy(),
    })


def category_comparison(latest: pd.DataFrame) -> list[dict]:
    """Median unit price (₹ per 100 g/ml or item) per category and store."""
    t = latest.dropna(subset=["unit_price"]).pivot_table(
        index="category", columns="store", values="unit_price", aggfunc="median")
    t = t.reindex(columns=list(STORES)).round(2)
    return [{"category": cat, **{s: (None if pd.isna(row[s]) else float(row[s])) for s in STORES}}
            for cat, row in t.iterrows()]


def discounts(latest: pd.DataFrame) -> dict[str, list[float]]:
    return {s: latest.loc[latest.store == s, "discount_pct"].round(1).tolist() for s in STORES}


def summary(db: Session) -> dict:
    df = snapshots_df(db)
    last = dict(db.execute(select(Store.name, func.max(ScrapeRun.finished_at))
                           .join(ScrapeRun, ScrapeRun.store_id == Store.id, isouter=True).group_by(Store.name)).all())
    base = {"products_tracked": 0, "snapshots": len(df), "last_scrape": last, "matched_pairs": 0,
            "win_rate": {s: 0.0 for s in STORES}, "ties_pct": 0.0, "avg_price_diff_pct": None,
            "median_price_diff_pct": None, "avg_discount": {s: None for s in STORES},
            "category_comparison": [], "top_gaps": [], "volatility": {s: None for s in STORES}, "trend": []}
    if df.empty:
        return base

    latest = latest_df(df)
    pairs = _pairs(db, latest)
    base["products_tracked"] = len(latest)
    base["matched_pairs"] = len(pairs)
    if len(pairs):
        bb, jm = pairs.bb_price.to_numpy(), pairs.jm_price.to_numpy()
        diff_pct = np.abs(bb - jm) / np.maximum(bb, jm) * 100  # how much the dearer store overcharges
        base["win_rate"] = {"BigBasket": round(float(np.mean(bb < jm) * 100), 1),
                            "JioMart": round(float(np.mean(jm < bb) * 100), 1)}
        base["ties_pct"] = round(float(np.mean(bb == jm) * 100), 1)
        base["avg_price_diff_pct"] = round(float(np.mean(diff_pct)), 1)
        base["median_price_diff_pct"] = round(float(np.median(diff_pct)), 1)
        pairs["gap"] = np.abs(bb - jm)
        pairs["cheaper"] = np.where(bb < jm, "BigBasket", np.where(jm < bb, "JioMart", "tie"))
        top = pairs.nlargest(10, "gap")
        base["top_gaps"] = [{"name": r.name, "bigbasket": r.bb_price, "jiomart": r.jm_price, "gap": round(r.gap, 2),
                             "cheaper": r.cheaper, "product_id": int(r.bb_id)} for r in top.itertuples()]

    base["avg_discount"] = {s: (round(float(v), 1) if pd.notna(v) else None)
                            for s, v in latest.groupby("store").discount_pct.mean().reindex(STORES).items()}
    base["category_comparison"] = category_comparison(latest)
    # volatility: std-dev of each product's price over time (needs 2+ snapshots), averaged per store
    std = df.groupby(["store", "product_id"]).price.std().dropna()
    base["volatility"] = {s: (round(float(v), 2) if pd.notna(v) else None)
                          for s, v in std.groupby("store").mean().reindex(STORES).items()}
    # trend: daily median unit price per store
    daily = (df.dropna(subset=["unit_price"]).assign(day=df.scraped_at.dt.strftime("%Y-%m-%d"))
             .groupby(["day", "store"]).unit_price.median().round(2).reset_index())
    base["trend"] = daily.to_dict("records")
    return base
