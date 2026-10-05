"""APScheduler job: re-scrape POPULAR_QUERIES every SCRAPE_INTERVAL_HOURS to build price history."""
import logging
import time
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.services.search import scrape_and_store

log = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def scrape_popular() -> None:
    """One query at a time with a pause between, so neither store is hammered."""
    for query in settings.popular_queries:
        try:
            scrape_and_store(query, settings.default_pincode, progress=lambda m, q=query: log.info("[%s] %s", q, m))
        except Exception:  # noqa: BLE001 - one bad query must not stop the rest
            log.exception("scheduled scrape of %r failed", query)
        time.sleep(20)


def start() -> None:
    global _scheduler
    if _scheduler or not settings.enable_scheduler:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    # first run one interval after startup, not at startup, so `--reload` doesn't trigger a 15-query scrape
    _scheduler.add_job(scrape_popular, "interval", hours=settings.scrape_interval_hours,
                       next_run_time=datetime.now() + timedelta(hours=settings.scrape_interval_hours),
                       max_instances=1, coalesce=True, id="scrape_popular")
    _scheduler.start()
    log.info("scheduler: popular products re-scraped every %sh", settings.scrape_interval_hours)


def stop() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
