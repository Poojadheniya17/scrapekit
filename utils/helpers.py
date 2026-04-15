"""
helpers.py — Common utilities for ScrapeKit
Retry logic, price cleaning, CSV/JSON export, header rotation, data quality reporting.
"""

import time
import random
import re
import io
import requests
import pandas as pd
from typing import Optional, Dict

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]


def get_random_headers(referer: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def retry_request(
    url: str,
    headers: Optional[Dict] = None,
    params: Optional[Dict] = None,
    max_retries: int = 3,
    timeout: int = 15,
    session: Optional[requests.Session] = None,
) -> Optional[requests.Response]:
    if headers is None:
        headers = get_random_headers()

    requester = session if session else requests

    for attempt in range(1, max_retries + 1):
        try:
            response = requester.get(url, headers=headers, params=params, timeout=timeout)
            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                time.sleep((2 ** attempt) + random.uniform(1, 3))
            elif response.status_code in (403, 401):
                headers = get_random_headers()
                time.sleep(random.uniform(2, 4))
            else:
                time.sleep(random.uniform(1, 2))
        except requests.exceptions.ConnectionError:
            time.sleep(random.uniform(2, 4))
        except requests.exceptions.Timeout:
            time.sleep(random.uniform(1, 3))
        except requests.exceptions.RequestException:
            time.sleep(random.uniform(1, 2))

    return None


def clean_price(price_string: str) -> Optional[float]:
    if not price_string or not isinstance(price_string, str):
        return None
    cleaned = re.sub(r"[^\d.,]", "", price_string.strip())
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def dataframe_to_csv(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, encoding="utf-8")
    return buffer.getvalue().encode("utf-8")


def dataframe_to_json(df: pd.DataFrame) -> bytes:
    return df.to_json(orient="records", indent=2, force_ascii=False).encode("utf-8")


def data_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    rows = []
    for col in df.columns:
        non_null = df[col].notna().sum()
        valid = df[col].apply(lambda x: bool(x) and str(x).strip() not in ("", "N/A", "nan", "None")).sum()
        completeness = round((valid / total) * 100, 1) if total > 0 else 0.0
        rows.append({
            "Column": col,
            "Non-Null": non_null,
            "Valid Values": valid,
            "Completeness %": completeness,
        })
    return pd.DataFrame(rows)


def normalize_product_name(name: str) -> str:
    """Lowercase, strip punctuation for fuzzy deduplication."""
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name
