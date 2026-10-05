"""FastAPI app: CORS, routers under /api, DB init and the scheduler.

Run:  uvicorn app.main:app --reload --port 8000   (Swagger at http://localhost:8000/docs)
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import analytics, basket, products, scrape, search
from app.services import scheduler
from app.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    init_db()
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="GroceryCompare API", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])

for r in (search.router, scrape.router, products.router, basket.router, analytics.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
