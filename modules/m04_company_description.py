"""Module 04: Company Description (Bloomberg: DES)."""

import streamlit as st

from config import NIFTY_50_SYMBOLS, COLORS
from utils.formatting import format_inr, format_crore


def render():
    """Render the Company Description module."""
    st.markdown("### COMPANY DESCRIPTION")

    symbol = st.selectbox("SYMBOL", NIFTY_50_SYMBOLS, index=0, key="m04_symbol")

    from data.fundamentals import get_company_info
    with st.spinner("Loading company data..."):
        info = get_company_info(symbol)

    if info is None:
        st.warning(f"No data available for {symbol}. yfinance may be rate-limited.")
        return

    _render_header(info, symbol)
    st.markdown("---")
    _render_key_stats(info)
    st.markdown("---")
    _render_description(info)


def _safe(info, key, fmt_fn=None, default="—"):
    """Safely extract and format a value from info dict."""
    val = info.get(key)
    if val is None:
        return default
    try:
        if fmt_fn:
            return fmt_fn(val)
        return str(val)
    except Exception:
        return default


def _render_header(info, symbol):
    """Display company name, sector, industry, and current price."""
    name = info.get("longName") or info.get("shortName") or symbol
    sector = info.get("sector", "—")
    industry = info.get("industry", "—")

    price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
    prev = info.get("previousClose", 0)
    change = price - prev if price and prev else 0
    pct = (change / prev * 100) if prev else 0
    color = COLORS["green"] if change >= 0 else COLORS["red"]

    st.markdown(
        f'<div style="margin-bottom:12px">'
        f'<div style="color:#FF9900;font-size:20px;font-weight:bold;font-family:monospace">{name}</div>'
        f'<div style="color:#888;font-size:12px;margin-top:2px">{symbol} | {sector} | {industry}</div>'
        f'<div style="margin-top:8px">'
        f'<span style="font-size:28px;font-family:monospace;color:{color}">₹{price:,.2f}</span>'
        f'<span style="font-size:14px;font-family:monospace;color:{color};margin-left:12px">'
        f'{change:+.2f} ({pct:+.2f}%)</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _render_key_stats(info):
    """Display key statistics in a 4-column grid."""
    st.markdown("##### KEY STATISTICS")

    # Format dividend yield safely
    div_yield = info.get("dividendYield")
    if div_yield is not None:
        # yfinance may return as fraction (0.0039) or percentage-like (0.39)
        if div_yield > 1:
            div_str = f"{div_yield:.2f}%"
        elif div_yield > 0:
            div_str = f"{div_yield * 100:.2f}%"
        else:
            div_str = "0.00%"
    else:
        div_str = "—"

    # 52W range
    w52_low = info.get("fiftyTwoWeekLow")
    w52_high = info.get("fiftyTwoWeekHigh")
    w52_range = f"₹{w52_low:,.0f} — ₹{w52_high:,.0f}" if w52_low and w52_high else "—"

    stats = [
        ("MARKET CAP", _safe(info, "marketCap", format_crore)),
        ("P/E (TTM)", _safe(info, "trailingPE", lambda v: f"{v:.2f}")),
        ("P/B", _safe(info, "priceToBook", lambda v: f"{v:.2f}")),
        ("EPS (TTM)", _safe(info, "trailingEps", lambda v: f"₹{v:,.2f}")),
        ("DIV YIELD", div_str),
        ("52W RANGE", w52_range),
        ("BETA", _safe(info, "beta", lambda v: f"{v:.3f}")),
        ("BOOK VALUE", _safe(info, "bookValue", lambda v: f"₹{v:,.2f}")),
    ]

    # Render as two rows of 4
    for row_start in range(0, len(stats), 4):
        cols = st.columns(4)
        for col, (label, value) in zip(cols, stats[row_start:row_start + 4]):
            col.markdown(
                f'<div style="background:#1A1A1A;padding:10px;border:1px solid #333;border-radius:4px">'
                f'<div style="color:#FF9900;font-size:10px;text-transform:uppercase;letter-spacing:1px">{label}</div>'
                f'<div style="color:#E0E0E0;font-size:16px;font-family:monospace;margin-top:4px">{value}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Additional ratios row
    st.markdown("")
    ratio_stats = [
        ("ROE", _safe(info, "returnOnEquity", lambda v: f"{v * 100:.2f}%" if v and v < 10 else f"{v:.2f}%")),
        ("ROA", _safe(info, "returnOnAssets", lambda v: f"{v * 100:.2f}%" if v and v < 10 else f"{v:.2f}%")),
        ("DEBT/EQUITY", _safe(info, "debtToEquity", lambda v: f"{v:.2f}")),
        ("OP. MARGIN", _safe(info, "operatingMargins", lambda v: f"{v * 100:.2f}%" if v and v < 10 else f"{v:.2f}%")),
    ]
    cols = st.columns(4)
    for col, (label, value) in zip(cols, ratio_stats):
        col.markdown(
            f'<div style="background:#1A1A1A;padding:10px;border:1px solid #333;border-radius:4px">'
            f'<div style="color:#FF9900;font-size:10px;text-transform:uppercase;letter-spacing:1px">{label}</div>'
            f'<div style="color:#E0E0E0;font-size:16px;font-family:monospace;margin-top:4px">{value}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_description(info):
    """Display business description."""
    st.markdown("##### BUSINESS DESCRIPTION")
    summary = info.get("longBusinessSummary", "No description available.")
    st.markdown(
        f'<div style="background:#1A1A1A;padding:14px;border:1px solid #333;border-radius:4px;'
        f'color:#E0E0E0;font-size:13px;line-height:1.6">{summary}</div>',
        unsafe_allow_html=True,
    )

    # Officers / Management
    officers = info.get("companyOfficers", [])
    if officers:
        st.markdown("##### KEY MANAGEMENT")
        rows = ""
        for officer in officers[:8]:
            name = officer.get("name", "—")
            title = officer.get("title", "—")
            rows += (
                f'<tr>'
                f'<td style="padding:4px 8px;color:#E0E0E0;border-bottom:1px solid #1A1A1A;font-size:12px">{name}</td>'
                f'<td style="padding:4px 8px;color:#888;border-bottom:1px solid #1A1A1A;font-size:12px">{title}</td>'
                f'</tr>'
            )
        st.markdown(
            f'<table style="width:100%;border-collapse:collapse">'
            f'<thead><tr>'
            f'<th style="padding:6px 8px;text-align:left;color:#FF9900;border-bottom:1px solid #FF9900;font-size:10px;text-transform:uppercase">Name</th>'
            f'<th style="padding:6px 8px;text-align:left;color:#FF9900;border-bottom:1px solid #FF9900;font-size:10px;text-transform:uppercase">Title</th>'
            f'</tr></thead>'
            f'<tbody>{rows}</tbody></table>',
            unsafe_allow_html=True,
        )
