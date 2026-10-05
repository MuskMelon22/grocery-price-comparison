"""Warm the database by asking the running API to scrape the popular queries.

Usage (API must be running on :8000):
    python seed_scrape.py                    # all POPULAR_QUERIES
    python seed_scrape.py milk atta          # just these
    python seed_scrape.py --pincode 560001 --pause 30
"""
import argparse
import sys
import time

import requests

from app.config import settings


def scrape(api: str, query: str, pincode: str) -> dict:
    r = requests.post(f"{api}/api/scrape", json={"query": query, "pincode": pincode}, timeout=10)
    r.raise_for_status()
    job, seen = r.json(), 0
    while job["status"] == "running":
        time.sleep(2)
        job = requests.get(f"{api}/api/scrape/{job['run_id']}", timeout=10).json()
        for msg in job["messages"][seen:]:
            print(f"    {msg}")
        seen = len(job["messages"])
    return job


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queries", nargs="*", help="defaults to POPULAR_QUERIES from config")
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--pincode", default=settings.default_pincode)
    ap.add_argument("--pause", type=int, default=20, help="seconds between queries (be polite)")
    args = ap.parse_args()
    queries = args.queries or settings.popular_queries

    try:
        requests.get(f"{args.api}/api/health", timeout=5).raise_for_status()
    except requests.RequestException as e:
        print(f"API not reachable at {args.api} ({e}). Start it with: uvicorn app.main:app --port 8000")
        return 1

    failed = 0
    for i, q in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] {q}")
        try:
            job = scrape(args.api, q, args.pincode)
        except requests.RequestException as e:
            print(f"    request failed: {e}")
            failed += 1
            continue
        tag = "cached" if job.get("cached") else job["status"]
        print(f"    -> {tag}")
        failed += job["status"] == "error"
        if i < len(queries) and not job.get("cached"):
            time.sleep(args.pause)
    print(f"Done: {len(queries) - failed}/{len(queries)} ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
