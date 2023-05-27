#!/usr/bin/env python3

#to read out discogs wantlist
import discogs_client

#to scrape all offers of releases
import requests
from bs4 import BeautifulSoup
import re
from tqdm import tqdm

import os

import functools

@functools.total_ordering
class Price(object):
    currency:str = '€'
    value:float = 0.0
    def __init__(self, string):
        price_tuple = re.split(r'(\d+)', string.strip())
        self.currency = price_tuple[0]
        value_str = ''.join(price_tuple[1:]).replace(',','')
        assert(value_str!='')
        self.value = float( value_str )
    def __add__(self, other):
        if type(self)==type(other):
            if self.currency != other.currency:
                raise NotImplemented
            else:
                return Price( self.currency + str(self.value + other.value) )
        else:
            raise NotImplemented
    def __str__(self):
        return self.currency+str(self.value)
    def __repr__(self):
        return str(self)
    def __eq__(self,other):
        if type(self)==type(other):
            return self.currency == other.currency and self.value == other.value
        else:
            return self.value == other
    def __gt__(self,other):
        if type(self)==type(other):
            if self.currency != other.currency:
                raise NotImplemented
            else:
                return self.value > other.value
        else:
            return self.value > other




@functools.total_ordering
class Condition(object):
    cond = 'P'
    def __init__(self, string):
        if string=='Mint (M)' or string=='M':
            self.cond = 'M'
        elif string=='Near Mint (NM)' or string=='Near Mint (NM or M-)' or string=='NM' or string=='M-':
            self.cond = 'NM'
        elif string=='Very Good Plus (VG+)' or string=='VG+':
            self.cond = 'VG+'
        elif string=='Very Good (VG)' or string=='VG':
            self.cond = 'VG'
        elif string=='Good Plus (G+)' or string=='G+':
            self.cond = 'G+'
        elif string=='Good (G)' or string=='G':
            self.cond = 'G'
        elif string=='Fair (F)' or string=='F':
            self.cond = 'F'
        elif string=='Poor (P)' or string=='P':
            self.cond = 'P'
        elif string=='Not Graded':
            self.cond = 'not graded'
        elif string=='Generic' or string=='generic':
            self.cond = 'generic'
        elif string=='No Cover' or string=='not provided' or string=='':
            self.cond = 'not provided'
        else:
            raise ValueError(f'condition cannot be determined! (for input: {string})')
    def __str__(self):
        return self.cond
    def __repr__(self):
        return f'<Condition {self.cond}>'
    def __int__(self):
        if self.cond=='M':
            return 0
        elif self.cond=='NM':
            return 1
        elif self.cond=='VG+':
            return 2
        elif self.cond=='VG':
            return 3
        elif self.cond=='G+':
            return 4
        elif self.cond=='G':
            return 5
        elif self.cond=='F':
            return 6
        elif self.cond=='P':
            return 7
        elif self.cond=='not graded':
            return 8
        elif self.cond=='generic':
            return 9
        elif self.cond=='not provided':
            return 10
    def __eq__(self, other):
        if type(self) != type(other):
            raise NotImplemented
        else:
            return self.cond == other.cond
    def __gt__(self,other):
        return int(self) < int(other)


class Stats(object):
    def __init__(self, mn:Price, md:Price, mx:Price):
        self.mn = mn
        self.md = md
        self.mx = mx
    def __repr__(self):
        return f'<Stats min={self.mn} med={self.md} max={self.mx}>'
    def __str__(self):
        return self.__repr__()


def get_redirected_url(url:str) -> str:
    """get redirected link, discogs release pages are redirects, sometimes are not loaded 'fast' enough, so we need to fetch html of redirected url!"""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode, no browser window
    # Create a new instance of the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)
    # Specify the URL of the webpage
    url = "https://www.discogs.com/release/4602523"
    # Load the webpage
    driver.get(url)
    # Get the final URL after any dynamic redirection
    final_url = driver.current_url
    # Close the browser
    driver.quit()
    # Print the final URL
    return final_url



def get_price_stats(item_id:int, url:str=None) -> Stats:
    """get min, med, and max price -- if sold in the past"""
    if url==None:
        url = f'https://www.discogs.com/release/{item_id}'
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.text, 'lxml')
    #get all setter items
    stats = soup.find_all('section', id='release-stats')[0]
    vals = stats.find_all('span', class_='') #should give [rating, min, med, max], if previuosly sold!
    if vals[1].contents[0] == 'Never': #never sold before
        return Stats( '-', '-', '-')
    elif vals[1].contents[0] == '--': #stats were not loaded! --use redirected url instead!
        return get_price_stats(item_id, get_redirected_url(url) )
    mn,md,mx = [Price(v.contents[0]) for v in vals[1:]  ]
    return Stats( mn, md, mx )

def parse_item_API(item):
    """parse item using listing_id and API -- slow"""
    listing_id = item.find_all('a', class_='item_description_title')[0].attrs['href'].split('/')[-1]
    try:
        l = d.listing(listing_id)
    except:
        return 'unavailable'
    sleeve_condition = Condition( l.sleeve_condition )
    media_condition = Condition( l.condition )
    price_no_shipping = Price( l.data['price']['currency'] + str(l.data['price']['value']) )
    try:
        #assumption: item is available in users country iff there is a shipping price
        price_with_shipping = Price( l.data['shipping_price']['currency'] + str(l.data['shipping_price']['value']) ) + price_no_shipping
        return {'listing_id': listing_id, 'item_id': item.attrs['data-release-id'], 'media_condition': media_condition, 'sleeve_condition': sleeve_condition, 'price': price_with_shipping, 'price_no_shipping': price_no_shipping}
    except KeyError:
        return 'unavailable'

def parse_item_html(item):
    """parse items content using html structure -- fast"""
    if 'unavailable' in item.attrs['class']:
        return 'unavailable'
    #parse price
    price_no_shipping = Price( item.find_all('span', class_='price')[0].contents[0].strip() )
    #parse price with shipping -- html is different if total is 'about' right, i.e., when currency is not €
    try:
        price_with_shipping = Price( item.find_all('span', class_='converted_price')[0].contents[0].strip() )
    except TypeError or IndexError:
        price_with_shipping = Price( item.find_all('span', class_='converted_price')[0].contents[1].strip() )
    #parse sleeve condition
    try:
        sleeve_condition = Condition( item.find_all('span', class_='item_sleeve_condition')[0].contents[0] )
    except IndexError:
        #no sleeve-condition information given!
        sleeve_condition = Condition('No Cover')
    #parse media condition
    media_condition = Condition( item.find_all('span', class_='has-tooltip')[0].parent.contents[0].strip() )
    #return all collected data
    return {'item_id': item.attrs['data-release-id'], 'media_condition': media_condition, 'sleeve_condition': sleeve_condition, 'price': price_with_shipping, 'price_no_shipping': price_no_shipping}

def change_price(wantlist_item, new_price:float):
    wantlist_item.notes=f'max price: €{new_price:.2f}'
    wantlist_item.save()

def parse_price(wantlist_item) -> Price or None:
    if wantlist_item.notes == '':
        return None
    else:
        return Price( wantlist_item.notes.split(':')[-1] )

def check_offers_in_wantlist(token:str, min_media_condition:Condition, min_sleeve_condition:Condition, interactive:bool=False) -> None:
    d = discogs_client.Client('wantlist_watcher/0.1', user_token=token)
    me = d.identity()

    #iterate wantlist
    print(f'loading wantlist from discogs')
    wantlist_list = []
    for i in tqdm(range(me.wantlist.pages+1)):
            wantlist_list.append( me.wantlist.page(i) )
    wantlist_items = sum(wantlist_list, [])
    #add master_id info to each wantlist_item
    wantlist = []
    for item in wantlist_items:
        item_master_id = item.release.master.id if item.release.master!=None else item.id
        wantlist.append( (item_master_id, item) )
    #also store wantlist grouped by master-releases
    wantlist_master = dict()
    for master_id,item in wantlist:
        if not(master_id in wantlist_master):
            wantlist_master[master_id] = []
        wantlist_master[master_id].append( item )


    print(f'fetching max prices from notes of wantlist-items')
    max_price = {}
    max_price_missing = []
    #check if threshold prices are complete
    for master_id,item in wantlist:
        max_price_item = parse_price(item)
        if max_price_item == None:
            #max-price could not be parsed! proceed as follows
            #(1) check if any other item on wantlist with same master_id has a max-price 
            #(2) otherwise ask for max price and save it for all those wantlist-items

            #(1) check other wantlist items with same master_id
            try:
                max_price_item = max(filter(lambda p: p!=None, [parse_price(wantlist_item) for wantlist_item in wantlist_master[master_id]]))
            except:
                if interactive:
                    #(2) ask for max price -- give stats to give a feeling for 'good price'
                    try:
                        release = d.master(master_id).main_release
                    except: #there might be no master release
                        release = d.release(master_id)
                    print(f'{ release.artists[0].name } : {release.tracklist} : {[get_price_stats(item.id) for item in wantlist_master[master_id]]}')
                    price_input:str = ''
                    while price_input == '':
                        price_input = input(f'enter price threshold: ')
                    price = float(price_input)
                    #save max price in notes field for all wantlist items with this master_id
                    for wantlist_item in wantlist_master[master_id]:
                        change_price(wantlist_item, price)
                    max_price_item = parse_price(item)
                else:
                    max_price_missing.append(item)
                    continue
        assert(max_price_item != None)
        max_price[item.id] = max_price_item
    if len(max_price_missing)>0:
        print(f'  \033[93mprices for {len(max_price_missing)} items are missing:\033[0m')
        for i in max_price_missing:
            print(f'    \033[93m{i}\033[0m')
        print(f'  \033[93mSet prices online as a note of the form \'max price: xxx\', or restart with argument \'-i\'.\033[0m')


    print(f'fetching prices for wantlist items (where max price is set)')
    items_on_sale = {}
    for master_id,item in tqdm([i for i in wantlist if i[1].id in max_price]):
        item_id = item.id
        items_on_sale[item_id] = []
        pg = 1
        last_page = False
        while not(last_page):
            url = f'https://www.discogs.com/sell/release/{item_id}?sort=price%2Casc&limit=250&ev=rb&page={pg}'
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
            page = requests.get(url, headers=headers)
            soup = BeautifulSoup(page.text, 'lxml')
            #get all setter items
            offers_on_page = soup.find_all('tr', class_='shortcut_navigable',attrs={'data-release-id':True})
            for offer in offers_on_page:
                parsed_item = parse_item_html(offer)
                if type(parsed_item) == dict:
                    parsed_item['wantlist_item'] = item
                    items_on_sale[item_id].append( parsed_item )
            if len(offers_on_page)<250:
                last_page = True
            else:
                pg += 1
    
    good_offers = []
    for master_id,item in tqdm(wantlist, desc='wantlist', leave=False):
        if(item.id in max_price):
            good_offers += list( 
                    filter(lambda on_sale: on_sale['price'] <= max_price[item.id] and on_sale['media_condition'] >= min_media_condition and on_sale['sleeve_condition'] >= min_sleeve_condition, items_on_sale[item.id])
                    )

    return good_offers, max_price_missing




if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Check your discogs wantlist for items on sale meeting a predefined price, stored in the _notes_ section of your wantlist items. (If no max price is found, it asks for it and stores it online. BEWARE THIS OVERWRITES NOTES OF WANTLIST ITEMS!)', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-tk', '--token', help='discogs personal access token (can be generated at "discogs.com/settings/developers")', type=str, required=True)
    parser.add_argument('-sc', '--sleeve-condition', help='min accepted sleeve-condition (M > NM > VG+ > VG > G+ > G > F > P > Not Graded >  Generic > No Cover)', type=str, default='No Cover')
    parser.add_argument('-mc', '--media-condition', help='min accepted sleeve-condition (M > NM > VG+ > VG > G+ > G > F > P > Not Graded)', type=str, default='VG')
    parser.add_argument('-i', '--interactive', help='ask for max prices for items in wantlist where max-price has not yet been selected', action='store_true')
    args = parser.parse_args()

    token = args.token
    min_media_condition = Condition( args.media_condition )
    min_sleeve_condition = Condition( args.sleeve_condition )
    interactive = args.interactive

    good_offers, max_price_missing = check_offers_in_wantlist(token, min_media_condition, min_sleeve_condition, interactive=interactive)

    if len(good_offers)==0:
        print(f'no good offers found!')

    #print buy_list
    for offer in good_offers:
        item = offer['wantlist_item'].release
        print(f'good offer found for:')
        print(f'    {[a.name for a in item.artists]}   : {item.title}')
        print(f'    with tracklist   : {item.tracklist}')
        print(f'    media condition  : {offer["media_condition"]}')
        print(f'    sleeve condition : {offer["sleeve_condition"]}')
        print(f'    price            : {offer["price"]}')
        print(f'    price (w/o ship) : {offer["price_no_shipping"]}')
        print(f'    min, med, max    : {get_price_stats(item.id, url=item.url)}')
        print(f'    (threshold price : {parse_price(offer["wantlist_item"])})')
        print(item.url)
    
    if len(max_price_missing)>0:
        print(f'  \033[93mprices for {len(max_price_missing)} items are missing:\033[0m')
        for i in max_price_missing:
            print(f'    \033[93m{i}\033[0m')
        print(f'  \033[93mSet prices online as a note of the form \'max price: xxx\', or restart with argument \'-i\'.\033[0m')

