"""HTML parsing functions for Discogs marketplace data."""
import re

from bs4 import BeautifulSoup, Tag

from .data_models import Condition, Price, Stats

PRICE_REGEX = re.compile(r"([€$£]?)\s*([\d,]+\.?\d*)")


def parse_marketplace_item(item_data: Tag) -> dict | None:
    if "unavailable" in item_data.attrs.get("class", []):
        return "unavailable"

    converted_price_span = item_data.find("span", class_="converted_price")
    if not converted_price_span:
        return None

    price_text = converted_price_span.get_text()
    match = PRICE_REGEX.search(price_text)
    if not match:
        return None

    currency = match.group(1) or "€"
    value = match.group(2).replace(",", "")
    price = Price(f"{currency}{value}")

    try:
        sleeve_elements = item_data.find_all("span", class_="item_sleeve_condition")
        if sleeve_elements:
            sleeve_text = sleeve_elements[0].contents[0].strip()
            sleeve_condition = Condition(sleeve_text)
        else:
            sleeve_condition = Condition("unknown")
    except Exception:
        sleeve_condition = Condition("unknown")

    try:
        has_tooltip = item_data.find_all("span", class_="has-tooltip")
        if has_tooltip:
            media_text = has_tooltip[0].parent.contents[0].strip()
            media_condition = Condition(media_text)
        else:
            media_condition = Condition("unknown")
    except Exception:
        media_condition = Condition("unknown")

    try:
        title_elements = item_data.find_all("a", class_="item_description_title")
        if title_elements:
            url = "https://www.discogs.com" + title_elements[0].attrs["href"]
        else:
            url = ""
    except Exception:
        url = ""

    return {
        "item_id": item_data.attrs.get("data-release-id"),
        "media_condition": media_condition,
        "sleeve_condition": sleeve_condition,
        "price": price,
        "price_no_shipping": price,
        "url": url,
    }


def get_price_stats(item_id: int, scraper, url: str | None = None) -> Stats:
    if url is None:
        url = f"https://www.discogs.com/release/{item_id}"
    page = scraper.get(url)
    soup = BeautifulSoup(page.text, "html.parser")
    stats_section = soup.find("section", id="release-stats")
    if not stats_section:
        return '<Stats SCRAPE-FAIL>'
    vals = stats_section.find_all(lambda tag: tag.string and "€" in tag.string)
    if not vals:
        return Stats("-", "-", "-")
    try:

        def parse_value(v):
            text = v.contents[0].strip()
            match = re.search(r"[\d,]+\.?\d*", text)
            if match:
                value_str = match.group(0).replace(",", "")
                return Price(text.split(value_str)[0] + value_str)
            return Price(text)

        mn, md, mx = [parse_value(v) for v in vals]
        return Stats(mn, md, mx)
    except Exception:
        return get_price_stats(item_id, scraper, get_redirected_url(url, scraper))


def get_redirected_url(url: str, scraper) -> str:
    scraper.get(url)
    return scraper.current_url


def parse_price_from_text(price_text: str) -> Price | None:
    match = PRICE_REGEX.search(price_text)
    if match:
        currency = match.group(1) or "€"
        value = match.group(2).replace(",", "")
        return Price(f"{currency}{value}")
    return None
