"""Marketplace scraping logic for Discogs wantlist notifier."""
import logging
import time

import cloudscraper
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from .parser import parse_marketplace_item

_LOGGER = logging.getLogger(__name__)


def get_scraper():
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    return scraper


def scrape_good_offers_lazy(wantlist, min_media, min_sleeve):
    scraper = get_scraper()

    rate_limit_remaining = 25
    delay = 1.0
    max_delay = 10.0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, min=30, max=60),
    )
    def fetch_page(release_id):
        response = scraper.get(f"https://www.discogs.com/sell/release/{release_id}")
        return response

    for _, item, max_price in wantlist:
        try:
            _LOGGER.debug("Fetching marketplace for: %s", item.release.title[:50])

            try:
                response = fetch_page(item.id)
            except Exception:
                _LOGGER.warning("Cloudflare challenge failed after retries for release %s (skipping)", item.id)
                continue

            if response.status_code != 200 or "Just a moment" in response.text[:200]:
                _LOGGER.warning("Cloudflare challenge for release %s", item.id)
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.find_all("tr", class_="shortcut_navigable", attrs={"data-release-id": True})

            if not items:
                _LOGGER.debug("No items found for release %s", item.id)
                continue

            _LOGGER.debug("Found %d items for release %s", len(items), item.id)

            for item_data in items:
                try:
                    parsed = parse_marketplace_item(item_data)
                    if parsed is None:
                        continue

                    price = parsed["price"]
                    media_condition = parsed["media_condition"]
                    sleeve_condition = parsed["sleeve_condition"]

                    if (price <= max_price
                            and media_condition >= min_media
                            and sleeve_condition >= min_sleeve):
                        yield {
                            "item_id": item.id,
                            "media_condition": media_condition,
                            "sleeve_condition": sleeve_condition,
                            "price": price,
                            "price_no_shipping": price,
                            "url": parsed["url"],
                            "wantlist_item": item,
                        }
                except Exception:
                    continue

            rate_limit_remaining = response.headers.get("X-Discogs-Ratelimit-Remaining", 25)
            if int(rate_limit_remaining) < 20:
                delay = min(delay * 2, max_delay)

            time.sleep(delay)

        except Exception as e:
            _LOGGER.warning("Error processing release %s: %s: %s", item.id, type(e).__name__, str(e)[:100])
            continue

    scraper.close()


def scrape_good_offers(wantlist, min_media, min_sleeve):
    return list(scrape_good_offers_lazy(wantlist, min_media, min_sleeve))