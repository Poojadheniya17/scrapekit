"""
price_comparator.py — Multi-Platform Price Comparison Engine
Runs all platform scrapers in parallel threads. Gracefully handles blocked platforms.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

from scrapers.snapdeal_scraper import scrape_snapdeal
from scrapers.ebay_scraper import scrape_ebay
from scrapers.flipkart_scraper import scrape_flipkart
from scrapers.amazon_scraper import scrape_amazon

PLATFORM_COLORS = {
    "Snapdeal": "#E40046",
    "eBay":     "#E53238",
    "Flipkart": "#F7941D",
    "Amazon":   "#FF9900",
}

PLATFORM_SCRAPERS = {
    "Snapdeal": scrape_snapdeal,
    "eBay":     scrape_ebay,
    "Flipkart": scrape_flipkart,
    "Amazon":   scrape_amazon,
}


def compare_prices(
    query: str,
    platforms: List[str] = None,
    pages_per_platform: int = 1,
    timeout_per_platform: int = 35,
) -> Dict:
    """
    Scrapes selected platforms in parallel. Returns unified price comparison.

    Args:
        query: Product search term
        platforms: List of platform names (default: all 4)
        pages_per_platform: Pages per platform (1 = ~20-24 products)
        timeout_per_platform: Max seconds per platform before skipping

    Returns:
        dict with all_results, best_deals, platform_counts, errors, cheapest
    """
    if platforms is None:
        platforms = list(PLATFORM_SCRAPERS.keys())

    platforms = [p for p in platforms if p in PLATFORM_SCRAPERS]
    results, errors, platform_counts = [], [], {}

    def _scrape(platform):
        fn = PLATFORM_SCRAPERS[platform]
        try:
            df = fn(query, pages=pages_per_platform)
            return platform, df, None
        except Exception as e:
            return platform, pd.DataFrame(), str(e)

    with ThreadPoolExecutor(max_workers=max(len(platforms), 1)) as executor:
        futures = {executor.submit(_scrape, p): p for p in platforms}
        for future in as_completed(futures, timeout=timeout_per_platform * 2):
            p = futures[future]
            try:
                platform, df, err = future.result(timeout=timeout_per_platform)
                if err:
                    errors.append(f"{platform}: {err}")
                    platform_counts[platform] = 0
                elif not df.empty:
                    results.append(df)
                    platform_counts[platform] = len(df)
                else:
                    platform_counts[platform] = 0
                    errors.append(f"{platform}: No results (blocked or no matches)")
            except Exception as e:
                errors.append(f"{p}: {str(e)}")
                platform_counts[p] = 0

    if not results:
        return {
            "all_results": pd.DataFrame(),
            "best_deals": pd.DataFrame(),
            "platform_counts": platform_counts,
            "errors": errors,
            "cheapest": None,
        }

    combined = pd.concat(results, ignore_index=True)
    combined["price_numeric"] = pd.to_numeric(combined["price_numeric"], errors="coerce")

    sorted_df = (
        combined.dropna(subset=["price_numeric"])
        .sort_values("price_numeric", ascending=True)
        .reset_index(drop=True)
    )
    sorted_df.insert(0, "rank", range(1, len(sorted_df) + 1))

    if not sorted_df.empty:
        max_p = sorted_df["price_numeric"].max()
        sorted_df["savings_vs_max"] = sorted_df["price_numeric"].apply(
            lambda x: f"Save ₹{int(max_p - x):,}" if (max_p - x) > 0 else "—"
        )

    best_deals = (
        sorted_df.groupby("platform").first().reset_index().sort_values("price_numeric")
        if not sorted_df.empty else pd.DataFrame()
    )
    cheapest = sorted_df.iloc[0].to_dict() if not sorted_df.empty else None

    return {
        "all_results": sorted_df,
        "best_deals": best_deals,
        "platform_counts": platform_counts,
        "errors": errors,
        "cheapest": cheapest,
    }
