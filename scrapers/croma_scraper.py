"""
croma_scraper.py — Croma Product Scraper
Croma uses a relatively stable layout. Scrapes search results cleanly.
"""

import time, random, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from utils.helpers import clean_price, get_random_headers

BASE = "https://www.croma.com"
SEARCH_URL = "https://www.croma.com/searchB"


def scrape_croma(query: str, pages: int = 2) -> pd.DataFrame:
    """Scrape Croma search results. Returns DataFrame with platform, name, price, etc."""
    all_products = []

    for page in range(0, pages):
        params = {
            "q": query + ":relevance",
            "currentPage": page,
        }
        headers = get_random_headers(referer="https://www.croma.com/")
        try:
            r = requests.get(SEARCH_URL, params=params, headers=headers, timeout=15)
            if r.status_code != 200:
                break
        except Exception:
            break

        soup = BeautifulSoup(r.text, "lxml")

        # Croma product cards
        cards = (
            soup.find_all("li", {"class": re.compile(r"product-item|cp-product")}) or
            soup.find_all("div", {"class": re.compile(r"product-item|plp-card")})
        )

        if not cards:
            break

        for card in cards:
            try:
                # Name
                name_tag = (
                    card.find(["h3","h4","a"], {"class": re.compile(r"product-title|pdpLink|cp-product__title")}) or
                    card.find("a", {"class": re.compile(r"title|name")})
                )
                if not name_tag:
                    continue
                name = name_tag.get_text(strip=True)
                if not name or len(name) < 4:
                    continue

                # URL
                lnk = card.find("a", href=True)
                url = (BASE + lnk["href"]) if lnk and lnk["href"].startswith("/") else (lnk["href"] if lnk else "N/A")

                # Price
                price_tag = card.find(["span","div"], {"class": re.compile(r"pdp-price|new-price|amount|cp-price|offer-price")})
                price_str = price_tag.get_text(strip=True) if price_tag else "N/A"
                price_num = clean_price(price_str)
                if not price_num:
                    continue

                # Original price
                orig_tag = card.find(["span","div"], {"class": re.compile(r"old-price|mrp|strike|cp-mrp")})
                orig_str = orig_tag.get_text(strip=True) if orig_tag else "N/A"

                # Discount
                ori = clean_price(orig_str)
                if price_num and ori and ori > price_num:
                    discount = f"{round(((ori - price_num) / ori) * 100)}% off"
                else:
                    discount = "N/A"

                # Rating
                rat_tag = card.find(["span","div"], {"class": re.compile(r"rating|star|review-count")})
                rating = "N/A"
                if rat_tag:
                    m = re.search(r"([1-5]\.\d|\d\.?\d*)\s*(out of|\/)?\s*5?", rat_tag.get_text(strip=True))
                    if m:
                        try:
                            val = float(m.group(1))
                            if 1.0 <= val <= 5.0:
                                rating = str(val)
                        except Exception:
                            pass

                all_products.append({
                    "platform": "Croma",
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

        if page < pages - 1:
            time.sleep(random.uniform(1, 2))

    if not all_products:
        return pd.DataFrame()

    df = pd.DataFrame(all_products)
    return df.drop_duplicates(subset=["name"]).reset_index(drop=True)
