"""Discogs Wantlist Notifier integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DATA_KEY,
    DOMAIN,
    CONF_TOKEN,
    CONF_MEDIA_CONDITION,
    CONF_SLEEVE_CONDITION,
    CONF_NOTIFICATION_ENTITY,
    DEFAULT_MEDIA_CONDITION,
    DEFAULT_SLEEVE_CONDITION,
    SERVICE_CHECK_OFFERS,
)
from .data_models import Condition
from .discogs_client import get_wantlist
from .scraper import scrape_good_offers
from .notification import send_notification, format_offer_message, notify_missing_prices

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Discogs Wantlist Notifier from a config entry."""
    hass.data.setdefault(DATA_KEY, {})
    hass.data[DATA_KEY][entry.entry_id] = entry

    async def check_offers_service(call: ServiceCall) -> None:
        """Check offers in Discogs Wantlist and send notifications."""
        config = entry.data
        options = entry.options

        token = config[CONF_TOKEN]
        media_cond = Condition(options.get(CONF_MEDIA_CONDITION, DEFAULT_MEDIA_CONDITION))
        sleeve_cond = Condition(options.get(CONF_SLEEVE_CONDITION, DEFAULT_SLEEVE_CONDITION))
        notification_entity = options.get(CONF_NOTIFICATION_ENTITY)

        _LOGGER.info("Checking offers in Discogs Wantlist")

        # (1) Load wantlist via executor (blocking API call)
        wantlist, max_price_missing = await hass.async_add_executor_job(
            get_wantlist, token
        )

        # (2) Notify about missing max prices
        if max_price_missing and notification_entity:
            notify_missing_prices(
                hass, notification_entity, max_price_missing
            )
            _LOGGER.info("Notifications sent for %d items missing max price", len(max_price_missing))

        # (3) Scrape marketplace for good offers via executor
        good_offers = await hass.async_add_executor_job(
            scrape_good_offers, wantlist, media_cond, sleeve_cond
        )

        # (4) Send notifications for each good offer
        if notification_entity:
            for offer in good_offers:
                title, msg = format_offer_message(offer)
                _LOGGER.info("%s -- %s", title, msg)
                send_notification(
                    hass, notification_entity, title, msg, offer.get("url")
                )

        _LOGGER.info("Finished checking offers in Discogs Wantlist")

    # Register the service
    hass.services.async_register(DOMAIN, SERVICE_CHECK_OFFERS, check_offers_service)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, SERVICE_CHECK_OFFERS)
    hass.data[DATA_KEY].pop(entry.entry_id)
    return True
