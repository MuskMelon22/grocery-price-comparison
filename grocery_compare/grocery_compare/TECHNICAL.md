# GroceryCompare: technical reference

> New here? Start with [README.md](README.md). This page is the detailed version.

Compare grocery prices between **BigBasket** and **JioMart** for your pincode. Real Selenium scraping,
cross-store product matching, price-per-100 g/ml normalisation, price history, a basket optimiser and analytics.

> Educational project. Scraping may violate the stores' terms of service, so it runs at low volume, is not meant
> for commercial use, and the data is not redistributed. Not affiliated with BigBasket or JioMart.

## Stack

| Layer | Tech |
|---|---|
| Scraping | Selenium (real Chrome, persistent profile) + BeautifulSoup/lxml |
| API | FastAPI, Pydantic, SQLAlchemy 2 (SQLite by default, any `DATABASE_URL`) |
| Jobs | APScheduler (background re-scrape), in-process scrape jobs with polling |
| Analytics | Pandas + NumPy |
| Frontend | React 19 + Vite + TypeScript, Tailwind 4, TanStack Query, Plotly.js |
| Seeding | `requests` script against the API |

## Run it (Windows)

Needs Python 3.11+, Node 20+ and Google Chrome.

**1. Backend** (terminal 1)
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

**2. Frontend** (terminal 2)
```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```
Open http://localhost:5173

**3. Seed data (optional, terminal 3, backend venv active, API running)**
```powershell
cd backend
python seed_scrape.py              # all 15 popular queries, 20 s apart
python seed_scrape.py milk atta    # or just a few
```

**Tests**
```powershell
cd backend
pytest
```

macOS/Linux: use `source venv/bin/activate` and `cp` instead of `copy`.

## How it works

1. **Search.** The frontend POSTs `/api/scrape`. If every store has a run for that query + pincode younger than `CACHE_HOURS`,
   the job finishes instantly from the DB. Otherwise a background thread opens Chrome, sets the pincode, scrapes
   each store and reports progress, which the UI polls.
2. **Normalise.** Pack sizes like `500 g`, `1 kg`, `6 x 200 ml` and `pack of 12` become base units, giving a unit price per 100 g, 100 ml or item.
3. **Match.** Products across stores are paired when the pack kind matches, the quantity is within 2%, the brand agrees and the
   name-similarity score is at least 0.55 (greedy one-to-one).
4. **Store.** Every scrape adds a price snapshot, so history accumulates over time.
5. **Scheduler.** APScheduler re-scrapes `POPULAR_QUERIES` every `SCRAPE_INTERVAL_HOURS`, one query at a time with
   a pause between queries, so the product-page price charts fill in. Disable it with `ENABLE_SCHEDULER=false`.

## Pages

- **Home**: search, pincode, popular searches
- **Search results**: side-by-side matched products, "only on X" sections, sort and filters, refresh, CSV export
- **Product**: both stores' listings, 7/30/90-day price and discount history, price stats
- **Basket**: per-store totals, best split across stores and savings, CSV export
- **Analytics**: win rate, category unit-price comparison, discount distribution, biggest gaps, trend, volatility

## API

All routes are under `/api`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness |
| GET | `/search?q=&pincode=&sort=&store=&min_price=&max_price=&fresh=&cached=` | matched + unmatched results (scrapes if stale unless `cached=true`) |
| POST | `/scrape` `{query, pincode, force}` | start a background scrape job |
| GET | `/scrape/{run_id}` | job status + progress messages |
| GET | `/products/{id}` | latest snapshot |
| GET | `/products/{id}/history?days=30` | history for product + matched counterpart, with stats |
| POST | `/basket/compare` | basket totals per store, best split, savings |
| GET | `/analytics/summary` | all dashboard metrics |
| GET | `/analytics/category-comparison` | median unit price per category per store |
| GET | `/analytics/discounts` | discount % lists per store |
| GET | `/export/csv?q=&pincode=` | search results as CSV |

## Layout

```
backend/
  app/
    scrapers/   browser.py (Chrome setup), base.py, bigbasket.py, jiomart.py
    services/   normalizer, matcher, search (scrape+store+cache), analytics, scheduler
    routers/    search, scrape, products, basket, analytics
    config.py  database.py  models.py  schemas.py  main.py
  tests/        normalizer, matcher, API tests (pytest)
  seed_scrape.py
frontend/src/
  api/client.ts  store.ts  format.ts  types.ts
  components/    Navbar, SearchBar, CompareRow, PincodeModal, Plot, ui
  pages/         Home, SearchResults, ProductDetail, Basket, Analytics, About
```

## Configuration (`backend/.env`)

See `backend/.env.example`. Key settings: `SCRAPE_HEADLESS`, `SCRAPE_TIMEOUT`, `DEFAULT_PINCODE`, `CACHE_HOURS`,
`BLOCK_COOLDOWN_MINUTES`, `DATABASE_URL`, `ENABLE_SCHEDULER`, `SCRAPE_INTERVAL_HOURS`, `POPULAR_QUERIES`.
Frontend: `VITE_API_URL` (default `http://localhost:8000`).

## Known limitations

- **BigBasket blocks automated browsers (Akamai).** The app does **not** try to bypass it: no stealth plugins,
  proxy rotation or fingerprint spoofing. When a block page or 403 is detected, the run is recorded as `blocked`,
  the store is skipped for `BLOCK_COOLDOWN_MINUTES`, and the UI says *"BigBasket blocked the request, showing JioMart only."*
  In that case, matching, the basket split and store-vs-store analytics only have JioMart data.
- **Selectors break.** Store markup changes often. The parsers are layout-agnostic (they look for product links plus
  price text rather than CSS class names), and failing pages are saved to `backend/debug_html/` for inspection.
- **Prices vary by pincode** and change often. Results are a cached snapshot (see the "prices from" timestamp).
- **Matching is heuristic.** Different variants can occasionally pair, or the same product fail to pair.
- **Scraping is slow** (tens of seconds per query), which is why results are cached and scraping runs in the background.
- **Single process.** Scrape jobs live in memory. Run one uvicorn worker. For multiple workers, move jobs to a
  queue (RQ/Celery) and the DB to PostgreSQL.
- **No Docker.** Selenium here drives a visible, persistent Chrome profile (headless gets blocked more), which doesn't fit a
  container well, so docker-compose was left out.
