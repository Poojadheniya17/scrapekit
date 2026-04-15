"""
ebay_scraper.py — eBay Product Scraper
Confirmed working: status=200, 1.5MB HTML on user's machine.
Uses exhaustive selector strategy to find s-item cards.
"""
import time, random, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import pandas as pd
from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Optional
from utils.helpers import clean_price

SEARCH_URL = "https://www.ebay.com/sch/i.html"
BASE_URL   = "https://www.ebay.com"


def _get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection":      "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control":   "max-age=0",
        "Referer":         "https://www.ebay.com/",
    })
    try:
        s.get("https://www.ebay.com", timeout=8)
        time.sleep(random.uniform(0.5, 1.0))
    except Exception:
        pass
    return s


def _has_class(el: Tag, cls: str) -> bool:
    """Check if element has a class that CONTAINS cls as substring."""
    return any(cls in c for c in el.get("class", []))


def _find_item_cards(soup: BeautifulSoup) -> List[Tag]:
    """
    Exhaustive search for eBay product cards.
    eBay's HTML is 1.5MB with 60+ products — they are definitely there.
    Tries every known selector pattern.
    """
    # Strategy 1: Standard eBay list items with s-item class (most reliable)
    cards = [el for el in soup.find_all("li")
             if any("s-item" in c for c in el.get("class", []))]
    if len(cards) > 3:
        # Filter out injected placeholder li's eBay adds
        cards = [c for c in cards if not (
            len(c.get("class", [])) == 1 and c.get("class", [""])[0] == "s-item"
        ) or c.find("h3") or c.find("span", string=re.compile(r'\$'))]
        if cards:
            return cards

    # Strategy 2: Any li containing a price span and a heading
    cards = []
    for li in soup.find_all("li"):
        has_price = li.find("span", string=re.compile(r'\$[\d,]+'))
        has_title = li.find(["h3", "h2"]) or li.find("span", {"role": "heading"})
        if has_price and has_title:
            cards.append(li)
    if cards:
        return cards

    # Strategy 3: divs with s-item__wrapper (inner wrapper eBay uses)
    wrappers = soup.find_all("div", {"class": re.compile(r"s-item__wrapper")})
    if wrappers:
        return wrappers

    # Strategy 4: Any element with a link to /itm/ AND a price
    cards = []
    seen = set()
    for a in soup.find_all("a", href=re.compile(r"ebay\.(com|in)/itm/")):
        parent = a.parent
        for _ in range(5):
            if parent is None:
                break
            pid = id(parent)
            if pid not in seen and parent.find(string=re.compile(r'\$[\d,]+')):
                seen.add(pid)
                cards.append(parent)
                break
            parent = parent.parent
    if cards:
        return cards

    return []


def _extract_item(card: Tag) -> Optional[Dict]:
    """Extract all fields from a single eBay product card."""

    # ── Name ──────────────────────────────────────────────────────────────────
    name_tag = (
        card.find("h3", {"class": re.compile(r"s-item__title")}) or
        card.find("h3") or
        card.find("h2") or
        card.find("span", {"class": re.compile(r"s-item__title|x-item-title")}) or
        card.find("span", {"role": "heading"})
    )
    if not name_tag:
        return None
    name = name_tag.get_text(strip=True)
    # eBay injects fake items with these titles
    bad_titles = {"shop on ebay", "new listing", "", "sponsored"}
    if not name or len(name) < 5 or name.lower() in bad_titles:
        return None

    # ── URL ───────────────────────────────────────────────────────────────────
    lnk = (
        card.find("a", {"class": re.compile(r"s-item__link")}, href=True) or
        card.find("a", href=re.compile(r"ebay\.(com|in)/itm/"))
    )
    if lnk:
        url = lnk["href"].split("?")[0]  # strip tracking params
    else:
        url = "N/A"

    # ── Price ─────────────────────────────────────────────────────────────────
    price_tag = (
        card.find("span", {"class": re.compile(r"s-item__price")}) or
        card.find("span", {"class": re.compile(r"x-price-primary|notranslate")}) or
        card.find("span", string=re.compile(r'\$[\d,]+'))
    )
    if not price_tag:
        return None
    price_str = price_tag.get_text(strip=True) if hasattr(price_tag, "get_text") else str(price_tag)
    # Handle price ranges like "$10.00 to $25.00" — take the lower
    price_str = re.split(r"\s+to\s+", price_str, flags=re.IGNORECASE)[0].strip()
    price_num = clean_price(price_str)
    if not price_num or price_num <= 0:
        return None

    # ── Condition ─────────────────────────────────────────────────────────────
    cond_tag = card.find("span", {"class": re.compile(r"s-item__condition|SECONDARY_INFO")})
    condition = cond_tag.get_text(strip=True) if cond_tag else "N/A"

    # ── Shipping ──────────────────────────────────────────────────────────────
    ship_tag = card.find("span", {"class": re.compile(r"s-item__shipping|s-item__freeXDays|s-item__logisticsCost")})
    shipping = ship_tag.get_text(strip=True) if ship_tag else "N/A"

    # ── Sold count (used as reviews proxy) ───────────────────────────────────
    sold_tag = card.find("span", {"class": re.compile(r"s-item__quantitySold|s-item__hotness")})
    reviews = sold_tag.get_text(strip=True) if sold_tag else "N/A"

    return {
        "platform":      "eBay",
        "name":          name,
        "price":         price_str,
        "price_numeric": price_num,
        "original_price":"N/A",
        "discount":      "N/A",
        "rating":        "N/A",
        "reviews":       reviews,
        "in_stock":      "Yes",
        "condition":     condition,
        "shipping":      shipping,
        "url":           url,
    }


def scrape_ebay(query: str, pages: int = 2) -> pd.DataFrame:
    """
    Scrape eBay search results. Confirmed working (status=200, 1.5MB HTML).
    Uses exhaustive multi-strategy card detection.
    """
    session = _get_session()
    all_products: List[Dict] = []

    for page in range(1, pages + 1):
        try:
            r = session.get(
                SEARCH_URL,
                params={
                    "_nkw":   query,
                    "_sacat": "0",
                    "_pgn":   page,
                    "_ipg":   "60",
                    "LH_TitleDesc": "0",
                },
                timeout=20,
            )
            if r.status_code != 200:
                break
        except Exception:
            break

        soup = BeautifulSoup(r.text, "lxml")
        cards = _find_item_cards(soup)

        page_products = []
        for card in cards:
            try:
                p = _extract_item(card)
                if p:
                    page_products.append(p)
            except Exception:
                continue

        if not page_products:
            break

        all_products.extend(page_products)
        if page < pages:
            time.sleep(random.uniform(1.5, 2.5))

    if not all_products:
        return pd.DataFrame()

    df = pd.DataFrame(all_products)
    return df.drop_duplicates(subset=["name"]).reset_index(drop=True)
