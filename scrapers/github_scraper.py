"""
github_scraper.py — GitHub Trending Repositories Scraper
Scrapes the GitHub Trending page for popular repositories filtered by language and time range.

Extracts: repo name, author, description, language, total stars, stars today, forks,
topics/tags, and repo URL. Returns a clean pandas DataFrame.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import time
from typing import List, Dict, Optional

import pandas as pd
from bs4 import BeautifulSoup

from utils.helpers import retry_request, get_random_headers

GITHUB_TRENDING_URL = "https://github.com/trending"

LANGUAGE_MAP = {
    "All": "",
    "Python": "python",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "Rust": "rust",
    "Go": "go",
    "Java": "java",
    "C++": "c++",
    "C": "c",
    "Kotlin": "kotlin",
    "Swift": "swift",
}

SINCE_MAP = {
    "Daily": "daily",
    "Weekly": "weekly",
    "Monthly": "monthly",
}


def _parse_star_count(text: str) -> Optional[int]:
    """
    Parses star count strings like '1,234', '12.3k', '1.2m' into integers.
    Returns None if parsing fails.
    """
    if not text:
        return None
    text = text.strip().replace(",", "").lower()
    try:
        if "k" in text:
            return int(float(text.replace("k", "")) * 1000)
        elif "m" in text:
            return int(float(text.replace("m", "")) * 1_000_000)
        else:
            match = re.search(r"(\d+)", text)
            return int(match.group(1)) if match else None
    except (ValueError, AttributeError):
        return None


def scrape_github_trending(language: str = "All", since: str = "Daily") -> pd.DataFrame:
    """
    Scrapes GitHub Trending page for popular repositories.

    Args:
        language: Programming language filter. One of: All, Python, JavaScript,
                  TypeScript, Rust, Go, Java, C++, C, Kotlin, Swift
        since: Time range. One of: Daily, Weekly, Monthly

    Returns:
        pandas DataFrame with columns:
        rank, repo_name, author, description, language, total_stars,
        stars_today, forks, topics, url
    """
    lang_slug = LANGUAGE_MAP.get(language, "")
    since_slug = SINCE_MAP.get(since, "daily")

    url = GITHUB_TRENDING_URL
    if lang_slug:
        url += f"/{lang_slug}"

    params = {"since": since_slug}
    headers = get_random_headers(referer="https://github.com/")

    response = retry_request(url, headers=headers, params=params)

    if response is None:
        return pd.DataFrame(columns=[
            "rank", "repo_name", "author", "description", "language",
            "total_stars", "stars_today", "forks", "topics", "url"
        ])

    soup = BeautifulSoup(response.text, "lxml")

    # GitHub trending repos are in <article class="Box-row"> elements
    repo_articles = soup.find_all("article", {"class": re.compile(r"Box-row")})

    if not repo_articles:
        return pd.DataFrame(columns=[
            "rank", "repo_name", "author", "description", "language",
            "total_stars", "stars_today", "forks", "topics", "url"
        ])

    repos: List[Dict] = []

    for rank, article in enumerate(repo_articles, start=1):
        try:
            repo = {"rank": rank}

            # ── Repo Name & Author ────────────────────────────────────────────
            title_tag = article.find("h2", {"class": re.compile(r"h3|lh-condensed")}) or article.find("h1")
            if not title_tag:
                continue

            link_tag = title_tag.find("a", href=True)
            if not link_tag:
                continue

            href = link_tag["href"].strip().lstrip("/")
            parts = href.split("/")
            repo["author"] = parts[0] if len(parts) > 0 else "Unknown"
            repo["repo_name"] = parts[1] if len(parts) > 1 else href
            repo["url"] = f"https://github.com/{href}"

            # ── Description ───────────────────────────────────────────────────
            desc_tag = article.find("p", {"class": re.compile(r"col-9|my-1|lh-1")})
            if not desc_tag:
                desc_tag = article.find("p")
            repo["description"] = desc_tag.get_text(strip=True) if desc_tag else "No description"

            # ── Language ──────────────────────────────────────────────────────
            lang_tag = article.find("span", {"itemprop": "programmingLanguage"})
            if not lang_tag:
                # Try finding the language color dot's sibling text
                lang_span = article.find("span", {"class": re.compile(r"d-inline-block.*ml-0")})
                lang_tag = lang_span
            repo["language"] = lang_tag.get_text(strip=True) if lang_tag else "Unknown"

            # ── Stars (Total) ─────────────────────────────────────────────────
            star_link = article.find("a", href=re.compile(r"/stargazers"))
            if star_link:
                repo["total_stars"] = _parse_star_count(star_link.get_text(strip=True))
            else:
                # Fallback: look for star SVG octicon sibling
                star_svg = article.find("svg", {"class": re.compile(r"octicon-star")})
                if star_svg:
                    star_text = star_svg.parent.get_text(strip=True)
                    repo["total_stars"] = _parse_star_count(star_text)
                else:
                    repo["total_stars"] = None

            # ── Forks ─────────────────────────────────────────────────────────
            fork_link = article.find("a", href=re.compile(r"/forks"))
            if fork_link:
                repo["forks"] = _parse_star_count(fork_link.get_text(strip=True))
            else:
                fork_svg = article.find("svg", {"class": re.compile(r"octicon-repo-forked")})
                if fork_svg:
                    fork_text = fork_svg.parent.get_text(strip=True)
                    repo["forks"] = _parse_star_count(fork_text)
                else:
                    repo["forks"] = None

            # ── Stars Today ───────────────────────────────────────────────────
            stars_today_span = article.find("span", {"class": re.compile(r"d-inline-block.*float-sm-right|f6.*color-fg-muted")})
            if stars_today_span:
                today_text = stars_today_span.get_text(strip=True)
                if "star" in today_text.lower():
                    repo["stars_today"] = _parse_star_count(today_text)
                else:
                    repo["stars_today"] = None
            else:
                # Search all spans for "stars today" pattern
                for span in article.find_all("span"):
                    text = span.get_text(strip=True)
                    if "stars" in text.lower() and "today" in text.lower():
                        repo["stars_today"] = _parse_star_count(text)
                        break
                else:
                    repo["stars_today"] = None

            # ── Topics ────────────────────────────────────────────────────────
            topic_tags = article.find_all("a", {"class": re.compile(r"topic-tag")})
            repo["topics"] = ", ".join(t.get_text(strip=True) for t in topic_tags) if topic_tags else ""

            repos.append(repo)

        except Exception:
            continue

    if not repos:
        return pd.DataFrame(columns=[
            "rank", "repo_name", "author", "description", "language",
            "total_stars", "stars_today", "forks", "topics", "url"
        ])

    df = pd.DataFrame(repos)
    col_order = ["rank", "repo_name", "author", "description", "language",
                 "total_stars", "stars_today", "forks", "topics", "url"]
    for col in col_order:
        if col not in df.columns:
            df[col] = None
    return df[col_order].reset_index(drop=True)
