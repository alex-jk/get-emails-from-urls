######################################################################
import logging

import re
from requests_html import HTMLSession
import requests
import time
import requests.adapters
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)

# scrape emails
from urllib.parse import urlsplit
from collections import deque
import collections, itertools
from bs4 import BeautifulSoup
import sys

import nest_asyncio
nest_asyncio.apply()

def get_source(url):
    try:
        session = HTMLSession()
        retry = Retry(connect=0, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        #print("start")
        
        headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "accept-encoding": "gzip, deflate, br",
        "cache-control": "max-age=0",
        "content-type": "application/x-www-form-urlencoded",
        "dnt": "1",
        "origin": "https://aavtrain.com",
        "referer": "https://aavtrain.com/index.asp",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) snap Chromium/74.0.3729.169 Chrome/74.0.3729.169 Safari/537.36"
        }
        
        response = session.get(url, verify=False, timeout=3.5, headers=headers)
        # response = session.get(url, verify=False, timeout=(0.5, 0.5))
        #print("done")
        return response
    except BaseException as e:
        print("EXCEPTION: ---------------------------")
        print(e)
        #print("--------------------------------------")
        return None
   
  def scrap_emails(urls, max_links):
    visited_num_times = {}
    visited_num_emails = {}
    
    emails_list = []
    for original_url in urls:
        # read url from input
        # original_url = urls[0]
        # to save urls to be scraped
        unscraped = deque([original_url])
        
        # to save scraped urls
        scraped = set()
        
        # to save fetched emails
        emails = set() 

        len_unscraped = 0
        while (len(unscraped)):
            # move unsraped_url to scraped_urls set
            url = unscraped.popleft()  # popleft(): Remove and return an element from the left side of the deque
            scraped.add(url)
            parts = urlsplit(url)    
            base_url = "{0.scheme}://{0.netloc}".format(parts)
            
            if '/' in parts.path:
                path = url[:url.rfind('/')+1]
            else:
                path = url
            print("Crawling URL %s" % url.encode(sys.stdout.encoding, errors='replace')) # Optional
            if not (url.endswith(".pdf") or url.endswith(".jpg") or url.endswith(".png")):
                response = get_source(url)
            
            if (response is None):
                continue
            
            # You may edit the regular expression as per your requirement
            new_emails = set(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+", 
                          response.text, re.I)) # re.I: (ignore case)
            new_emails = [email for email in new_emails if email.endswith('.com') or email.endswith('.ru') or email.endswith('.net')]
            print("Added more emails:", len(new_emails))
            
            # check netloc part of the url
            url_netloc = parts.netloc
            
            if url_netloc in visited_num_times:
                visited_num_times[url_netloc] = visited_num_times.get(url_netloc,0) + 1
            else:
                visited_num_times[url_netloc] = 1
            
            if url_netloc in visited_num_emails:
                visited_num_emails[url_netloc] = visited_num_emails.get(url_netloc,0) + len(new_emails)
            else:
                visited_num_emails[url_netloc] = len(new_emails)
                
            print("Current netloc: %s, visits: %d, netloc emails added: %d" %(url_netloc, visited_num_times[url_netloc], visited_num_emails[url_netloc]))
            if (visited_num_times[url_netloc] > 7) and (visited_num_emails[url_netloc] == 0):
                continue
            
            print("Len unscraped:", len(unscraped))
            emails.update(new_emails)
            emails_list.extend(emails)            
            
            # get more links
            if len_unscraped < max_links:
                print("Getting more links...")
                # create a beutiful soup for the html document
                soup = BeautifulSoup(response.text, 'lxml')
    
                for anchor in soup.find_all("a"): 
                    
                    # extract linked url from the anchor
                    if "href" in anchor.attrs:
                        link = anchor.attrs["href"]
                    else:
                        link = ''
                    
                    # resolve relative links (starting with /)
                    if link.startswith('/'):
                        link = base_url + link
                        
                    elif not link.startswith('http'):
                        link = path + link            
    
                    if not link.endswith(".gz"):
                        if not link in unscraped and not link in scraped:
                            unscraped.append(link)
                    # select max number of links
                    unscraped = collections.deque(itertools.islice(unscraped, 0, max_links))
                    
                    print(unscraped, len(unscraped))
                    len_unscraped = len(unscraped)
              
    #print(emails_list)
    return(emails_list)

# google search 
from googlesearch import search

# to search
query = "naturopath health practitioner contact"

urls = []
for j in search(query, tld="co.in", num=10, start=5, stop=20, pause=2):
    urls.append(j)

urls = list(set(urls))
print(urls)

#urls = ['http://www.ggpi.org/news.php', 'https://www.gasu.ru/']
emails_list = scrap_emails(urls, 10)

# filter out mail.ru - has anti-spam filtering
emails_list_f = [email for email in emails_list if not '@mail.ru' in email]
for substr in ['@example.com', '@email.com']:
    emails_list_f = [email for email in emails_list_f if not substr in email]
        
emails_set = list(set(emails_list_f))
print("Total emails collected:", len(emails_set))

for email in emails_set:
    print(email)

output_emails = open("output_emails.txt", "r")
content = output_emails.read()
existing_emails_list = content.split("\n")
output_emails.close()

with open('output_emails.txt', 'a') as f:
    f.write("\n")
    for email in emails_set:
        if email not in existing_emails_list:
            f.write(f"{email}\n")
