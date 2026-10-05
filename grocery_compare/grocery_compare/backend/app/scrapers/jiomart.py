"""JioMart scraper.

JioMart has no <a href> product links on its search page. Each card carries analytics
data-* attributes (data-product-slug, data-name, data-price, data-image), which are far
more stable than its CSS class names, so we parse those.
"""
import logging
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.scrapers.base import BaseScraper, RawProduct, is_out_of_stock, parse_prices, pause, qty_text

log = logging.getLogger(__name__)

BASE = "https://www.jiomart.com"


def _visible_text(driver: WebDriver) -> str:
    return driver.execute_script("return document.body ? document.body.innerText : ''")


class JioMartScraper(BaseScraper):
    store = "JioMart"
    product_css = "[data-product-slug]"

    def search_url(self, query: str) -> str:
        return f"{BASE}/products?{urlencode({'q': query})}"

    def set_location(self, driver: WebDriver, pincode: str) -> bool:
        # The header shows e.g. "MUMBAI, MAHARASHTRA, 400001, INDIA" a few seconds after load.
        wait = WebDriverWait(driver, 10)
        try:
            wait.until(lambda d: pincode in _visible_text(d)[:1000])
            return True
        except WebDriverException:
            pass  # different (or no) pincode shown: change it below
        try:
            buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Select Location Manually')]")
            if not buttons:  # popup already dismissed: open it from the header instead
                buttons = driver.find_elements(By.XPATH, "//*[normalize-space(text())='Location']")
            buttons[0].click()
            box = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input[placeholder*='area'], input[placeholder*='pincode' i]")))
            box.send_keys(pincode)
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".pac-item"))).click()
            pause()
            for label in ("Confirm", "Save", "Proceed"):  # some flows ask to confirm the address
                for b in driver.find_elements(By.XPATH, f"//button[contains(., '{label}')]"):
                    if b.is_displayed():
                        b.click()
                        pause()
                        break
            driver.refresh()
            wait.until(lambda d: pincode in _visible_text(d)[:1000])
            return True
        except (WebDriverException, IndexError) as e:
            log.warning("JioMart: setting pincode %s failed: %s", pincode, getattr(e, "msg", e))
            return False

    def parse(self, html: str) -> list[RawProduct]:
        soup = BeautifulSoup(html, "lxml")
        products: dict[str, RawProduct] = {}  # keyed by slug = dedupe
        for card in soup.select("[data-product-slug]"):
            slug = card["data-product-slug"]
            meta = card.select_one("[data-name]")
            if slug in products or meta is None:
                continue
            text = card.get_text(" ")
            prices = parse_prices(text)
            try:
                price = float(meta["data-price"])
            except (KeyError, ValueError):
                if not prices:
                    continue
                price = min(prices)
            name = meta.get("data-name", "").strip()
            products[slug] = RawProduct(
                name=name,
                price=price,
                mrp=max(prices + [price]),  # card shows selling price and struck-out MRP
                image_url=meta.get("data-image"),
                url=f"{BASE}/product/{slug}",
                in_stock=not is_out_of_stock(text),
                raw_qty_text=qty_text(name),
            )
        return list(products.values())
