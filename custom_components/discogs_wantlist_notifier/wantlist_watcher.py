#!/usr/bin/env python3

#to read out discogs wantlist
import discogs_client

#to scrape all offers of releases
import requests
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
import cloudscraper

import os
import math
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
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
                raise NotImplementedError
            else:
                return Price( self.currency + str(self.value + other.value) )
        else:
            raise NotImplementedError
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
                raise ValueError(f'Cannot compare Prices with different currencies: {self.currency} vs {other.currency}')
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
        elif string=='unknown':
            self.cond = 'unknown'
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
        elif self.cond=='unknown':
            return 11
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


def get_scraper(**kwargs):
    # Use a Windows Chrome user agent that works with Cloudflare
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return scraper


def get_redirected_url(url:str) -> str:
    """get redirected link, discogs release pages are redirects, sometimes are not loaded 'fast' enough, so we need to fetch html of redirected url!"""
    scraper = get_scraper()
    # Load the webpage
    scraper.get(url)
    # Get the final URL after any dynamic redirection
    final_url = scraper.current_url
    # Close the browser
    scraper.quit()
    # Print the final URL
    return final_url



def get_price_stats(item_id:int, url:str=None) -> Stats:
    """get min, med, and max price -- if sold in the past"""
    if url==None:
        url = f'https://www.discogs.com/release/{item_id}'
    scraper = get_scraper()
    page = scraper.get(url)
    #parse html
    soup = BeautifulSoup(page.text, 'html.parser')
    scraper.close()
    #parse stats
    stats_ = soup.find_all('section', id='release-stats')
    if len(stats_)==0:
        print(f'SCRAPE-FAIL in get_price_stats: {url=}')
        return '<Stats SCRAPE-FAIL>'
    stats = stats_[0]
    vals = stats.find_all(lambda tag: tag.string and '€' in tag.string) #should give [min, med, max], if previuosly sold!
    if not vals:
        return Stats( '-', '-', '-')
    #try parsing - if it fails retry with 'redirected url'!
    try:
        # Parse each value to extract just the numeric price (handles "about €10" cases)
        def parse_value(v):
            text = v.contents[0].strip()
            # Extract numeric value from text like "about €10" or "€10.99"
            import re
            match = re.search(r'[\d,]+\.?\d*', text)
            if match:
                value_str = match.group(0).replace(',', '')
                return Price(text.split(value_str)[0] + value_str)  # Keep original prefix/currency
            else:
                return Price(text)
        mn,md,mx = [parse_value(v) for v in vals]
        return Stats( mn, md, mx )
    except:
        #stats were probably not yet loaded! re-try with redirected url!
        return get_price_stats(item_id, get_redirected_url(url) )


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
        #sleeve-condition could not be parsed!
        sleeve_condition = Condition('unknown')
    #parse media condition
    try:
        media_condition = Condition( item.find_all('span', class_='has-tooltip')[0].parent.contents[0].strip() )
    except:
        #try different structure:
        try:
            media_condition = Condition(
                item.find_all('p', class_='item_condition')[0].find_next('span',class_='').contents[0].strip()
            )
        except:
            try:
                media_condition = Condition(
                    item.find(lambda tag: tag.name == 'span' and 'Media Condition' in tag.get_text()).find_next("span").find_next("span").get_text().strip()
                )
            except:
                #media condition parsing failed! (or changed!)
                media_condition = Condition('unknown')

    #parse item-offer-url
    url = 'https://www.discogs.com'+ item.find_all('a', class_='item_description_title')[0].attrs['href']
    #return all collected data
    return {'item_id': item.attrs['data-release-id'], 'media_condition': media_condition, 'sleeve_condition': sleeve_condition, 'price': price_with_shipping, 'price_no_shipping': price_no_shipping, 'url': url}

def change_price(wantlist_item, new_price:float):
    wantlist_item.notes=f'max price: €{new_price:.2f}'
    wantlist_item.save()

def parse_price(wantlist_item) -> Price or None:
    if wantlist_item.notes == '':
        return None
    else:
        return Price( wantlist_item.notes.split(':')[-1] )

def get_wantlist(token:str, interactive:bool=False) -> tuple[list,list]:
    d = discogs_client.Client('wantlist_watcher/0.1', user_token=token)
    me = d.identity()

    #iterate wantlist
    print(f'loading wantlist from discogs')
    wantlist_items = []
    for i in tqdm(range(me.wantlist.pages+1)):
        wantlist_items += me.wantlist.page(i)
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
    wantlist_=[]
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
        wantlist_.append( (master_id,item,max_price_item) )
        max_price[item.id] = max_price_item
    if len(max_price_missing)>0:
        print(f'  \033[93mprices for {len(max_price_missing)} items are missing:\033[0m')
        for i in max_price_missing:
            print(f'    \033[93m{i}\033[0m')
        print(f'  \033[93mSet prices online as a note of the form \'max price: xxx\', or restart with argument \'-i\'.\033[0m')
    print(f'fetching prices for wantlist items (where max price is set)')

    return wantlist_, max_price_missing

def scrape_good_offers(wantlist:list, min_media_condition:Condition, min_sleeve_condition:Condition) -> list:
    return list( scrape_good_offers_lazy(wantlist, min_media_condition, min_sleeve_condition) )

def scrape_good_offers_lazy(wantlist:list, min_media_condition:Condition, min_sleeve_condition:Condition):
    # Scrape marketplace items using cloudscraper with Cloudflare bypass
    scraper = get_scraper()

    good_offers = []
    rate_limit_remaining = 25
    delay = 1.0
    max_delay = 10.0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, min=30, max=60),
    )
    def fetch_page(release_id):
        """Fetch marketplace page with automatic retries."""
        response = scraper.get(f'https://www.discogs.com/sell/release/{release_id}')
        return response

    for master_id, item, _ in wantlist:
        try:
            print(f'  Fetching marketplace for: {item.release.title[:50]}')

            # Try to fetch page with tenacity retries
            try:
                response = fetch_page(item.id)
                print(f'    Page fetched: {response.status_code}')
            except Exception:
                print(f'    ✗ Cloudflare challenge failed after retries (skipping)')
                continue

            if response.status_code != 200 or 'Just a moment' in response.text[:200]:
                print(f'    ✗ Cloudflare challenge')
                continue

            # Parse items
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('tr', class_='shortcut_navigable', attrs={'data-release-id':True})

            if not items:
                print(f'    ℹ️  No items found')
                continue

            print(f'    Found {len(items)} items')

            # Parse each item
            for item_data in items:
                try:
                    # Parse price from converted_price span (includes VAT and currency conversion)
                    converted_price_span = item_data.find('span', class_='converted_price')
                    if not converted_price_span:
                        continue

                    price_text = converted_price_span.get_text()

                    # Extract just the price and currency using regex
                    match = re.search(r'([€$£]?)\s*([\d,]+\.?\d*)', price_text)
                    if not match:
                        continue

                    currency = match.group(1) or '€'
                    value = match.group(2).replace(',', '')
                    price = Price(f'{currency}{value}')

                    # Parse conditions
                    try:
                        sleeve_elements = item_data.find_all('span', class_='item_sleeve_condition')
                        if sleeve_elements:
                            sleeve_text = sleeve_elements[0].contents[0].strip()
                            sleeve_condition = Condition(sleeve_text)
                        else:
                            sleeve_condition = Condition('unknown')
                    except:
                        sleeve_condition = Condition('unknown')

                    # Parse media condition (try tooltip first)
                    try:
                        has_tooltip = item_data.find_all('span', class_='has-tooltip')
                        if has_tooltip:
                            media_text = has_tooltip[0].parent.contents[0].strip()
                            media_condition = Condition(media_text)
                        else:
                            media_condition = Condition('unknown')
                    except:
                        media_condition = Condition('unknown')

                    # Parse URL
                    try:
                        title_elements = item_data.find_all('a', class_='item_description_title')
                        if title_elements:
                            url = 'https://www.discogs.com' + title_elements[0].attrs['href']
                        else:
                            url = ''
                    except:
                        url = ''

                    # Check if meets criteria
                    if (price <= max_price and
                        media_condition >= min_media_condition and
                        sleeve_condition >= min_sleeve_condition):

                        good_offers.append({
                            'item_id': item.id,
                            'media_condition': media_condition,
                            'sleeve_condition': sleeve_condition,
                            'price': price,
                            'price_no_shipping': price,
                            'url': url,
                            'wantlist_item': item
                        })

                except Exception as e:
                    continue

            # Update rate limiting
            rate_limit_remaining = response.headers.get('X-Discogs-Ratelimit-Remaining', 25)
            if int(rate_limit_remaining) < 20:
                delay = min(delay * 2, max_delay)

        except Exception as e:
            print(f'    ✗ Error: {type(e).__name__}: {str(e)[:100]}')
            continue

    scraper.close()
    return good_offers

    #max_price:dict[int,Price] = {}
    #for item_id,_,price in wantlist:
    #    max_price[item_id] = price
    ##filter good offers
    #good_offers = []
    #for master_id,item in tqdm(wantlist, desc='wantlist', leave=False):
    #    good_offers += list( 
    #                filter(lambda on_sale: on_sale['price'] <= max_price[item.id] and on_sale['media_condition'] >= min_media_condition and on_sale['sleeve_condition'] >= min_sleeve_condition, items_on_sale[item.id])
    #            )
    #return good_offers




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

    wantlist, max_price_missing = get_wantlist(token, interactive=interactive)
    good_offers_lazy = scrape_good_offers_lazy(wantlist, min_media_condition, min_sleeve_condition)


    num_offers = 0
    #print buy_list
    for offer in good_offers_lazy:
        num_offers+=1
        #print good offer
        item = offer['wantlist_item'].release
        print(f'good offer found for:')
        print(f'    {[a.name for a in item.artists]} -- {item.title}')
        print(f'    with tracklist   : {item.tracklist}')
        print(f'    media condition  : {offer["media_condition"]}')
        print(f'    sleeve condition : {offer["sleeve_condition"]}')
        print(f'    price            : {offer["price"]}')
        print(f'    price (w/o ship) : {offer["price_no_shipping"]}')
        print(f'    min, med, max    : {get_price_stats(item.id, url=item.url)}')
        print(f'    (threshold price : {parse_price(offer["wantlist_item"])})')
        print(f'    url              : {offer["url"]}')
        print(f'')
    if num_offers==0:
        print(f'no good offers found!')
    
    if len(max_price_missing)>0:
        print(f'  \033[93mprices for {len(max_price_missing)} items are missing:\033[0m')
        for i in max_price_missing:
            print(f'    \033[93m{i}\033[0m')
        print(f'  \033[93mSet prices online as a note of the form \'max price: xxx\', or restart with argument \'-i\'.\033[0m')

