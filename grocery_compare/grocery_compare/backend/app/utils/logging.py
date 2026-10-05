"""Console + file logging for scrape runs."""
import logging

from app.config import BACKEND_DIR


def setup_logging() -> None:
    log_dir = BACKEND_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_dir / "app.log", encoding="utf-8")],
    )
    for noisy in ("selenium", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
