from .snapdeal_scraper import scrape_snapdeal
from .ebay_scraper import scrape_ebay
from .flipkart_scraper import scrape_flipkart
from .amazon_scraper import scrape_amazon
from .price_comparator import compare_prices, PLATFORM_COLORS
from .news_scraper import scrape_news
from .github_scraper import scrape_github_trending

__all__ = [
    "scrape_snapdeal", "scrape_ebay", "scrape_flipkart", "scrape_amazon",
    "compare_prices", "PLATFORM_COLORS", "scrape_news", "scrape_github_trending"
]
