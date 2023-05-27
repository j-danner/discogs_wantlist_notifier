"""Example of a custom component exposing a service."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .wantlist_watcher import *

# The domain of your component. Should be equal to the name of your component.
DOMAIN = "discogs_wantlist_notifier"
_LOGGER = logging.getLogger(__name__)


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the sync service example component."""
    def check_offers_in_wantlist(call: ServiceCall) -> None:
        """Check offers in Discogs Wantlist."""
        device = call.data.get("device_name", None)
        token = call.data.get("discogs_token", None)
        min_sleeve_condition = call.data.get("min_sleeve_condition", 'No Cover')
        min_media_condition = call.data.get("min_media_condition", 'G')
        
        _LOGGER.info('Received data', call.data)

        ## (1) check for good offers
        good_offers, max_price_missing = check_offers_in_wantlist(token, min_media_condition, min_sleeve_condition, interactive=False)
        
        _LOGGER.info('offers in wantlist checked')

        ## (2) send notifications to 'device' about good offers

        #helper function to send notifications to given device, clicking on notification opens given url
        def send_notification(title:str, msg:str, url:str, device:str) -> None:
            service_data = {"message": msg, "title": title, "data": {"notification_icon": "mdi:album", "group": "Discogs Wantlist Watcher", "color": "black", "clickAction": url}}
            hass.services.call('notify', f'mobile_app_{device}', service_data, False)
        
        for offer in good_offers:
            item = offer['wantlist_item'].release
            send_notification(
                title=f'Good offer found for {item.title}!',
                msg=f'media condition: {offer["media_condition"]}, sleeve condition: {offer["sleeve_condition"]}; ' 
                  + f'price {offer["price"]} (max-price: {parse_price(offer["wantlist_item"])})\n'
                  + f' marketplace stats: {get_price_stats(item.id, url=item.url)}\n'
                  + f'tracklist: {item.tracklist}',
                url=item.url,
                device=device)
        
        _LOGGER.info('notifications on offers sent')

        if len(max_price_missing) > 0:
            send_notification(
                title=f'Found items without max price!',
                msg=f'Please set a max-price for the following items: {max_price_missing}',
                url=item.url,
                device=device)
        
        _LOGGER.info('notifications on offers sent')

    # Register our service with Home Assistant.
    hass.services.register(DOMAIN, 'check_offers_in_wantlist', check_offers_in_wantlist)

    # Return boolean to indicate that initialization was successfully.
    return True




