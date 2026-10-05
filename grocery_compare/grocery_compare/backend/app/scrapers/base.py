"""Shared scraper plumbing: result types, retries, rate limit, block detection, debug dumps."""
import logging
import random
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.config import settings
from app.scrapers.browser import make_driver

log = logging.getLogger(__name__)

PRICE_RE = re.compile(r"₹\s?([\d,]+(?:\.\d+)?)")
QTY_RE = re.compile(r"\d+(?:\.\d+)?\s?(?:kgs?|gms?|g|ltrs?|l|ml|pcs|pc)\b", re.I)
BLOCK_WORDS = ("access denied", "captcha", "are you a robot", "unusual traffic")
OUT_OF_STOCK_WORDS = ("out of stock", "notify me", "currently unavailable", "sold out")
MIN_GAP_SECONDS = 5  # rate limit: at most one live scrape per store in this window
ATTEMPTS = 3  # first try + 2 retries


@dataclass
class RawProduct:
    name: str
    price: float  # selling price
    mrp: float
    image_url: str | None
    url: str
    in_stock: bool
    raw_qty_text: str  # e.g. "500 g"; the normalizer does the real parsing


@dataclass
class ScrapeResult:
    store: str
    status: str  # success | partial | failed | blocked
    products: list[RawProduct] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Blocked(Exception):
    """The store served a block / captcha page instead of results."""

    def __init__(self, html: str):
        super().__init__("blocked")
        self.html = html


def parse_prices(text: str) -> list[float]:
    return [float(m.group(1).replace(",", "")) for m in PRICE_RE.finditer(text)]


def qty_text(name: str) -> str:
    m = QTY_RE.search(name)
    return m.group(0) if m else ""


def is_out_of_stock(text: str) -> bool:
    text = text.lower()
    return any(w in text for w in OUT_OF_STOCK_WORDS)


def pause(lo: float = 1, hi: float = 3) -> None:
    time.sleep(random.uniform(lo, hi))


class BaseScraper:
    """Subclasses set `store`, `product_css` and implement search_url/set_location/parse."""

    store: str
    product_css: str  # CSS selector that exists once product cards have rendered
    _lock = threading.Lock()  # replaced per subclass in __init_subclass__
    _last_run = 0.0
    _blocked_until = 0.0  # monotonic time; skip live scrapes until then

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._lock = threading.Lock()  # one live scrape per store at a time

    # --- per-store hooks -------------------------------------------------
    def search_url(self, query: str) -> str:
        raise NotImplementedError

    def set_location(self, driver: WebDriver, pincode: str) -> bool:
        """Make the site show prices for `pincode`. Return False if that couldn't be confirmed."""
        raise NotImplementedError

    def parse(self, html: str) -> list[RawProduct]:
        raise NotImplementedError

    def is_soft_blocked(self, driver: WebDriver) -> bool:
        """Page loaded but the store refused its data calls. Override per store."""
        return False

    # --- shared flow -----------------------------------------------------
    def search(self, query: str, pincode: str) -> ScrapeResult:
        """Scrape one store. Never raises: failures come back as status + warnings."""
        with self._lock:
            if time.monotonic() < type(self)._blocked_until:
                return ScrapeResult(self.store, "blocked", warnings=[
                    f"{self.store} blocked us recently; skipping it for now to avoid hammering the site."
                ])
            wait = MIN_GAP_SECONDS - (time.monotonic() - type(self)._last_run)
            if wait > 0:
                time.sleep(wait)
            started = time.monotonic()
            try:
                result = self._search(query, pincode)
            except Blocked as e:
                self._save_debug_html(query, e.html)
                type(self)._blocked_until = time.monotonic() + settings.block_cooldown_minutes * 60
                result = ScrapeResult(self.store, "blocked", warnings=[
                    f"{self.store} blocked the request (bot protection). Try again later."
                ])
            except Exception as e:  # noqa: BLE001 - one store failing must not break the other
                log.exception("%s scrape crashed", self.store)
                result = ScrapeResult(self.store, "failed", warnings=[f"{self.store} failed: {e}"])
            finally:
                type(self)._last_run = time.monotonic()
            log.info("scrape store=%s query=%r pincode=%s status=%s items=%d duration=%.1fs warnings=%s",
                     self.store, query, pincode, result.status, len(result.products),
                     time.monotonic() - started, result.warnings)
            return result

    def _search(self, query: str, pincode: str) -> ScrapeResult:
        warnings: list[str] = []
        driver = make_driver(self.store.lower())
        html = ""
        try:
            for attempt in range(ATTEMPTS):
                try:
                    driver.get(self.search_url(query))
                    pause()
                    self._wait_for_products(driver)  # returns early if the store blocks us
                    self._raise_if_blocked(driver)
                    if attempt == 0 and not self.set_location(driver, pincode):
                        warnings.append(f"{self.store}: couldn't set pincode {pincode}; "
                                        "prices are for the site's default location.")
                    self._wait_for_products(driver)  # instant unless set_location reloaded
                    self._scroll(driver)
                    html = driver.page_source
                    products = self.parse(html)
                    if products:
                        return ScrapeResult(self.store, "partial" if warnings else "success",
                                            products, warnings)
                    self._raise_if_blocked(driver)
                    log.warning("%s: 0 products for %r (attempt %d)", self.store, query, attempt + 1)
                except WebDriverException as e:
                    log.warning("%s: browser error on attempt %d: %s", self.store, attempt + 1, e.msg)
                time.sleep(2 * 2 ** attempt)  # backoff: 2s, 4s, 8s
            self._save_debug_html(query, html or driver.page_source)
            warnings.append(f"{self.store}: no products found for '{query}'.")
            return ScrapeResult(self.store, "failed", warnings=warnings)
        finally:
            driver.quit()

    def _raise_if_blocked(self, driver: WebDriver) -> None:
        # Check visible text, not raw HTML: JioMart's HTML contains config like "skip_captcha".
        visible = (driver.title + " " + driver.execute_script(
            "return document.body ? document.body.innerText : ''")).lower()
        if any(w in visible for w in BLOCK_WORDS) or self.is_soft_blocked(driver):
            raise Blocked(driver.page_source)

    def _wait_for_products(self, driver: WebDriver) -> None:
        try:
            WebDriverWait(driver, settings.scrape_timeout).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, self.product_css) or self.is_soft_blocked(d))
        except TimeoutException:
            pass  # parse() finds 0 items and the retry loop handles it

    def _scroll(self, driver: WebDriver, times: int = 6) -> None:
        """Scroll in steps so lazy-loaded cards render."""
        for _ in range(times):
            driver.execute_script("window.scrollBy(0, 1200)")
            pause(0.8, 1.5)

    def _save_debug_html(self, query: str, html: str) -> None:
        settings.debug_html_dir.mkdir(parents=True, exist_ok=True)
        safe_q = re.sub(r"\W+", "_", query)[:40]
        path = settings.debug_html_dir / f"{self.store.lower()}_{safe_q}_{datetime.now():%Y%m%d_%H%M%S}.html"
        path.write_text(html, encoding="utf-8")
        log.warning("%s: saved page to %s for debugging", self.store, path)
