"""API smoke tests on a seeded temp DB (no live scraping)."""
import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import PriceSnapshot, Product, ProductMatch, ScrapeRun, Store, utcnow


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # runs lifespan -> init_db
        seed()
        yield c


def seed() -> None:
    with SessionLocal() as db:
        bb, jm = (db.query(Store).filter_by(name=n).one() for n in ("BigBasket", "JioMart"))
        now = utcnow()
        runs = {s: ScrapeRun(store=s, query="milk", pincode="400001", started_at=now, finished_at=now,
                             status="success", items_found=2) for s in (bb, jm)}
        db.add_all(runs.values())

        def prod(store, slug, name, price, mrp, qty=500):
            p = Product(store=store, store_product_url=f"https://x/{slug}", name=name, brand="Amul",
                        pack_qty_base=qty, pack_kind="volume", category="dairy")
            db.add(PriceSnapshot(product=p, scrape_run=runs[store], pincode="400001", price=price, mrp=mrp,
                                 discount_pct=round((mrp - price) / mrp * 100, 1), unit_price=price / qty * 100,
                                 scraped_at=now))
            return p

        a = prod(bb, "bb1", "Amul Taaza Milk 500 ml", 28, 30)
        b = prod(jm, "jm1", "Amul Taaza Toned Milk 500 ml", 27, 29)
        prod(bb, "bb2", "Amul Gold Milk 1 L", 68, 70, qty=1000)
        db.flush()
        db.add(ProductMatch(bigbasket_product_id=a.id, jiomart_product_id=b.id, match_score=0.9))
        db.commit()


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_search_uses_cache(client):
    r = client.get("/api/search", params={"q": "Milk", "pincode": "400001"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["matched"]) == 1 and data["matched"][0]["cheaper"] == "jiomart"
    assert data["matched"][0]["saving_abs"] == 1
    assert [p["name"] for p in data["only_bigbasket"]] == ["Amul Gold Milk 1 L"]
    assert client.get("/api/search", params={"q": "milk", "store": "jiomart"}).json()["only_bigbasket"] == []


@pytest.mark.parametrize("params", [{"q": "m"}, {"q": "milk", "pincode": "12345"}, {"q": "milk", "sort": "x"}])
def test_search_validation(client, params):
    assert client.get("/api/search", params=params).status_code == 422


def test_scrape_job_cached(client):
    job = client.post("/api/scrape", json={"query": "milk", "pincode": "400001"}).json()
    assert job["status"] == "done" and job["cached"]
    assert client.get(f"/api/scrape/{job['run_id']}").json()["run_id"] == job["run_id"]
    assert client.get("/api/scrape/nope").status_code == 404


def test_history_and_product(client):
    match_row = client.get("/api/search", params={"q": "milk"}).json()["matched"][0]
    pid = match_row["bigbasket"]["id"]
    h = client.get(f"/api/products/{pid}/history").json()
    assert h["counterpart"]["store"] == "JioMart" and len(h["history"]) == 2
    assert {s["store"] for s in h["stats"]} == {"BigBasket", "JioMart"}
    assert client.get("/api/products/99999").status_code == 404


def test_basket(client):
    res = client.get("/api/search", params={"q": "milk"}).json()
    body = {"pincode": "400001", "items": [
        {"match_id": res["matched"][0]["match_id"], "qty": 2},
        {"product_ids": [res["only_bigbasket"][0]["id"]], "qty": 1},
    ]}
    b = client.post("/api/basket/compare", json=body).json()
    assert b["totals"] == {"bigbasket": 124.0, "jiomart": 54.0}
    assert b["missing"] == {"bigbasket": 0, "jiomart": 1}
    assert b["best_split_total"] == 122.0  # 2x27 on JioMart + 68 on BigBasket
    assert b["saving_vs_best_single"] == 2.0
    assert client.post("/api/basket/compare", json={"pincode": "400001", "items": [{"qty": 1}]}).status_code == 422


def test_analytics_and_csv(client):
    s = client.get("/api/analytics/summary").json()
    assert s["matched_pairs"] == 1 and s["win_rate"]["JioMart"] == 100.0
    assert s["top_gaps"][0]["gap"] == 1
    assert client.get("/api/analytics/category-comparison").json()[0]["category"] == "dairy"
    assert len(client.get("/api/analytics/discounts").json()["BigBasket"]) == 2
    csv = client.get("/api/export/csv", params={"q": "milk"})
    assert csv.headers["content-type"].startswith("text/csv") and "Amul Gold" in csv.text
