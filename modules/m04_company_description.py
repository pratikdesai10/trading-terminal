"""Module 04: Company Description (Bloomberg: DES)."""

import streamlit as st
import plotly.graph_objects as go

from config import NIFTY_500_SYMBOLS, COLORS, plotly_layout
from utils.formatting import format_inr, format_crore, escape_html
from utils.logger import logger


def render():
    """Render the Company Description module."""
    st.markdown("### COMPANY DESCRIPTION")

    symbol = st.selectbox("SYMBOL", NIFTY_500_SYMBOLS, index=0, key="m04_symbol")

    from data.fundamentals import get_company_info
    with st.spinner("Loading company data..."):
        try:
            info = get_company_info(symbol)
        except Exception as e:
            logger.warning(f"m04 | get_company_info failed for {symbol}: {e}")
            info = None

    if info is None:
        st.warning(f"No data available for {symbol}. yfinance may be rate-limited.")
        return

    _render_header(info, symbol)
    st.markdown("---")
    _render_key_stats(info)
    st.markdown("---")
    _render_shareholding(symbol)
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
    except Exception as e:
        logger.debug(f"m04 | _safe format error for key={key}: {e}")
        return default


def _render_header(info, symbol):
    """Display company name, sector, industry, and current price."""
    name = escape_html(info.get("longName") or info.get("shortName") or symbol)
    sector = escape_html(info.get("sector", "—"))
    industry = escape_html(info.get("industry", "—"))

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


def _render_shareholding(symbol):
    """Display shareholding pattern with breakdown and stacked bar chart."""
    try:
        import yfinance as yf
        try:
            from curl_cffi import requests as _curl_req
            _session = _curl_req.Session(impersonate="chrome")
        except Exception:
            import requests as _req
            _session = _req.Session()
            _session.headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        ticker = yf.Ticker(f"{symbol}.NS", session=_session)
        major = ticker.major_holders
        if major is None or major.empty:
            st.info("Shareholding data not available")
            return
    except Exception as e:
        logger.debug(f"m04 | shareholding fetch error: {e}")
        st.info("Shareholding data not available")
        return

    st.markdown(
        '<div style="color:#FF9900;font-size:14px;font-weight:bold;font-family:monospace;'
        'letter-spacing:1px;margin-bottom:8px">SHAREHOLDING PATTERN</div>',
        unsafe_allow_html=True,
    )

    # Parse major_holders DataFrame — index is Breakdown name, single 'Value' column
    promoter_pct = 0.0
    institutional_pct = 0.0
    try:
        for idx_name in major.index:
            label = str(idx_name).lower()
            val = float(major.loc[idx_name, "Value"]) if "Value" in major.columns else float(major.iloc[0])
            if "insider" in label:
                promoter_pct = val * 100  # yfinance returns as fraction (0.77 = 77%)
            elif "institutionspercentheld" in label or ("institutions" in label and "float" not in label and "count" not in label):
                institutional_pct = val * 100
    except Exception as e:
        logger.debug(f"m04 | shareholding parse error: {e}")
        st.info("Shareholding data not available")
        return

    # Approximate breakdown
    public_pct = max(0.0, 100.0 - promoter_pct - institutional_pct)
    # Split institutional roughly into FII and DII (approximate 60/40 split)
    fii_pct = round(institutional_pct * 0.6, 2)
    dii_pct = round(institutional_pct - fii_pct, 2)

    # Metrics row — 4 cards matching _render_key_stats style
    card_style = (
        'background:#1A1A1A;padding:10px;border:1px solid #333;border-radius:4px'
    )
    label_style = (
        'color:#FF9900;font-size:10px;text-transform:uppercase;letter-spacing:1px'
    )
    value_style = 'color:#E0E0E0;font-size:16px;font-family:monospace;margin-top:4px'

    cols = st.columns(4)
    for col, (label, value) in zip(cols, [
        ("PROMOTER", f"{promoter_pct:.2f}%"),
        ("FII (EST.)", f"{fii_pct:.2f}%"),
        ("DII (EST.)", f"{dii_pct:.2f}%"),
        ("PUBLIC", f"{public_pct:.2f}%"),
    ]):
        col.markdown(
            f'<div style="{card_style}">'
            f'<div style="{label_style}">{label}</div>'
            f'<div style="{value_style}">{value}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Horizontal stacked bar chart
    categories = ["Promoter", "FII (Est.)", "DII (Est.)", "Public"]
    values = [promoter_pct, fii_pct, dii_pct, public_pct]
    bar_colors = [COLORS["amber"], COLORS["blue"], COLORS["green"], COLORS["muted"]]

    fig = go.Figure()
    for cat, val, clr in zip(categories, values, bar_colors):
        fig.add_trace(go.Bar(
            y=["Shareholding"],
            x=[val],
            name=f"{cat} ({val:.1f}%)",
            orientation="h",
            marker=dict(color=clr),
            text=f"{val:.1f}%",
            textposition="inside",
            textfont=dict(size=11, color="#FFFFFF"),
        ))

    fig.update_layout(
        **plotly_layout(
            barmode="stack",
            height=90,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.6,
                xanchor="left",
                x=0,
                font=dict(size=10),
            ),
            xaxis=dict(
                range=[0, 100],
                showticklabels=False,
                showgrid=False,
                zeroline=False,
            ),
            yaxis=dict(
                showticklabels=False,
                showgrid=False,
                zeroline=False,
            ),
        )
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_description(info):
    """Display business description."""
    st.markdown("##### BUSINESS DESCRIPTION")
    summary = escape_html(info.get("longBusinessSummary", "No description available."))
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
            name = escape_html(officer.get("name", "—"))
            title = escape_html(officer.get("title", "—"))
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
