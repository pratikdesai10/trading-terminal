"""Module 15: News & Sentiment (Bloomberg: TOP / NEWS)."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from time import mktime

import feedparser
import streamlit as st

from config import COLORS
from utils.logger import logger

# ── RSS Feed Sources ──
FEEDS = {
    "Moneycontrol": "https://www.moneycontrol.com/rss/marketreports.xml",
    "ET Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "LiveMint": "https://www.livemint.com/rss/markets",
    "Business Standard": "https://www.business-standard.com/rss/markets-106.rss",
}

# ── Category keywords for filtering ──
CATEGORY_KEYWORDS = {
    "Markets": ["market", "nifty", "sensex", "bse", "nse", "index", "indices", "rally",
                 "trading", "bull", "bear", "benchmark", "intraday", "closing"],
    "Stocks": ["stock", "share", "equity", "ipo", "buyback", "dividend", "listing",
               "stake", "promoter", "quarter", "results", "earnings"],
    "Economy": ["economy", "gdp", "rbi", "inflation", "fiscal", "budget", "tax",
                "rate", "repo", "monetary", "policy", "growth", "reform", "rupee"],
    "Global": ["global", "us ", "fed", "china", "crude", "oil", "dollar", "euro",
               "ftse", "nasdaq", "dow", "s&p", "wall street", "imf", "world",
               "foreign", "fii", "geopolitical", "tariff", "trade war"],
}

# ── Sentiment keyword lists ──
POSITIVE_WORDS = [
    "surge", "surges", "surging", "rally", "rallies", "rallied", "gain", "gains",
    "jump", "jumps", "jumped", "bullish", "soar", "soars", "soared", "rise",
    "rises", "rising", "climbs", "up", "boom", "booming", "record high",
    "outperform", "upgrade", "recovery", "recovers", "positive", "profit",
    "growth", "strong", "strength", "optimism", "upbeat", "hits high",
    "all-time high", "breakout", "buying", "advances",
]

NEGATIVE_WORDS = [
    "crash", "crashes", "crashed", "fall", "falls", "fell", "drop", "drops",
    "dropped", "bear", "bearish", "loss", "losses", "tumble", "tumbles",
    "tumbled", "plunge", "plunges", "plunged", "decline", "declines",
    "declining", "sink", "sinks", "slump", "slumps", "slumped", "weak",
    "weakness", "down", "downgrade", "sell-off", "selloff", "panic",
    "crisis", "fear", "negative", "worst", "low", "hits low", "correction",
    "warning", "risk", "deficit", "debt", "recession",
]


def render():
    """Render the News & Sentiment module."""
    st.markdown("### NEWS & SENTIMENT")

    # ── Filter controls ──
    col_cat, col_source, col_sentiment = st.columns(3)

    with col_cat:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">'
            f'CATEGORY</p>',
            unsafe_allow_html=True,
        )
        category = st.selectbox(
            "CATEGORY", ["All", "Markets", "Stocks", "Economy", "Global"],
            label_visibility="collapsed",
        )

    with col_source:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">'
            f'SOURCE</p>',
            unsafe_allow_html=True,
        )
        source = st.selectbox(
            "SOURCE", ["All"] + list(FEEDS.keys()),
            label_visibility="collapsed",
        )

    with col_sentiment:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">'
            f'SENTIMENT</p>',
            unsafe_allow_html=True,
        )
        sentiment_filter = st.selectbox(
            "SENTIMENT", ["All", "Positive", "Negative", "Neutral"],
            label_visibility="collapsed",
        )

    st.markdown(
        f'<div style="border-bottom:1px solid {COLORS["border"]};margin:4px 0 8px 0"></div>',
        unsafe_allow_html=True,
    )

    # ── Fetch news ──
    with st.spinner("Fetching news feeds..."):
        articles = _fetch_all_feeds()

    if not articles:
        st.warning("Unable to fetch news feeds. Please try again later.")
        return

    # ── Apply filters ──
    filtered = articles

    if source != "All":
        filtered = [a for a in filtered if a["source"] == source]

    if category != "All":
        cat_kw = CATEGORY_KEYWORDS.get(category, [])
        filtered = [
            a for a in filtered
            if any(kw in a["title"].lower() for kw in cat_kw)
        ]

    if sentiment_filter != "All":
        filtered = [a for a in filtered if a["sentiment"] == sentiment_filter]

    # ── Summary bar ──
    _render_sentiment_summary(articles, filtered)

    # ── News list ──
    if not filtered:
        st.info("No articles match the selected filters.")
        return

    _render_news_ticker(filtered)

    # ── Footer ──
    st.markdown(
        f'<div style="color:{COLORS["muted"]};font-size:10px;margin-top:12px;'
        f'border-top:1px solid {COLORS["border"]};padding-top:6px">'
        f'Sources: Moneycontrol, Economic Times, LiveMint, Business Standard '
        f'| Auto-refresh: 5 min | Sentiment: keyword-based (indicative only)'
        f'</div>',
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_all_feeds():
    """Fetch and parse all RSS feeds. Returns sorted list of article dicts."""
    logger.info("m15_news | fetching all RSS feeds")
    all_articles = []

    def _fetch_single(name, url):
        try:
            feed = feedparser.parse(url)
            items = []
            for entry in feed.entries[:25]:  # Cap per source
                title = entry.get("title", "").strip()
                if not title:
                    continue
                link = entry.get("link", "")
                published = _parse_published(entry)
                sentiment = _score_sentiment(title)
                items.append({
                    "title": title,
                    "link": link,
                    "published": published,
                    "source": name,
                    "sentiment": sentiment,
                })
            logger.info(f"m15_news | {name} | {len(items)} articles")
            return items
        except Exception as e:
            logger.error(f"m15_news | {name} | {type(e).__name__}: {e}")
            return []

    # Fetch feeds in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_fetch_single, name, url): name
            for name, url in FEEDS.items()
        }
        for future in as_completed(futures):
            result = future.result()
            all_articles.extend(result)

    # Sort by published date (newest first)
    all_articles.sort(key=lambda a: a["published"], reverse=True)
    logger.info(f"m15_news | total {len(all_articles)} articles fetched")
    return all_articles


def _parse_published(entry):
    """Extract published datetime from a feed entry."""
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                pass
    # Fallback: use current time
    return datetime.now(tz=timezone.utc)


def _score_sentiment(title):
    """Score sentiment of a headline using word-boundary matching.

    Returns 'Positive', 'Negative', or 'Neutral'.
    """
    import re
    lower = title.lower()
    pos = sum(1 for w in POSITIVE_WORDS if re.search(r'\b' + re.escape(w) + r'\b', lower))
    neg = sum(1 for w in NEGATIVE_WORDS if re.search(r'\b' + re.escape(w) + r'\b', lower))

    if pos > neg:
        return "Positive"
    elif neg > pos:
        return "Negative"
    return "Neutral"


def _render_sentiment_summary(all_articles, filtered):
    """Render sentiment breakdown bar at the top."""
    total = len(all_articles)
    pos_count = sum(1 for a in all_articles if a["sentiment"] == "Positive")
    neg_count = sum(1 for a in all_articles if a["sentiment"] == "Negative")
    neu_count = total - pos_count - neg_count

    c1, c2, c3, c4 = st.columns(4)

    c1.markdown(
        f'<div style="text-align:center">'
        f'<div style="color:{COLORS["muted"]};font-size:10px">TOTAL</div>'
        f'<div style="color:{COLORS["text"]};font-size:18px;font-family:monospace">'
        f'{len(filtered)}<span style="color:{COLORS["muted"]};font-size:12px">/{total}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        f'<div style="text-align:center">'
        f'<div style="color:{COLORS["muted"]};font-size:10px">POSITIVE</div>'
        f'<div style="color:{COLORS["green"]};font-size:18px;font-family:monospace">{pos_count}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    c3.markdown(
        f'<div style="text-align:center">'
        f'<div style="color:{COLORS["muted"]};font-size:10px">NEGATIVE</div>'
        f'<div style="color:{COLORS["red"]};font-size:18px;font-family:monospace">{neg_count}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    c4.markdown(
        f'<div style="text-align:center">'
        f'<div style="color:{COLORS["muted"]};font-size:10px">NEUTRAL</div>'
        f'<div style="color:{COLORS["muted"]};font-size:18px;font-family:monospace">{neu_count}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Sentiment bar
    if total > 0:
        pos_pct = pos_count / total * 100
        neg_pct = neg_count / total * 100
        st.markdown(
            f'<div style="display:flex;height:6px;border-radius:3px;overflow:hidden;'
            f'margin:6px 0 10px 0">'
            f'<div style="width:{pos_pct}%;background:{COLORS["green"]}"></div>'
            f'<div style="width:{neg_pct}%;background:{COLORS["red"]}"></div>'
            f'<div style="flex:1;background:{COLORS["border"]}"></div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_news_ticker(articles):
    """Render news articles as a Bloomberg-style scrollable ticker list."""
    rows_html = ""

    for article in articles:
        title = _escape_html(article["title"])
        source = article["source"]
        link = article["link"]
        sentiment = article["sentiment"]
        time_str = _format_time_ago(article["published"])

        # Sentiment indicator
        if sentiment == "Positive":
            sent_color = COLORS["green"]
            sent_icon = "+"
        elif sentiment == "Negative":
            sent_color = COLORS["red"]
            sent_icon = "-"
        else:
            sent_color = COLORS["muted"]
            sent_icon = "~"

        rows_html += (
            f'<div style="display:flex;align-items:flex-start;padding:8px 10px;'
            f'border-bottom:1px solid {COLORS["panel"]};'
            f'font-family:\'Fira Code\',Consolas,\'Courier New\',monospace">'
            # Sentiment dot
            f'<div style="min-width:22px;color:{sent_color};font-size:14px;'
            f'font-weight:bold;padding-top:1px">{sent_icon}</div>'
            # Headline
            f'<div style="flex:1;min-width:0">'
            f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
            f'style="color:{COLORS["text"]};text-decoration:none;font-size:13px;'
            f'line-height:1.4;display:block;overflow:hidden;text-overflow:ellipsis">'
            f'{title}</a>'
            f'</div>'
            # Source + time
            f'<div style="min-width:140px;text-align:right;padding-left:12px;'
            f'white-space:nowrap">'
            f'<span style="color:{COLORS["amber"]};font-size:10px">{source}</span>'
            f'<br>'
            f'<span style="color:{COLORS["muted"]};font-size:10px">{time_str}</span>'
            f'</div>'
            f'</div>'
        )

    # Wrap in scrollable container
    st.markdown(
        f'<div style="border:1px solid {COLORS["border"]};border-radius:4px;'
        f'max-height:600px;overflow-y:auto;background:{COLORS["bg"]}">'
        # Header row
        f'<div style="display:flex;padding:6px 10px;'
        f'border-bottom:1px solid {COLORS["amber"]};'
        f'font-family:\'Fira Code\',Consolas,\'Courier New\',monospace">'
        f'<div style="min-width:22px;color:{COLORS["amber"]};font-size:10px">S</div>'
        f'<div style="flex:1;color:{COLORS["amber"]};font-size:10px">HEADLINE</div>'
        f'<div style="min-width:140px;text-align:right;color:{COLORS["amber"]};'
        f'font-size:10px">SOURCE / TIME</div>'
        f'</div>'
        # Articles
        f'{rows_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _format_time_ago(dt):
    """Format a datetime as relative time string (e.g. '2h ago')."""
    now = datetime.now(tz=timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 0:
        return "just now"
    elif seconds < 60:
        return f"{seconds}s ago"
    elif seconds < 3600:
        return f"{seconds // 60}m ago"
    elif seconds < 86400:
        return f"{seconds // 3600}h ago"
    elif seconds < 604800:
        days = seconds // 86400
        return f"{days}d ago"
    else:
        return dt.strftime("%d %b %Y")


def _escape_html(text):
    """Escape HTML special characters in text."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
