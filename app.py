"""
app.py — ScrapeKit v2.1
Warm editorial aesthetic. Price comparison + clickable Buy Now links.

"""
from dotenv import load_dotenv
load_dotenv()
import time, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd

from scrapers.flipkart_scraper import scrape_flipkart
from scrapers.news_scraper import scrape_news
from scrapers.github_scraper import scrape_github_trending, LANGUAGE_MAP, SINCE_MAP
from scrapers.price_comparator import compare_prices, PLATFORM_COLORS
from utils.helpers import dataframe_to_csv, dataframe_to_json, data_quality_report

st.set_page_config(
    page_title="ScrapeKit — Smart Shopping & Data Toolkit",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: #2C1810; }

.sk-header {
    background: linear-gradient(135deg, #C8602A 0%, #E8873A 40%, #D4702E 100%);
    border-radius: 20px; padding: 2.5rem 3rem; margin-bottom: 2rem;
    position: relative; overflow: hidden;
    box-shadow: 0 8px 32px rgba(200,96,42,0.25);
}
.sk-header::after {
    content: '◉'; position: absolute; right: 2rem; top: 50%;
    transform: translateY(-50%); font-size: 8rem;
    color: rgba(255,255,255,0.06); line-height: 1;
}
.sk-title {
    font-family: 'Playfair Display', serif; font-size: 2.8rem;
    font-weight: 800; color: #FFF8F0; margin: 0;
    line-height: 1.1; letter-spacing: -1px;
}
.sk-subtitle { color: rgba(255,248,240,0.75); font-size: 1rem; margin-top: 0.5rem; font-weight: 300; }

.sk-card {
    background: #FFFBF7; border: 1px solid #EAD9C8; border-radius: 14px;
    padding: 1.4rem 1.6rem; margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(44,24,16,0.06);
    transition: box-shadow 0.2s, transform 0.15s;
}
.sk-card:hover { box-shadow: 0 6px 20px rgba(200,96,42,0.12); transform: translateY(-1px); }

.best-deal-banner {
    background: linear-gradient(135deg, #2C7A3A, #3DAA52);
    border-radius: 14px; padding: 1.5rem 2rem; margin: 1rem 0;
    color: white; display: flex; align-items: center; gap: 1.5rem;
    box-shadow: 0 4px 16px rgba(44,122,58,0.2);
}
.best-deal-icon { font-size: 2.5rem; }
.best-deal-platform { font-family: 'DM Mono', monospace; font-size: 0.72rem; letter-spacing: 0.12em; opacity: 0.8; text-transform: uppercase; }
.best-deal-name { font-family: 'Playfair Display', serif; font-size: 1.1rem; font-weight: 700; line-height: 1.3; margin: 0.2rem 0; }
.best-deal-price { font-family: 'DM Mono', monospace; font-size: 1.8rem; font-weight: 500; color: #A8FFB8; }
.best-deal-link { display: inline-block; margin-top: 0.5rem; background: rgba(255,255,255,0.2); color: white !important; padding: 0.3rem 1rem; border-radius: 6px; font-size: 0.82rem; font-weight: 600; text-decoration: none !important; border: 1px solid rgba(255,255,255,0.3); }
.best-deal-link:hover { background: rgba(255,255,255,0.3); }

.plat-summary {
    background: #FFFBF7; border: 1px solid #EAD9C8; border-radius: 12px;
    padding: 1rem; text-align: center; border-top: 4px solid;
}
.plat-count { font-family: 'Playfair Display', serif; font-size: 1.8rem; font-weight: 700; line-height: 1; }
.plat-name { font-size: 0.78rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 0.2rem; opacity: 0.7; }
.plat-best-price { font-family: 'DM Mono', monospace; font-size: 0.85rem; margin-top: 0.4rem; font-weight: 500; }

.news-card {
    background: #FFFBF7; border: 1px solid #EAD9C8;
    border-left: 4px solid #C8602A; border-radius: 0 12px 12px 0;
    padding: 1.1rem 1.4rem; margin-bottom: 0.8rem;
}
.news-headline { font-family: 'Playfair Display', serif; font-size: 1rem; font-weight: 600; color: #2C1810; line-height: 1.4; margin-bottom: 0.4rem; }
.news-meta { font-size: 0.73rem; color: #8C6A58; margin-bottom: 0.5rem; }
.news-summary { font-size: 0.83rem; color: #5C3D2E; line-height: 1.55; }
.news-link { font-size: 0.75rem; color: #C8602A; text-decoration: none; font-weight: 600; }

.section-head {
    font-family: 'Playfair Display', serif; font-size: 1.4rem; font-weight: 700;
    color: #2C1810; margin: 1.5rem 0 0.8rem; padding-bottom: 0.4rem;
    border-bottom: 2px solid #EAD9C8;
}

.buy-btn {
    display: inline-block; background: #C8602A; color: white !important;
    padding: 0.3rem 0.9rem; border-radius: 6px; font-size: 0.75rem;
    font-weight: 600; text-decoration: none !important; font-family: 'DM Sans', sans-serif;
    transition: background 0.2s;
}
.buy-btn:hover { background: #A84A1A; }

.sk-warning {
    background: #FFFAEE; border: 1px solid #FFE4A0;
    border-left: 4px solid #E0A020; border-radius: 0 10px 10px 0;
    padding: 0.9rem 1.2rem; font-size: 0.85rem; color: #6A4A10; margin: 0.5rem 0;
}

.sk-footer {
    text-align: center; color: #8C6A58; font-size: 0.78rem;
    padding: 2.5rem 0 1rem; border-top: 1px solid #EAD9C8; margin-top: 3rem;
}
.sk-footer strong { color: #C8602A; }

[data-testid="stSidebar"] { background: #F5EDE2 !important; border-right: 1px solid #EAD9C8; }

.stButton > button {
    background: linear-gradient(135deg, #C8602A, #E8873A) !important;
    color: white !important; font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important; border: none !important; border-radius: 10px !important;
    padding: 0.6rem 1.8rem !important; box-shadow: 0 3px 12px rgba(200,96,42,0.3) !important;
}
.stButton > button:hover { opacity: 0.88 !important; }

.stDownloadButton > button {
    background: white !important; color: #C8602A !important;
    border: 1.5px solid #C8602A !important;
    font-family: 'DM Mono', monospace !important; font-size: 0.8rem !important;
    border-radius: 8px !important; padding: 0.4rem 1.1rem !important;
}

[data-testid="stDataFrame"] { border: 1px solid #EAD9C8 !important; border-radius: 10px !important; }
.stTextInput > div > div > input { background: #FFFBF7 !important; border-color: #D4B8A0 !important; border-radius: 8px !important; }
.stSelectbox > div > div { background: #FFFBF7 !important; }
.stMultiSelect > div > div { background: #FFFBF7 !important; }
.stSuccess { background: #F0FAF2 !important; border-color: #A8DFB0 !important; color: #1A4A22 !important; }
.stError   { background: #FFF0EE !important; border-color: #FFBFB0 !important; color: #7A2010 !important; }
.stWarning { background: #FFFAEE !important; border-color: #FFE4A0 !important; color: #6A4A10 !important; }
.stInfo    { background: #F5EDE2 !important; border-color: #D4B8A0 !important; color: #4A2C1A !important; }
hr { border-color: #EAD9C8 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k in ["results_df","last_mode","scrape_time","compare_data"]:
    if k not in st.session_state:
        st.session_state[k] = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="sk-header">
    <div class="sk-title">🔍 ScrapeKit</div>
    <div class="sk-subtitle">Smart shopping intelligence · Compare prices · Track news · Discover code</div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style="font-family:'Playfair Display',serif;font-size:1.2rem;
    font-weight:700;color:#2C1810;margin-bottom:1rem;">⚙️ Control Panel</div>""",
    unsafe_allow_html=True)

    mode = st.selectbox("Mode", [
        "🏷️ Price Comparator",
        "🛒 Flipkart Only",
        "📰 News Articles",
        "🐙 GitHub Trending",
    ])
    st.markdown("---")

    if mode == "🏷️ Price Comparator":
        st.markdown("**Search across platforms**")
        compare_query = st.text_input("Product name", value="wireless earbuds",
                                       placeholder="e.g. Sony headphones, iPhone 15")
        st.markdown("**Select platforms**")
        plat_snapdeal = st.checkbox("🔴 Snapdeal", value=True)
        plat_ebay     = st.checkbox("🔵 eBay",     value=True)
        plat_flipkart = st.checkbox("🟠 Flipkart",  value=True)
        plat_amazon   = st.checkbox("🟡 Amazon",    value=False)
        pages_compare = st.slider("Pages per platform", 1, 3, 1)
        selected_platforms = []
        if plat_snapdeal: selected_platforms.append("Snapdeal")
        if plat_ebay:     selected_platforms.append("eBay")
        if plat_flipkart: selected_platforms.append("Flipkart")
        if plat_amazon:   selected_platforms.append("Amazon")

    elif mode == "🛒 Flipkart Only":
        fk_query = st.text_input("Search term", value="wireless earbuds")
        fk_pages = st.slider("Pages to scrape", 1, 5, 2)

    elif mode == "📰 News Articles":
        news_query = st.text_input("Topic / keyword", value="artificial intelligence")
        max_articles = st.slider("Max articles", 10, 50, 25)

    elif mode == "🐙 GitHub Trending":
        language = st.selectbox("Language", list(LANGUAGE_MAP.keys()))
        since    = st.selectbox("Time range", list(SINCE_MAP.keys()))

    st.markdown("---")
    run_btn = st.button("▶  Run Scraper", use_container_width=True)
    st.markdown("---")
    st.markdown("""<div style="font-size:0.73rem;color:#8C6A58;line-height:1.9;">
    🌐 Live data from public websites<br>
    🔄 Parallel scraping (all platforms)<br>
    🛡️ Retry logic + rate limiting<br>
    🔗 Clickable Buy Now links<br>
    ⬇️ CSV &amp; JSON export
    </div>""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def render_downloads(df, prefix):
    c1, c2, _ = st.columns([1,1,3])
    with c1:
        st.download_button("⬇ CSV",  dataframe_to_csv(df),  f"{prefix}.csv",  "text/csv")
    with c2:
        st.download_button("⬇ JSON", dataframe_to_json(df), f"{prefix}.json", "application/json")


def render_quality(df):
    with st.expander("📊 Data Quality Report"):
        rpt = data_quality_report(df)
        try:
            styled = rpt.style.map(
                lambda v: ("color:#2C7A3A;font-weight:600" if isinstance(v,float) and v>=90
                      else "color:#C8602A;font-weight:600" if isinstance(v,float) and v>=60
                      else "color:#E04020;font-weight:600" if isinstance(v,float) else ""),
                subset=["Completeness %"]
            )
        except Exception:
            styled = rpt.style
        st.dataframe(styled, use_container_width=True, hide_index=True)


def render_news_cards(df):
    for _, row in df.iterrows():
        url = row.get("url","")
        link = f'<a class="news-link" href="{url}" target="_blank">Read article →</a>' if url and url != "N/A" else ""
        st.markdown(f"""
        <div class="news-card">
            <div class="news-headline">{row['headline']}</div>
            <div class="news-meta">📰 {row['source']} &nbsp;·&nbsp; 🕐 {row['published_date']}</div>
            <div class="news-summary">{row['summary']}</div><br>{link}
        </div>""", unsafe_allow_html=True)


def make_product_cards(df: pd.DataFrame, max_show: int = 5):
    """Render top N products as visual cards with Buy Now buttons."""
    st.markdown('<div class="section-head">🏅 Top Deals</div>', unsafe_allow_html=True)
    cols = st.columns(min(max_show, len(df)))
    for i, (_, row) in enumerate(df.head(max_show).iterrows()):
        color = PLATFORM_COLORS.get(row.get("platform",""), "#C8602A")
        url = row.get("url","")
        buy_btn = f'<a class="buy-btn" href="{url}" target="_blank">🛒 Buy Now</a>' if url and url != "N/A" else ""
        discount = row.get("discount","N/A")
        disc_html = f'<div style="color:#2C7A3A;font-size:0.75rem;font-weight:600;margin:0.2rem 0;">{discount}</div>' if discount and discount != "N/A" else ""
        rating = row.get("rating","N/A")
        rat_html = f'<div style="font-size:0.75rem;color:#8C6A58;">⭐ {rating}</div>' if rating and rating != "N/A" else ""
        with cols[i]:
            st.markdown(f"""
            <div class="sk-card" style="border-top:3px solid {color};min-height:200px;">
                <div style="font-size:0.68rem;font-weight:700;color:{color};
                            text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.4rem;">
                    {row.get('platform','')}
                </div>
                <div style="font-size:0.82rem;font-weight:600;color:#2C1810;
                            line-height:1.4;margin-bottom:0.5rem;min-height:50px;">
                    {str(row.get('name',''))[:80]}{'...' if len(str(row.get('name','')))>80 else ''}
                </div>
                <div style="font-family:'DM Mono',monospace;font-size:1.3rem;
                            font-weight:700;color:{color};">
                    {row.get('price','N/A')}
                </div>
                {disc_html}{rat_html}
                <div style="margin-top:0.8rem;">{buy_btn}</div>
            </div>""", unsafe_allow_html=True)


def render_compare_results(data, elapsed):
    all_df     = data["all_results"]
    best_deals = data["best_deals"]
    pcounts    = data["platform_counts"]
    errors     = data["errors"]
    cheapest   = data["cheapest"]
    total      = len(all_df)

    st.success(f"✅ Found **{total}** products across **{len([p for p,c in pcounts.items() if c>0])}** platforms in **{elapsed:.1f}s**")

    for e in errors:
        if "flipkart" in e.lower() and ("blocked" in e.lower() or "no results" in e.lower()):
            st.markdown('''<div class="sk-warning">
                🔒 <strong>Flipkart blocked</strong>: Your IP is flagged by Flipkart's bot detection.<br>
                <strong>Quick fix:</strong> Restart your WiFi router for a new IP, or use mobile hotspot.<br>
                <strong>Permanent fix:</strong> Get a free ScraperAPI key (1000 free credits/month) at
                <a href="https://www.scraperapi.com" target="_blank" style="color:#C8602A;font-weight:600;">scraperapi.com</a>
                → Set <code>SCRAPER_API_KEY=your_key</code> in a <code>.env</code> file in the project root → Restart app.
            </div>''', unsafe_allow_html=True)
        elif "ebay" in e.lower() and ("blocked" in e.lower() or "no results" in e.lower()):
            st.markdown(f'''<div class="sk-warning">
                ⚠️ <strong>eBay</strong>: No results returned. This may be a temporary issue.
                Try again in a few seconds.
            </div>''', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="sk-warning">⚠️ {e}</div>', unsafe_allow_html=True)

    # ── Best deal banner ──────────────────────────────────────────────────────
    if cheapest:
        name_s   = str(cheapest.get("name",""))[:70] + ("..." if len(str(cheapest.get("name","")))>70 else "")
        platform = cheapest.get("platform","")
        price    = cheapest.get("price","")
        savings  = cheapest.get("savings_vs_max","")
        url      = cheapest.get("url","")
        buy_link = f'<a class="best-deal-link" href="{url}" target="_blank">🛒 Buy Now →</a>' if url and url != "N/A" else ""
        st.markdown(f"""
        <div class="best-deal-banner">
            <div class="best-deal-icon">🏆</div>
            <div style="flex:1;">
                <div class="best-deal-platform">Best Deal — {platform}</div>
                <div class="best-deal-name">{name_s}</div>
                <div class="best-deal-price">{price}</div>
                {buy_link}
            </div>
            <div style="text-align:right;opacity:0.85;font-size:0.9rem;font-weight:600;">
                {savings}
            </div>
        </div>""", unsafe_allow_html=True)

    # ── Top 5 product cards ───────────────────────────────────────────────────
    if not all_df.empty:
        make_product_cards(all_df, max_show=5)

    # ── Platform summary ──────────────────────────────────────────────────────
    st.markdown('<div class="section-head">Platform Summary</div>', unsafe_allow_html=True)
    active = {p:c for p,c in pcounts.items() if c > 0}
    if active:
        pcols = st.columns(len(active))
        sorted_p = sorted(active.keys(), key=lambda p: (
            best_deals[best_deals["platform"]==p]["price_numeric"].values[0]
            if not best_deals.empty and len(best_deals[best_deals["platform"]==p]) > 0 else float("inf")
        ))
        for i, platform in enumerate(sorted_p):
            color = PLATFORM_COLORS.get(platform, "#C8602A")
            best_row = best_deals[best_deals["platform"]==platform]
            best_price = best_row["price"].values[0] if not best_row.empty else "N/A"
            best_name  = str(best_row["name"].values[0])[:35]+"..." if not best_row.empty and len(str(best_row["name"].values[0]))>35 else (best_row["name"].values[0] if not best_row.empty else "—")
            with pcols[i]:
                st.markdown(f"""
                <div class="plat-summary" style="border-top-color:{color};">
                    <div class="plat-count" style="color:{color};">{active[platform]}</div>
                    <div class="plat-name" style="color:{color};">{platform}</div>
                    <div class="plat-best-price">{best_price}</div>
                    <div style="font-size:0.7rem;color:#8C6A58;margin-top:0.3rem;line-height:1.3;">{best_name}</div>
                </div>""", unsafe_allow_html=True)

    # ── Full table with clickable links ───────────────────────────────────────
    st.markdown('<div class="section-head">All Results — Sorted by Price ↑</div>', unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        filter_platform = st.multiselect("Filter platform", options=list(pcounts.keys()), default=list(pcounts.keys()))
    with fc2:
        max_p = int(all_df["price_numeric"].max()) if not all_df.empty and all_df["price_numeric"].notna().any() else 100000
        max_p = max(max_p, 1)
        price_range = st.slider("Max price", 0, max_p, max_p)
    with fc3:
        only_stock = st.checkbox("In stock only", value=False)

    filtered = all_df[all_df["platform"].isin(filter_platform)]
    filtered = filtered[filtered["price_numeric"] <= price_range]
    if only_stock:
        filtered = filtered[filtered["in_stock"] == "Yes"]

    st.caption(f"Showing {len(filtered)} of {total} results")

    # Build display df — use LinkColumn for URLs
    display_cols = [c for c in filtered.columns if c not in ("price_numeric", "savings_vs_max")]
    display_df = filtered[display_cols].copy()

    # Streamlit LinkColumn for clickable URLs
    col_config = {}
    if "url" in display_df.columns:
        col_config["url"] = st.column_config.LinkColumn(
            "🔗 Buy Link",
            display_text="🛒 Buy Now",
            help="Click to open product page",
        )

    st.dataframe(display_df, use_container_width=True, hide_index=True, column_config=col_config)

    st.markdown("---")
    render_downloads(display_df, "price_comparison")
    render_quality(display_df)


# ── Run logic ─────────────────────────────────────────────────────────────────
if run_btn:
    st.session_state.results_df   = None
    st.session_state.compare_data = None

    if mode == "🏷️ Price Comparator":
        if not compare_query.strip():
            st.error("Please enter a product name.")
            st.stop()
        if not selected_platforms:
            st.error("Please select at least one platform.")
            st.stop()
        with st.spinner(f"Searching **{compare_query}** across {', '.join(selected_platforms)}... (15–40s)"):
            t0 = time.time()
            try:
                data = compare_prices(
                    query=compare_query.strip(),
                    platforms=selected_platforms,
                    pages_per_platform=pages_compare,
                    timeout_per_platform=35,
                )
                elapsed = time.time() - t0
            except Exception as e:
                st.error(f"Comparison failed: {str(e)}")
                st.stop()
        if data["all_results"].empty:
            st.warning("No results found. Try a different search term.")
            st.stop()
        st.session_state.compare_data = data
        st.session_state.scrape_time  = elapsed
        st.session_state.last_mode    = "compare"

    elif mode == "🛒 Flipkart Only":
        if not fk_query.strip():
            st.error("Please enter a search term.")
            st.stop()
        with st.spinner(f"Scraping Flipkart for **{fk_query}**..."):
            t0 = time.time()
            try:
                df = scrape_flipkart(fk_query.strip(), pages=fk_pages)
                elapsed = time.time() - t0
            except Exception as e:
                st.error(f"Scraping failed: {str(e)}")
                st.stop()
        if df.empty:
            st.warning("No products found. Try a different search term or check your connection.")
            st.stop()
        st.session_state.results_df  = df
        st.session_state.scrape_time = elapsed
        st.session_state.last_mode   = "flipkart"

    elif mode == "📰 News Articles":
        if not news_query.strip():
            st.error("Please enter a topic.")
            st.stop()
        with st.spinner(f"Fetching news about **{news_query}**..."):
            t0 = time.time()
            try:
                df = scrape_news(news_query.strip(), max_articles=max_articles)
                elapsed = time.time() - t0
            except Exception as e:
                st.error(f"Scraping failed: {str(e)}")
                st.stop()
        if df.empty:
            st.warning("No articles found. Try a different keyword.")
            st.stop()
        st.session_state.results_df  = df
        st.session_state.scrape_time = elapsed
        st.session_state.last_mode   = "news"

    elif mode == "🐙 GitHub Trending":
        with st.spinner(f"Scraping GitHub Trending — {language} — {since}..."):
            t0 = time.time()
            try:
                df = scrape_github_trending(language=language, since=since)
                elapsed = time.time() - t0
            except Exception as e:
                st.error(f"Scraping failed: {str(e)}")
                st.stop()
        if df.empty:
            st.warning("No repositories found.")
            st.stop()
        st.session_state.results_df  = df
        st.session_state.scrape_time = elapsed
        st.session_state.last_mode   = "github"


# ── Display results ───────────────────────────────────────────────────────────
if st.session_state.last_mode == "compare" and st.session_state.compare_data:
    render_compare_results(st.session_state.compare_data, st.session_state.scrape_time or 0)

elif st.session_state.results_df is not None:
    df     = st.session_state.results_df
    elapsed = st.session_state.scrape_time or 0
    mode_k  = st.session_state.last_mode

    c1,c2,c3 = st.columns(3)
    c1.metric("Results", len(df))
    c2.metric("Scrape Time", f"{elapsed:.1f}s")
    c3.metric("Columns", len(df.columns))
    st.markdown("---")

    # Build column config for URL links
    col_config = {}
    if "url" in df.columns:
        col_config["url"] = st.column_config.LinkColumn(
            "🔗 Link",
            display_text="Open →",
            help="Click to open",
        )

    if mode_k == "news":
        view = st.radio("View as", ["📋 Table","🗞️ Cards"], horizontal=True, label_visibility="collapsed")
        if view == "🗞️ Cards":
            render_news_cards(df)
        else:
            st.dataframe(df, use_container_width=True, hide_index=True, column_config=col_config)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True, column_config=col_config)

    st.markdown("---")
    prefix = {"flipkart":"flipkart_products","news":"news_articles","github":"github_trending"}.get(mode_k,"results")
    render_downloads(df, prefix)
    render_quality(df)

else:
    # Landing page
    st.markdown('<div class="section-head">What can ScrapeKit do?</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    for col, (icon, color, title, desc) in zip([c1,c2,c3,c4], [
        ("🏷️","#C8602A","Price Comparator","Compare any product across Snapdeal, eBay, Flipkart & Amazon. Ranked by price with one-click Buy Now links."),
        ("🛒","#F7941D","Flipkart Deep Dive","Multi-page Flipkart scraper with ratings, reviews, discount data and direct product links."),
        ("📰","#5C8A3A","News Intelligence","Pull live headlines, sources and summaries for any topic via Google News RSS."),
        ("🐙","#4A3A8C","GitHub Trending","Track rising repos by language and time range. Stars, forks, topics and more."),
    ]):
        with col:
            st.markdown(f"""
            <div class="sk-card" style="border-top:4px solid {color};">
                <div style="font-size:2rem;margin-bottom:0.5rem;">{icon}</div>
                <div style="font-family:'Playfair Display',serif;font-weight:700;font-size:1rem;color:#2C1810;margin-bottom:0.5rem;">{title}</div>
                <div style="font-size:0.82rem;color:#5C3D2E;line-height:1.6;">{desc}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:1.5rem;padding:1.2rem 1.6rem;background:#F5EDE2;border-radius:12px;
                border:1px solid #EAD9C8;text-align:center;color:#5C3D2E;font-size:0.88rem;">
        👈 Pick a mode from the sidebar and hit <strong style="color:#C8602A;">Run Scraper</strong>
    </div>""", unsafe_allow_html=True)

st.markdown("""
<div class="sk-footer">
    Built by <strong>Pooja Dheniya</strong> &nbsp;·&nbsp; ScrapeKit v2.1 &nbsp;·&nbsp;
    Streamlit · BeautifulSoup · Parallel scraping · Live data
</div>""", unsafe_allow_html=True)
