from __future__ import annotations

import logging

import discogs_client

from .data_models import Price

_LOGGER = logging.getLogger(__name__)


def parse_price(wantlist_item) -> Price | None:
    if wantlist_item.notes == "":
        return None
    return Price(wantlist_item.notes.split(":")[-1])


def get_wantlist(token: str) -> tuple[list, list]:
    d = discogs_client.Client("wantlist_watcher/0.1", user_token=token)
    me = d.identity()

    _LOGGER.info("loading wantlist from discogs")
    wantlist_items = []
    for i in range(me.wantlist.pages + 1):
        wantlist_items += me.wantlist.page(i)

    wantlist = []
    for item in wantlist_items:
        master_id = item.release.master.id if item.release.master is not None else item.id
        wantlist.append((master_id, item))

    wantlist_master: dict[int, list] = {}
    for master_id, item in wantlist:
        if master_id not in wantlist_master:
            wantlist_master[master_id] = []
        wantlist_master[master_id].append(item)

    _LOGGER.info("fetching max prices from notes of wantlist-items")
    max_price_missing = []
    wantlist_ = []

    for master_id, item in wantlist:
        max_price_item = parse_price(item)
        if max_price_item is None:
            prices = [
                parse_price(wantlist_item)
                for wantlist_item in wantlist_master[master_id]
            ]
            valid_prices = [p for p in prices if p is not None]
            if valid_prices:
                max_price_item = max(valid_prices)
            else:
                max_price_missing.append(item)
                continue
        wantlist_.append((master_id, item, max_price_item))

    if max_price_missing:
        _LOGGER.info("prices for %d items are missing", len(max_price_missing))
        for item in max_price_missing:
            _LOGGER.info("  %s", item)

    _LOGGER.info(
        "processed wantlist: %d items with prices, %d items missing prices",
        len(wantlist_),
        len(max_price_missing),
    )

    return wantlist_, max_price_missing


def validate_token(token: str) -> bool:
    try:
        d = discogs_client.Client("wantlist_watcher/0.1", user_token=token)
        d.identity()
        return True
    except Exception:
        return False
