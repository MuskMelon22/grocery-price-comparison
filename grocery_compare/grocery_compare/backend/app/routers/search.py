"""/search and /export/csv."""
from typing import Annotated, Literal

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SearchResponse, StoreKey
from app.services.search import apply_filters, get_results, is_fresh, scrape_and_store

router = APIRouter(tags=["search"])

Q = Annotated[str, Query(min_length=2, max_length=60)]
PIN = Annotated[str, Query(pattern=r"^\d{6}$")]


@router.get("/search", response_model=SearchResponse)
def search(
    q: Q,
    pincode: PIN = "400001",
    sort: Literal["cheapest", "saving", "unit_price", "name"] = "cheapest",
    store: StoreKey | None = None,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    fresh: bool = False,
    cached: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    """Cached results if under CACHE_HOURS old, otherwise a live scrape (10-60 s).

    `fresh=true` forces a live scrape; `cached=true` never scrapes (the frontend uses it after
    running POST /scrape + polling, so a failed store isn't retried straight away).
    """
    if not cached and (fresh or not is_fresh(db, q, pincode)):
        scrape_and_store(q, pincode)
    return apply_filters(get_results(db, q, pincode), sort, store, min_price, max_price)


@router.get("/export/csv")
def export_csv(q: Q, pincode: PIN = "400001", db: Session = Depends(get_db)) -> Response:
    """Download the stored results of a search (no new scrape) as CSV."""
    res = get_results(db, q, pincode)
    rows = []
    for r in res["matched"]:
        bb, jm = r["bigbasket"], r["jiomart"]
        rows.append({"product": bb["name"], "pack": bb["pack_qty_base"], "bigbasket_price": bb["price"],
                     "jiomart_price": jm["price"], "cheaper": r["cheaper"], "saving": r["saving_abs"],
                     "bigbasket_unit_price": bb["unit_price"], "jiomart_unit_price": jm["unit_price"],
                     "bigbasket_url": bb["url"], "jiomart_url": jm["url"]})
    for key in ("bigbasket", "jiomart"):
        for p in res[f"only_{key}"]:
            rows.append({"product": p["name"], "pack": p["pack_qty_base"], f"{key}_price": p["price"],
                         "cheaper": key, f"{key}_unit_price": p["unit_price"], f"{key}_url": p["url"]})
    csv = pd.DataFrame(rows).to_csv(index=False)
    name = "_".join(q.split())[:40]
    return Response(csv, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="grocery_{name}_{pincode}.csv"'})
