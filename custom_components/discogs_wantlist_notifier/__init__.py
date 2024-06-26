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
    def check_offers_in_wantlist_service(call: ServiceCall) -> None:
        """Check offers in Discogs Wantlist."""

        #helper function to send notifications to given device, clicking on notification opens given url
        def send_notification(title:str, msg:str, url:str, device:str) -> None:
            if url!=None:
                service_data = {"message": msg, "title": title, "data": {"notification_icon": "mdi:album", "group": "Discogs Wantlist Watcher", "color": "black", "clickAction": url}}
            else:
                service_data = {"message": msg, "title": title, "data": {"notification_icon": "mdi:album", "group": "Discogs Wantlist Watcher", "color": "black"}}
            hass.services.call('notify', f'mobile_app_{device}', service_data, False)
        
        device = call.data.get("device_name", None)
        token = call.data.get("discogs_token", None)
        min_sleeve_condition = Condition( call.data.get("min_sleeve_condition", 'No Cover') )
        min_media_condition = Condition( call.data.get("min_media_condition", 'G') )
        
        _LOGGER.info('Received data')
        ## (1) load wantlist
        wantlist, max_price_missing = get_wantlist(token)
        if len(max_price_missing) > 0:
            send_notification(
                title=f'Found items without max price!',
                msg=f'Please set a max-price for the following items: { str(max_price_missing).replace("<","").replace(">","") }',
                url=None,
                device=device)
        
        _LOGGER.info('notifications on missing prices sent')

        ## (2) check for good offers and send notifications to 'device'
        good_offers_lazy = scrape_good_offers_lazy(wantlist, min_media_condition, min_sleeve_condition)
        
        for offer in good_offers_lazy:
            item = offer['wantlist_item'].release
            title = f'Good offer found for {item.artists[0].name} - {item.title}'
            msg = f'tracklist: { list(i.title for i in item.tracklist) }\n' + f'media condition: {offer["media_condition"]}, sleeve condition: {offer["sleeve_condition"]}\n' + f'price {offer["price"]} (max-price: {parse_price(offer["wantlist_item"])})\n' + f'Marketplace {str(get_price_stats(item.id, url=item.url)).replace("<","").replace(">","")}'
            _LOGGER.info(title + ' -- ' + msg)
            send_notification(title=title, msg=msg, url=offer['url'], device=device)
        
        _LOGGER.info('offers in wantlist checked and notifications sent')

    # Register our service with Home Assistant.
    hass.services.register(DOMAIN, 'check_offers_in_wantlist', check_offers_in_wantlist_service)

    # Return boolean to indicate that initialization was successfully.
    return True




