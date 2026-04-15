"""
amazon_scraper.py — Amazon.in Product Scraper
CONFIRMED from user's live HTML:
- _c2Itd_item_3Z9mf      → product card (new React layout)
- _c2Itd_price_3jDlv     → price
- _c2Itd_itemInfo_1g6UG  → product info
- _c2Itd_productWrapper_2YcYM → wrapper
- a-price-whole / a-price-fraction → price digits
- s-result-item          → classic layout fallback
Uses BOTH layouts with auto-detection.
"""
import time, random, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from utils.helpers import clean_price

BASE       = "https://www.amazon.in"
SEARCH_URL = "https://www.amazon.in/s"

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def _get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent":      random.choice(UA_POOL),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection":      "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control":   "max-age=0",
    })
    try:
        s.get(BASE, timeout=8)
        time.sleep(random.uniform(0.8, 1.5))
    except Exception:
        pass
    return s


def _get_price(card) -> tuple:
    """Extract price using every known Amazon price pattern."""
    # Pattern 1: whole + fraction (most common)
    whole = card.find("span", {"class": "a-price-whole"})
    if whole:
        frac = card.find("span", {"class": "a-price-fraction"})
        w = whole.get_text(strip=True).replace(",", "").rstrip(".")
        f = frac.get_text(strip=True) if frac else "00"
        price_str = f"₹{w}.{f}"
        num = clean_price(price_str)
        if num:
            return price_str, num

    # Pattern 2: _c2Itd_price class (new React layout - confirmed in user's HTML)
    price_div = card.find(["div","span"], {"class": re.compile(r"_c2Itd_price|_c2Itd_priceWrapper")})
    if price_div:
        txt = price_div.get_text(strip=True)
        num = clean_price(txt)
        if num:
            return txt, num

    # Pattern 3: a-offscreen (accessibility fallback, always present)
    for span in card.find_all("span", {"class": "a-offscreen"}):
        txt = span.get_text(strip=True)
        num = clean_price(txt)
        if num and num > 0:
            return txt, num

    # Pattern 4: any span containing ₹
    for span in card.find_all("span"):
        txt = span.get_text(strip=True)
        if "₹" in txt and re.search(r"₹[\d,]+", txt):
            num = clean_price(txt)
            if num and num > 0:
                return txt, num

    return "N/A", None


def _extract_new_layout(card) -> Optional[Dict]:
    """
    Parse Amazon's NEW React layout using _c2Itd_ classes.
    Confirmed from user's live HTML: _c2Itd_item_3Z9mf, _c2Itd_itemInfo_1g6UG
    """
    # Name from itemInfo div
    info = card.find(["div","span"], {"class": re.compile(r"_c2Itd_itemInfo|_c2Itd_item")})
    if not info:
        return None

    name_tag = info.find(["span","div","a"], string=re.compile(r"[A-Za-z]{3,}"))
    if not name_tag:
        return None
    name = name_tag.get_text(strip=True)
    if not name or len(name) < 5:
        return None

    price_str, price_num = _get_price(card)
    if not price_num:
        return None

    lnk = card.find("a", href=re.compile(r"/dp/"))
    url = "N/A"
    if lnk:
        href = lnk["href"]
        dp = re.search(r"(/dp/[A-Z0-9]{10})", href)
        url = BASE + dp.group(1) if dp else (BASE + href if href.startswith("/") else href)

    # Rating
    rt = card.find("span", {"class": "a-icon-alt"})
    rating = "N/A"
    if rt:
        m = re.search(r"([1-5]\.\d)", rt.get_text(strip=True))
        if m: rating = m.group(1)

    return {
        "platform": "Amazon", "name": name,
        "price": price_str, "price_numeric": price_num,
        "original_price": "N/A", "discount": "N/A",
        "rating": rating, "reviews": "N/A",
        "in_stock": "Yes", "url": url,
    }


def _extract_classic_layout(card) -> Optional[Dict]:
    """Parse Amazon's classic layout using s-result-item / data-asin."""
    # Skip ads
    if card.get("data-component-type") == "sp-sponsored-result":
        return None

    # Name
    name_tag = (
        card.find("h2") or
        card.find("span", {"class": "a-size-medium a-color-base a-text-normal"}) or
        card.find("span", {"class": "a-size-base-plus a-color-base a-text-normal"}) or
        card.find("span", {"class": re.compile(r"a-size-medium.*a-text-normal|a-size-base-plus.*a-text-normal")})
    )
    if not name_tag:
        return None
    name = name_tag.get_text(strip=True)
    if not name or len(name) < 4:
        return None

    price_str, price_num = _get_price(card)
    if not price_num:
        return None

    # URL
    lnk = card.find("a", href=re.compile(r"/dp/"))
    url = "N/A"
    if lnk:
        href = lnk["href"]
        dp = re.search(r"(/dp/[A-Z0-9]{10})", href)
        url = BASE + dp.group(1) if dp else (BASE + href if href.startswith("/") else href)

    # Original price
    orig_tag = card.find("span", {"class": re.compile(r"a-text-price")})
    orig_str = "N/A"
    if orig_tag:
        inner = orig_tag.find("span", {"class": "a-offscreen"})
        orig_str = inner.get_text(strip=True) if inner else orig_tag.get_text(strip=True)

    # Discount
    ori = clean_price(orig_str)
    discount = f"{round(((ori-price_num)/ori)*100)}% off" if ori and ori > price_num else "N/A"

    # Rating
    rt = card.find("span", {"class": "a-icon-alt"})
    rating = "N/A"
    if rt:
        m = re.search(r"([1-5]\.\d)", rt.get_text(strip=True))
        if m: rating = m.group(1)

    # Reviews
    rev_tag = card.find("span", {"aria-label": re.compile(r"\d+")})
    reviews = "N/A"
    if rev_tag:
        m = re.search(r"([\d,]+)", rev_tag.get("aria-label",""))
        if m: reviews = m.group(1).replace(",","")

    return {
        "platform": "Amazon", "name": name,
        "price": price_str, "price_numeric": price_num,
        "original_price": orig_str, "discount": discount,
        "rating": rating, "reviews": reviews,
        "in_stock": "Yes", "url": url,
    }


def _parse_page(soup: BeautifulSoup) -> List[Dict]:
    products = []

    # Strategy 1: New React layout (_c2Itd_ classes confirmed in user's HTML)
    new_cards = soup.find_all(["div","li"], {"class": re.compile(r"_c2Itd_item_|_c2Itd_productWrapper")})
    if new_cards:
        for card in new_cards:
            try:
                p = _extract_new_layout(card)
                if p: products.append(p)
            except Exception:
                continue
        if products:
            return products

    # Strategy 2: Classic layout with data-asin
    classic_cards = soup.find_all("div", {"data-asin": re.compile(r"[A-Z0-9]{10}")})
    for card in classic_cards:
        try:
            p = _extract_classic_layout(card)
            if p: products.append(p)
        except Exception:
            continue
    if products:
        return products

    # Strategy 3: Any element with a-price-whole (guaranteed to be a product)
    seen = set()
    for price_el in soup.find_all("span", {"class": "a-price-whole"}):
        try:
            parent = price_el.parent
            for _ in range(8):
                if parent is None: break
                name_tag = parent.find("h2") or parent.find("span", string=re.compile(r"[A-Za-z]{5,}"))
                if name_tag:
                    name = name_tag.get_text(strip=True)
                    if len(name) > 5 and name not in seen:
                        price_str, price_num = _get_price(parent)
                        if price_num:
                            lnk = parent.find("a", href=re.compile(r"/dp/"))
                            url = "N/A"
                            if lnk:
                                dp = re.search(r"(/dp/[A-Z0-9]{10})", lnk["href"])
                                url = BASE + dp.group(1) if dp else BASE + lnk["href"]
                            seen.add(name)
                            products.append({
                                "platform": "Amazon", "name": name,
                                "price": price_str, "price_numeric": price_num,
                                "original_price": "N/A", "discount": "N/A",
                                "rating": "N/A", "reviews": "N/A",
                                "in_stock": "Yes", "url": url,
                            })
                            break
                parent = parent.parent
        except Exception:
            continue

    return products


def scrape_amazon(query: str, pages: int = 2) -> pd.DataFrame:
    """
    Scrape Amazon.in. Uses confirmed class names from live HTML inspection.
    Handles both old and new React layout automatically.
    """
    session = _get_session()
    all_products: List[Dict] = []

    for page in range(1, pages + 1):
        try:
            r = session.get(
                SEARCH_URL,
                params={"k": query, "page": page, "ref": f"sr_pg_{page}"},
                timeout=20,
            )
            if r.status_code != 200 or "captcha" in r.text.lower():
                break
        except Exception:
            break

        soup = BeautifulSoup(r.text, "lxml")
        page_products = _parse_page(soup)

        if not page_products:
            break

        all_products.extend(page_products)
        if page < pages:
            time.sleep(random.uniform(2, 3))

    if not all_products:
        return pd.DataFrame()

    df = pd.DataFrame(all_products)
    df = df[df["price_numeric"].notna()]
    return df.drop_duplicates(subset=["name"]).reset_index(drop=True)
