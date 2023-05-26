#load discogs_wantlist_watcher
from discogs_wantlist_watcher import *

#get service data:
#device to notify
device = data.get("device", "pixel6")
#discogs token
token = data.get("token", None)
#minimal sleeve condition
min_sleeve_condition = Condition( data.get("min_sleeve_condition", 'No Cover')
#minimal media condition
min_media_condition = Condition( data.get("min_media_condition", 'F')

#start 

logger.info(f'starting discogs wantlist watcher')
    
#helper function to send notifications to given device, clicking on notification opens given url
def send_notification(msg:str, url:str, device:str) -> None:
    service_data = {"message": 'New Good Offer', "title": msg, "data": {"notification_icon": "mdi:album", "group": "Discogs Wantlist Watcher", "color": "black", "clickAction": url}}
    hass.services.call('notify', f'mobile_app_{device}', service_data, False)

send_notification(f'Good offer for blablabla found! (token={token})\n media condition: {min_media_condition}, sleeve condition: {min_sleeve_condition}', "https://www.discogs.com/release/484125-Men-At-Work-Down-Under?ev=drec", device)


