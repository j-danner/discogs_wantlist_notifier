"""Notification service for Discogs Wantlist Notifier."""
from __future__ import annotations

from homeassistant.core import HomeAssistant


def send_notification(
    hass: HomeAssistant,
    notification_entity: str,
    title: str,
    msg: str,
    url: str | None,
) -> None:
    """Send a notification via Home Assistant's notify service."""
    service_data = {
        "message": msg,
        "title": title,
        "data": {
            "notification_icon": "mdi:album",
            "group": "Discogs Wantlist Watcher",
            "color": "black",
        },
    }
    if url is not None:
        service_data["data"]["clickAction"] = url

    hass.services.async_call("notify", notification_entity, service_data, False)


def format_offer_message(offer: dict) -> tuple[str, str]:
    """Format a good offer notification title and body."""
    item = offer["wantlist_item"].release
    title = f"Good offer found for {item.artists[0].name} - {item.title}"
    msg = (
        f"tracklist: {[i.title for i in item.tracklist]}\n"
        f"media condition: {offer['media_condition']}, "
        f"sleeve condition: {offer['sleeve_condition']}\n"
        f"price: {offer['price']}"
    )
    return title, msg


def notify_missing_prices(
    hass: HomeAssistant,
    notification_entity: str,
    missing_items: list,
) -> None:
    """Notify user that some wantlist items are missing max prices."""
    missing_releases = "\n".join(
        str(item).replace("<", "").replace(">", "")
        for item in missing_items
    )
    send_notification(
        hass,
        notification_entity,
        title="Found items without max price!",
        msg=f"Please set a max-price for the following items: {missing_releases}",
        url=None,
    )
