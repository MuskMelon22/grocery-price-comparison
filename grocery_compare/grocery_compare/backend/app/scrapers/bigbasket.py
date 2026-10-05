"""BigBasket scraper, using layout-agnostic parsing (no hashed CSS classes).

BigBasket sits behind Akamai bot protection. When it serves "Access Denied",
the base class reports the run as `blocked` and the other store carries on.
"""
import logging
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup, Tag
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.scrapers.base import BaseScraper, RawProduct, is_out_of_stock, parse_prices, pause, qty_text

log = logging.getLogger(__name__)

BASE = "https://www.bigbasket.com"
MAX_CLIMB = 7  # parents to climb from a product link to find its card


def _pin_cookie(driver: WebDriver) -> str | None:
    c = driver.get_cookie("_bb_pin_code")
    return c["value"] if c else None


def _card_for(link: Tag) -> Tag | None:
    """Climb from the product link until the ancestor contains a price."""
    node = link
    for _ in range(MAX_CLIMB):
        node = node.parent
        if node is None:
            return None
        if "₹" in node.get_text():
            return node
    return None


class BigBasketScraper(BaseScraper):
    store = "BigBasket"
    product_css = "a[href*='/pd/']"

    def search_url(self, query: str) -> str:
        return f"{BASE}/ps/?{urlencode({'q': query, 'nl': 1})}"

    def is_soft_blocked(self, driver: WebDriver) -> bool:
        # Akamai lets the page shell load but answers the product API with 403.
        # Chrome's resource timing exposes each request's status, so no extra request is made.
        return bool(driver.execute_script("""
            return performance.getEntriesByType('resource').some(
                e => e.name.includes('/listing-svc/') && e.responseStatus === 403);"""))

    def set_location(self, driver: WebDriver, pincode: str) -> bool:
        # BigBasket stores the chosen pincode in the _bb_pin_code cookie.
        if _pin_cookie(driver) == pincode:
            return True
        # ponytail: selectors below are best guesses - written while BigBasket was blocking us,
        # never run live. First successful run: check this path and fix selectors if it warns.
        try:
            wait = WebDriverWait(driver, 10)
            opener = [e for e in driver.find_elements(
                By.XPATH, "//button[contains(., 'Select Location') or contains(., 'Delivery in')]")
                if e.is_displayed()]
            opener[0].click()
            box = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input[placeholder*='area' i], input[placeholder*='location' i]")))
            box.send_keys(pincode)
            wait.until(EC.element_to_be_clickable((By.XPATH, f"//li[contains(., '{pincode}')]"))).click()
            pause()
            wait.until(lambda d: _pin_cookie(d) == pincode)
            driver.refresh()
            return True
        except (WebDriverException, IndexError) as e:
            log.warning("BigBasket: setting pincode %s failed: %s", pincode, getattr(e, "msg", e))
            return False

    def parse(self, html: str) -> list[RawProduct]:
        soup = BeautifulSoup(html, "lxml")
        products: dict[str, RawProduct] = {}  # keyed by URL = dedupe
        for link in soup.select("a[href*='/pd/']"):
            url = urljoin(BASE, link["href"].split("?")[0])
            if url in products:
                continue
            card = _card_for(link)
            if card is None:
                continue
            prices = parse_prices(card.get_text(" "))
            if not prices:
                continue
            img = card.find("img", alt=True)
            if img and len(img["alt"].strip()) > 8:
                name = img["alt"].strip()
            else:
                name = max(card.stripped_strings, key=len)
            products[url] = RawProduct(
                name=name,
                price=min(prices),
                mrp=max(prices),
                image_url=img.get("src") if img else None,
                url=url,
                in_stock=not is_out_of_stock(card.get_text(" ")),
                raw_qty_text=qty_text(name),
            )
        return list(products.values())
