"""
snapdeal_scraper.py — Snapdeal Product Scraper (confirmed working, 200 status)
"""
import time, random, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from utils.helpers import clean_price, get_random_headers

BASE = "https://www.snapdeal.com"
SEARCH_URL = "https://www.snapdeal.com/search"

def scrape_snapdeal(query: str, pages: int = 2) -> pd.DataFrame:
    """Scrape Snapdeal search results."""
    all_products = []

    for page in range(1, pages + 1):
        headers = get_random_headers(referer="https://www.snapdeal.com/")
        try:
            r = requests.get(
                SEARCH_URL,
                params={"keyword": query, "pageNum": page, "sort": "rlvncy"},
                headers=headers,
                timeout=15,
            )
            if r.status_code != 200:
                break
        except Exception:
            break

        soup = BeautifulSoup(r.text, "lxml")

        # Multiple selector attempts for Snapdeal's layout
        cards = (
            soup.find_all("div", {"class": re.compile(r"product-tuple-listing")}) or
            soup.find_all("div", {"class": re.compile(r"product-tuple-description")}) or
            soup.find_all("div", {"class": re.compile(r"col-xs-6.*product|jasmine-card")}) or
            soup.find_all("div", {"class": "product-tuple-listing js-tuple"})
        )

        if not cards:
            # Try finding all divs with data-id (product identifiers)
            cards = soup.find_all("div", {"data-id": True})

        for card in cards:
            try:
                # Name
                name_tag = (
                    card.find("p", {"class": re.compile(r"product-title")}) or
                    card.find("p", {"class": "product-title"}) or
                    card.find(["p", "span", "a"], {"class": re.compile(r"title")})
                )
                if not name_tag:
                    continue
                name = name_tag.get_text(strip=True)
                if not name or len(name) < 4:
                    continue

                # URL
                lnk = (
                    card.find("a", {"class": re.compile(r"dp-widget-link|product-link")}) or
                    card.find("a", href=re.compile(r"/product/"))
                )
                if lnk:
                    href = lnk.get("href", "")
                    url = href if href.startswith("http") else BASE + href
                else:
                    url = "N/A"

                # Price
                price_tag = (
                    card.find("span", {"class": re.compile(r"lfloat product-price|product-price")}) or
                    card.find("span", {"class": "lfloat product-price"}) or
                    card.find(["span", "div"], {"class": re.compile(r"price-val|payBlkBig")})
                )
                price_str = price_tag.get_text(strip=True) if price_tag else "N/A"
                price_num = clean_price(price_str)
                if not price_num:
                    continue

                # Original price
                orig_tag = (
                    card.find("span", {"class": re.compile(r"product-desc-mrp|strike|slash")}) or
                    card.find("s", {"class": True})
                )
                orig_str = orig_tag.get_text(strip=True) if orig_tag else "N/A"

                # Discount
                disc_tag = card.find(["span", "div"], {"class": re.compile(r"product-discount|discount-txt")})
                if disc_tag:
                    discount = disc_tag.get_text(strip=True)
                else:
                    ori = clean_price(orig_str)
                    if price_num and ori and ori > price_num:
                        discount = f"{round(((ori - price_num) / ori) * 100)}% off"
                    else:
                        discount = "N/A"

                # Rating — Snapdeal uses filled-stars width % style
                rating = "N/A"
                rat_tag = card.find(["div", "span"], {"class": re.compile(r"filled-stars")})
                if rat_tag:
                    style = rat_tag.get("style", "")
                    m = re.search(r"width:\s*(\d+)%", style)
                    if m:
                        rating = str(round(int(m.group(1)) / 20, 1))

                all_products.append({
                    "platform": "Snapdeal",
                    "name": name,
                    "price": price_str,
                    "price_numeric": price_num,
                    "original_price": orig_str,
                    "discount": discount,
                    "rating": rating,
                    "reviews": "N/A",
                    "in_stock": "Yes",
                    "url": url,
                })
            except Exception:
                continue

        if page < pages:
            time.sleep(random.uniform(1, 2))

    if not all_products:
        return pd.DataFrame()

    df = pd.DataFrame(all_products)
    return df.drop_duplicates(subset=["name"]).reset_index(drop=True)
