"""POST /scrape starts a background scrape; GET /scrape/{run_id} reports progress."""
import logging
import threading
import uuid

from fastapi import APIRouter, HTTPException

from app.database import SessionLocal
from app.schemas import ScrapeJob, ScrapeRequest
from app.services.search import clean_query, is_fresh, scrape_and_store

router = APIRouter(tags=["scrape"])
log = logging.getLogger(__name__)

# ponytail: in-memory job table, lost on restart and single-process only; move to a DB table
# if the API ever runs with several workers.
JOBS: dict[str, ScrapeJob] = {}
_lock = threading.Lock()


def _run(job: ScrapeJob) -> None:
    try:
        scrape_and_store(job.query, job.pincode, progress=job.messages.append)
        job.status = "done"
    except Exception as e:  # noqa: BLE001 - report to the UI instead of dying silently
        log.exception("scrape job %s crashed", job.run_id)
        job.messages.append(f"Scrape failed: {e}")
        job.status = "error"


@router.post("/scrape", response_model=ScrapeJob)
def start_scrape(req: ScrapeRequest) -> ScrapeJob:
    query = clean_query(req.query)
    with _lock:
        for job in JOBS.values():  # same search already running: share it
            if job.status == "running" and (job.query, job.pincode) == (query, req.pincode):
                return job
        job = ScrapeJob(run_id=uuid.uuid4().hex, query=query, pincode=req.pincode,
                        status="running", messages=[])
        JOBS[job.run_id] = job
    with SessionLocal() as db:
        if not req.force and is_fresh(db, query, req.pincode):
            job.status, job.cached = "done", True
            job.messages.append("Using prices scraped in the last few hours.")
            return job
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return job


@router.get("/scrape/{run_id}", response_model=ScrapeJob)
def scrape_status(run_id: str) -> ScrapeJob:
    job = JOBS.get(run_id)
    if job is None:
        raise HTTPException(404, "Unknown run_id (the server may have restarted).")
    return job
