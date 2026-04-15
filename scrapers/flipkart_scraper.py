"""
flipkart_scraper.py — Flipkart Product Scraper
Two modes:
1. DIRECT: Works when IP not blocked. Falls back gracefully.
2. SCRAPERAPI: Uses free ScraperAPI proxy (1000 free credits/month).
   Get free key at: https://www.scraperapi.com (takes 30 seconds)
   Set SCRAPER_API_KEY in .env or pass directly.
"""
import time, random, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from utils.helpers import clean_price

BASE       = "https://www.flipkart.com"
SEARCH_URL = "https://www.flipkart.com/search"

# Optional: set your ScraperAPI key here or in .env
# Get free key at https://www.scraperapi.com — 1000 free credits/month
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "")

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def _fetch_via_scraperapi(url: str, params: dict) -> Optional[requests.Response]:
    """Route request through ScraperAPI to bypass CAPTCHA."""
    if not SCRAPER_API_KEY:
        return None
    try:
        import urllib.parse
        target = url + "?" + urllib.parse.urlencode(params)
        r = requests.get(
            "https://api.scraperapi.com",
            params={
                "api_key":  SCRAPER_API_KEY,
                "url":      target,
                "country_code": "in",
                "render":   "false",
            },
            timeout=30,
        )
        if r.status_code == 200 and len(r.text) > 5000:
            return r
    except Exception:
        pass
    return None


def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent":      random.choice(UA_POOL),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection":      "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control":   "no-cache",
    })
    try:
        s.get(BASE, timeout=8)
        time.sleep(random.uniform(1, 2))
    except Exception:
        pass
    return s


def _parse_html(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    products = []

    # Pass 1: CSS selectors (multiple layout variants)
    cards = (
        soup.find_all("div", {"class": re.compile(r"tUxRFH|_75nlfW|CGtC98|_1xHGtK|_4ddWXP|_2kHMtA")}) or
        soup.find_all("div", {"class": re.compile(r"_1AtVbE|yKfJKb|_13oc-S|DOjaWF")}) or
        soup.find_all("div", {"data-id": True})
    )

    for card in cards:
        try:
            name = None
            for cls in [re.compile(r"KzDlHZ|wjcEIp|_4rR01T|s1Q9rs|IRpwTa|WKTcLC|lymLMd|a9UBell")]:
                t = card.find(["div","a","span"], {"class": cls})
                if t:
                    n = t.get_text(strip=True)
                    if n and len(n) > 4:
                        name = n; break
            if not name: continue

            lnk = card.find("a", href=re.compile(r"/p/")) or card.find("a", href=True)
            url = (BASE + lnk["href"]) if lnk else "N/A"

            pt = card.find(["div","span"], {"class": re.compile(r"Nx9bqj|_30jeq3|_1_WHN1|koV_if|hl05au|_3qQ9m1")})
            price_str = pt.get_text(strip=True) if pt else None
            if not price_str: continue
            price_num = clean_price(price_str)

            ot = card.find(["div","span"], {"class": re.compile(r"yRaY8j|_3I9_wc|_2p6lqe|_3auQ3N")})
            orig_str = ot.get_text(strip=True) if ot else "N/A"

            dt = card.find(["div","span"], {"class": re.compile(r"UkUFwK|_3Ay6Sb|_1cv_pj|VGWI4j")})
            if dt:
                discount = dt.get_text(strip=True)
            else:
                cur = price_num; ori = clean_price(orig_str)
                discount = f"{round(((ori-cur)/ori)*100)}% off" if cur and ori and ori > cur else "N/A"

            rt = card.find(["div","span"], {"class": re.compile(r"XQDdHH|_3LWZlK|gUuXy-|_2d4LTz")})
            rating = "N/A"
            if rt:
                m = re.search(r"([1-5]\.\d)", rt.get_text(strip=True))
                if m: rating = m.group(1)

            products.append({
                "platform": "Flipkart", "name": name,
                "price": price_str, "price_numeric": price_num,
                "original_price": orig_str, "discount": discount,
                "rating": rating, "reviews": "N/A",
                "in_stock": "Yes", "url": url,
            })
        except Exception:
            continue

    if products:
        return products

    # Pass 2: ₹ price DOM walker
    seen = set()
    bad = {"login","cart","wishlist","home","offer","deal","category","brand","filter","sort"}
    for pt in soup.find_all(string=re.compile(r"₹[\d,]+")):
        try:
            parent = pt.parent
            for _ in range(10):
                if parent is None: break
                nt = parent.find(["a","div","span"], string=re.compile(r"[A-Za-z]{4,}"))
                if nt:
                    name = nt.get_text(strip=True)
                    if len(name) > 6 and name not in seen and not any(w in name.lower() for w in bad):
                        lnk = parent.find("a", href=re.compile(r"/p/"))
                        seen.add(name)
                        price_str = str(pt).strip()
                        products.append({
                            "platform": "Flipkart", "name": name,
                            "price": price_str, "price_numeric": clean_price(price_str),
                            "original_price": "N/A", "discount": "N/A",
                            "rating": "N/A", "reviews": "N/A",
                            "in_stock": "Yes",
                            "url": (BASE + lnk["href"]) if lnk else "N/A",
                        })
                        break
                parent = parent.parent
        except Exception:
            continue
    return products


def scrape_flipkart(query: str, pages: int = 2) -> pd.DataFrame:
    """
    Scrape Flipkart with automatic CAPTCHA bypass if ScraperAPI key is set.
    Without key: works when IP is not blocked.
    With free ScraperAPI key: works always, permanently.
    Get free key (1000 credits/month): https://www.scraperapi.com
    """
    all_products: List[Dict] = []

    for page in range(1, pages + 1):
        page_products = []
        params = {"q": query, "page": page, "sort": "relevance"}

        # Method 1: ScraperAPI (if key is set — bypasses CAPTCHA permanently)
        if SCRAPER_API_KEY and not page_products:
            r = _fetch_via_scraperapi(SEARCH_URL, params)
            if r:
                page_products = _parse_html(r.text)

        # Method 2: Direct request
        if not page_products:
            for attempt in range(2):
                try:
                    if attempt > 0:
                        time.sleep(random.uniform(3, 5))
                    s = _make_session()
                    r = s.get(SEARCH_URL, params=params, timeout=15)
                    if r.status_code == 200 and "captcha" not in r.text.lower() and len(r.text) > 5000:
                        page_products = _parse_html(r.text)
                        if page_products:
                            break
                except Exception:
                    continue

        if page_products:
            all_products.extend(page_products)
        elif page == 1:
            break

        if page < pages:
            time.sleep(random.uniform(2, 3))

    if not all_products:
        return pd.DataFrame()

    df = pd.DataFrame(all_products)
    df = df[df["price_numeric"].notna()]
    return df.drop_duplicates(subset=["name"]).reset_index(drop=True)
