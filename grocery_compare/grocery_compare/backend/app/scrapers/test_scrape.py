"""Phase 1 check: scrape both stores from the command line.

    python -m app.scrapers.test_scrape "milk" 400001
    python -m app.scrapers.test_scrape "atta" 400001 --store jiomart
"""
import argparse
from dataclasses import asdict

import pandas as pd

from app.scrapers.bigbasket import BigBasketScraper
from app.scrapers.jiomart import JioMartScraper
from app.utils.logging import setup_logging

SCRAPERS = {"bigbasket": BigBasketScraper, "jiomart": JioMartScraper}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("pincode", nargs="?", default="400001")
    ap.add_argument("--store", choices=SCRAPERS, help="scrape only this store")
    ap.add_argument("--save", action="store_true", help="save to the DB, match, and print the pairs")
    args = ap.parse_args()
    setup_logging()

    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 55)
    if args.save:
        return save_and_show(args.query, args.pincode)
    for key, cls in SCRAPERS.items():
        if args.store and key != args.store:
            continue
        result = cls().search(args.query, args.pincode)
        print(f"\n=== {result.store}: {result.status}, {len(result.products)} products ===")
        for w in result.warnings:
            print("  warning:", w)
        if result.products:
            df = pd.DataFrame([asdict(p) for p in result.products])
            print(df[["name", "price", "mrp", "raw_qty_text", "in_stock", "url"]].to_string(index=False))


def save_and_show(query: str, pincode: str) -> None:
    """Phase 2 check: scrape -> DB -> matcher, then print what the API would return."""
    from app.database import SessionLocal, init_db
    from app.services.search import get_results, scrape_and_store

    init_db()
    scrape_and_store(query, pincode, progress=print)
    with SessionLocal() as db:
        res = get_results(db, query, pincode)
    for w in res["warnings"]:
        print("  warning:", w)
    print(f"\n=== {len(res['matched'])} matched pairs ===")
    if res["matched"]:
        print(pd.DataFrame([{
            "bigbasket": r["bigbasket"]["name"], "bb_price": r["bigbasket"]["price"],
            "jiomart": r["jiomart"]["name"], "jm_price": r["jiomart"]["price"],
            "unit_price_bb": r["bigbasket"]["unit_price"], "unit_price_jm": r["jiomart"]["unit_price"],
            "cheaper": r["cheaper"], "score": r["match_score"],
        } for r in res["matched"]]).to_string(index=False))
    for key in ("bigbasket", "jiomart"):
        rows = res[f"only_{key}"]
        print(f"\n=== only on {key}: {len(rows)} ===")
        if rows:
            print(pd.DataFrame(rows)[["name", "price", "pack_qty_base", "pack_kind", "unit_price"]]
                  .to_string(index=False))


if __name__ == "__main__":
    main()
