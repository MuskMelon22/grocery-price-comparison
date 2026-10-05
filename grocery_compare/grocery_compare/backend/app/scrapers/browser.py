"""Selenium Chrome driver factory."""
from pathlib import Path

from selenium import webdriver

from app.config import settings

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


def make_driver(profile_name: str) -> webdriver.Chrome:
    """Start Chrome with a persistent per-store profile so cookies/location survive runs.

    Selenium Manager downloads the matching chromedriver automatically.
    """
    profile: Path = settings.chrome_profile_dir / profile_name
    profile.mkdir(parents=True, exist_ok=True)

    opts = webdriver.ChromeOptions()
    opts.add_argument(f"--user-data-dir={profile}")
    opts.add_argument(f"--user-agent={USER_AGENT}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1366,900")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    if settings.scrape_headless:
        opts.add_argument("--headless=new")

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(settings.scrape_timeout)
    return driver
