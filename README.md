# 🔍 ScrapeKit v2.1 — Smart Shopping & Data Toolkit

A production-ready web scraping toolkit built with Streamlit. Compare prices across platforms, scrape news, and track GitHub trends — all in one warm, editorial UI.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🏷️ Price Comparator | Snapdeal + eBay + Flipkart + Amazon in parallel |
| 🛒 Flipkart Scraper | Mobile API bypass + HTML fallback |
| 📰 News Scraper | Google News RSS via feedparser |
| 🐙 GitHub Trending | Stars, forks, topics, language filter |
| 🔗 Buy Now Links | Clickable product links in every table |
| ⬇️ Export | CSV + JSON download |
| 📊 Data Quality | Per-column completeness report |

---

## 🚀 Local Setup

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/scrapekit.git
cd scrapekit

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python -m streamlit run app.py
```

App opens at `http://localhost:8501`

---

## ☁️ Deploy on Streamlit Cloud (Free)

1. Push repo to GitHub (public)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click **New app**
5. Select repo → branch `main` → Main file: `app.py`
6. Click **Deploy**

Live in ~2 minutes. No extra config needed.

---

## 📁 Structure

```
scrapekit/
├── app.py                        # Streamlit frontend
├── requirements.txt
├── .streamlit/config.toml        # Warm theme config
├── scrapers/
│   ├── flipkart_scraper.py       # Mobile API + HTML fallback
│   ├── amazon_scraper.py         # Amazon.in scraper
│   ├── ebay_scraper.py           # eBay scraper (confirmed working)
│   ├── snapdeal_scraper.py       # Snapdeal scraper (confirmed working)
│   ├── price_comparator.py       # Parallel multi-platform engine
│   ├── news_scraper.py           # Google News RSS
│   └── github_scraper.py         # GitHub Trending
└── utils/
    └── helpers.py                # Retry, price parsing, export, quality
```

---

## 🛠️ Tech Stack

Streamlit · requests · BeautifulSoup4 · feedparser · pandas · lxml · ThreadPoolExecutor

---

## ⚠️ Notes

- **Flipkart**: Uses internal mobile API to bypass reCAPTCHA. If blocked, try on a different network or VPN.
- **Amazon**: May be blocked on some networks. Uncheck if not needed.
- **Snapdeal + eBay**: Confirmed working without blocks.
- Built for educational and personal use. Always check a site's ToS before scraping.

---

**Built by Pooja Dheniya** — Electronics & Telecommunication Engineering, DJSCE Mumbai
