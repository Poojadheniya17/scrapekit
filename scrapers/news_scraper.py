"""
news_scraper.py — Google News RSS Article Scraper
Fetches recent news articles for a given topic using the Google News RSS feed.

Uses feedparser for robust XML parsing. Extracts: headline, source, published date,
article URL, and summary. Returns a clean pandas DataFrame.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import time
import random
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Optional

import feedparser
import pandas as pd
from bs4 import BeautifulSoup

from utils.helpers import retry_request, get_random_headers

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


def _clean_summary(raw_html: str) -> str:
    """
    Strips HTML tags from a raw summary string and trims whitespace.
    Returns plain text summary, truncated to 300 characters.
    """
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "lxml")
    text = soup.get_text(separator=" ", strip=True)
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300] + ("..." if len(text) > 300 else "")


def _parse_date(date_str: str) -> str:
    """
    Parses various RSS date formats into a clean 'YYYY-MM-DD HH:MM' string.
    Falls back to the raw string if parsing fails.
    """
    if not date_str:
        return "Unknown"
    # feedparser provides a parsed time struct
    try:
        import email.utils
        dt = email.utils.parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    # Try strptime fallbacks
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return date_str[:16] if len(date_str) > 16 else date_str


def _extract_real_url(google_url: str) -> str:
    """
    Google News RSS links are Google redirect URLs.
    Attempts to extract the canonical article URL from the redirect.
    Falls back to the Google URL if extraction fails.
    """
    # Many Google News links contain the real URL as a query parameter
    try:
        parsed = urllib.parse.urlparse(google_url)
        params = urllib.parse.parse_qs(parsed.query)
        if "url" in params:
            return params["url"][0]
    except Exception:
        pass
    return google_url


def scrape_news(query: str, max_articles: int = 25) -> pd.DataFrame:
    """
    Scrapes Google News RSS for the given topic/keyword.

    Args:
        query: News search topic (e.g., "artificial intelligence", "climate change")
        max_articles: Maximum number of articles to return (default: 25)

    Returns:
        pandas DataFrame with columns:
        headline, source, published_date, summary, url
    """
    encoded_query = urllib.parse.quote_plus(query)
    rss_url = f"{GOOGLE_NEWS_RSS}?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    headers = get_random_headers()
    headers["Accept"] = "application/rss+xml, application/xml, text/xml, */*"

    response = retry_request(rss_url, headers=headers)

    if response is None:
        return pd.DataFrame(columns=["headline", "source", "published_date", "summary", "url"])

    # Parse with feedparser (handles encoding, malformed XML, etc.)
    feed = feedparser.parse(response.text)

    if not feed.entries:
        return pd.DataFrame(columns=["headline", "source", "published_date", "summary", "url"])

    articles: List[Dict] = []
    entries = feed.entries[:max_articles]

    for entry in entries:
        try:
            # Headline
            headline = getattr(entry, "title", "").strip()
            if not headline:
                continue

            # Source — Google News includes source in title as "Headline - Source"
            source = "Unknown"
            if " - " in headline:
                parts = headline.rsplit(" - ", 1)
                headline = parts[0].strip()
                source = parts[1].strip()
            elif hasattr(entry, "source") and hasattr(entry.source, "title"):
                source = entry.source.title

            # URL
            raw_url = getattr(entry, "link", "")
            url = _extract_real_url(raw_url) if raw_url else ""

            # Published Date
            pub_date = ""
            if hasattr(entry, "published"):
                pub_date = _parse_date(entry.published)
            elif hasattr(entry, "updated"):
                pub_date = _parse_date(entry.updated)

            # Summary
            summary = ""
            if hasattr(entry, "summary"):
                summary = _clean_summary(entry.summary)
            elif hasattr(entry, "description"):
                summary = _clean_summary(entry.description)

            # If summary is just the headline repeated, clear it
            if summary.strip().lower().startswith(headline.lower()[:30].lower()):
                summary = ""

            articles.append({
                "headline": headline,
                "source": source,
                "published_date": pub_date,
                "summary": summary if summary else "No summary available",
                "url": url,
            })

        except Exception:
            continue

    if not articles:
        return pd.DataFrame(columns=["headline", "source", "published_date", "summary", "url"])

    df = pd.DataFrame(articles)
    df = df.drop_duplicates(subset=["headline"]).reset_index(drop=True)
    return df
