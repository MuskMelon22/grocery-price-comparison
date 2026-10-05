"""App settings, read from environment variables / backend/.env."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    scrape_headless: bool = False  # visible browser gets blocked less often
    scrape_timeout: int = 30  # seconds to wait for a page / product links
    chrome_profile_dir: Path = BACKEND_DIR / "chrome_profile"  # keeps cookies + chosen location
    debug_html_dir: Path = BACKEND_DIR / "debug_html"
    default_pincode: str = "400001"
    block_cooldown_minutes: int = 30  # after a store blocks us, don't retry it for this long

    # Swap to PostgreSQL by setting e.g. postgresql+psycopg://user:pass@host/db
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'grocery.db').as_posix()}"
    cache_hours: int = 6  # search results younger than this are served from the DB
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    enable_scheduler: bool = True
    scrape_interval_hours: int = 12
    popular_queries: list[str] = [
        "milk", "atta", "eggs", "butter", "rice", "sugar", "tea", "coffee", "sunflower oil",
        "toor dal", "paneer", "curd", "bread", "maggi", "biscuits",
    ]


settings = Settings()
