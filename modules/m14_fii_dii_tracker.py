"""Module 14: FII/DII Flow Tracker (India-Specific)."""

import plotly.graph_objects as go
import pandas as pd
import streamlit as st

try:
    from curl_cffi import requests
except Exception:
    import requests

from config import COLORS, plotly_layout
from utils.logger import logger


def render():
    """Render the FII/DII Tracker module."""
    st.markdown("### FII / DII FLOW TRACKER")

    with st.spinner("Loading FII/DII data..."):
        data = _fetch_fii_dii_data()

    if not data:
        st.warning("FII/DII data not available. NSE may have restricted access.")
        return

    # ── Summary metrics ──
    st.divider()
    _render_summary(data)
    st.divider()

    # ── Daily bar chart ──
    _render_daily_chart(data)

    st.divider()

    # ── Data table ──
    _render_data_table(data)


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_fii_dii_data():
    """Fetch FII/DII activity data from NSE.

    Returns a list of dicts with keys: date, category, buyValue, sellValue, netValue.
    """
    logger.info("m14_fii_dii | fetching from NSE API")

    try:
        try:
            from curl_cffi import requests as _curl_req
            s = _curl_req.Session(impersonate="chrome")
        except Exception:
            s = requests.Session()
            s.headers.update({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            })
        # Hit main page first to get cookies
        s.get("https://www.nseindia.com", timeout=10)

        r = s.get("https://www.nseindia.com/api/fiidiiTradeReact", timeout=10)
        if r.status_code != 200:
            logger.warning(f"m14_fii_dii | NSE API returned {r.status_code}")
            return None

        raw = r.json()
        if not raw or not isinstance(raw, list):
            logger.warning("m14_fii_dii | empty or invalid response")
            return None

        # Parse into structured records
        records = []
        for item in raw:
            cat = item.get("category", "")
            records.append({
                "category": "FII" if "FII" in cat or "FPI" in cat else "DII",
                "date": item.get("date", ""),
                "buyValue": _parse_num(item.get("buyValue", "0")),
                "sellValue": _parse_num(item.get("sellValue", "0")),
                "netValue": _parse_num(item.get("netValue", "0")),
            })

        logger.info(f"m14_fii_dii | OK | {len(records)} records")
        return records

    except Exception as e:
        logger.error(f"m14_fii_dii | {type(e).__name__}: {e}")
        return None


def _parse_num(val):
    """Parse a numeric string, removing commas."""
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def _render_summary(data):
    """Render summary metrics for FII/DII flows."""
    fii = [r for r in data if r["category"] == "FII"]
    dii = [r for r in data if r["category"] == "DII"]

    c1, c2, c3, c4 = st.columns(4)

    if fii:
        fii_net = fii[0]["netValue"]
        fii_buy = fii[0]["buyValue"]
        fii_sell = fii[0]["sellValue"]
        fii_color = COLORS["green"] if fii_net >= 0 else COLORS["red"]

        c1.markdown(
            f'<div style="text-align:center">'
            f'<div style="color:{COLORS["muted"]};font-size:10px">FII/FPI NET</div>'
            f'<div style="color:{fii_color};font-size:20px;font-weight:bold">₹{fii_net:,.2f} Cr</div>'
            f'</div>', unsafe_allow_html=True,
        )
        c2.markdown(
            f'<div style="text-align:center">'
            f'<div style="color:{COLORS["muted"]};font-size:10px">FII BUY / SELL</div>'
            f'<div style="color:{COLORS["text"]};font-size:14px">'
            f'<span style="color:{COLORS["green"]}">₹{fii_buy:,.2f}</span>'
            f' / '
            f'<span style="color:{COLORS["red"]}">₹{fii_sell:,.2f}</span>'
            f'</div></div>', unsafe_allow_html=True,
        )
    else:
        c1.markdown(f'<div style="color:{COLORS["muted"]};text-align:center">FII data unavailable</div>',
                    unsafe_allow_html=True)

    if dii:
        dii_net = dii[0]["netValue"]
        dii_buy = dii[0]["buyValue"]
        dii_sell = dii[0]["sellValue"]
        dii_color = COLORS["green"] if dii_net >= 0 else COLORS["red"]

        c3.markdown(
            f'<div style="text-align:center">'
            f'<div style="color:{COLORS["muted"]};font-size:10px">DII NET</div>'
            f'<div style="color:{dii_color};font-size:20px;font-weight:bold">₹{dii_net:,.2f} Cr</div>'
            f'</div>', unsafe_allow_html=True,
        )
        c4.markdown(
            f'<div style="text-align:center">'
            f'<div style="color:{COLORS["muted"]};font-size:10px">DII BUY / SELL</div>'
            f'<div style="color:{COLORS["text"]};font-size:14px">'
            f'<span style="color:{COLORS["green"]}">₹{dii_buy:,.2f}</span>'
            f' / '
            f'<span style="color:{COLORS["red"]}">₹{dii_sell:,.2f}</span>'
            f'</div></div>', unsafe_allow_html=True,
        )
    else:
        c3.markdown(f'<div style="color:{COLORS["muted"]};text-align:center">DII data unavailable</div>',
                    unsafe_allow_html=True)

    # Date label
    if data:
        trade_date = data[0].get("date", "")
        st.markdown(
            f'<div style="text-align:center;color:{COLORS["muted"]};font-size:10px;margin-top:4px">'
            f'Data as of {trade_date} (₹ in Crores)'
            f'</div>', unsafe_allow_html=True,
        )


def _render_daily_chart(data):
    """Render FII/DII buy vs sell bar chart."""
    st.markdown("##### FII / DII ACTIVITY")

    fii = [r for r in data if r["category"] == "FII"]
    dii = [r for r in data if r["category"] == "DII"]

    categories = []
    buy_vals = []
    sell_vals = []
    net_vals = []

    if fii:
        categories.append("FII/FPI")
        buy_vals.append(fii[0]["buyValue"])
        sell_vals.append(fii[0]["sellValue"])
        net_vals.append(fii[0]["netValue"])
    if dii:
        categories.append("DII")
        buy_vals.append(dii[0]["buyValue"])
        sell_vals.append(dii[0]["sellValue"])
        net_vals.append(dii[0]["netValue"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories, y=buy_vals, name="Buy",
        marker_color=COLORS["green"], opacity=0.8,
        text=[f"₹{v:,.0f} Cr" for v in buy_vals],
        textposition="auto",
    ))
    fig.add_trace(go.Bar(
        x=categories, y=sell_vals, name="Sell",
        marker_color=COLORS["red"], opacity=0.8,
        text=[f"₹{v:,.0f} Cr" for v in sell_vals],
        textposition="auto",
    ))
    fig.add_trace(go.Bar(
        x=categories, y=net_vals, name="Net",
        marker_color=[COLORS["green"] if n >= 0 else COLORS["red"] for n in net_vals],
        opacity=0.5,
        text=[f"₹{v:+,.0f} Cr" for v in net_vals],
        textposition="auto",
    ))

    fig.update_layout(**plotly_layout(
        height=350,
        barmode="group",
        yaxis_title="Value (₹ Cr)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    ))

    st.plotly_chart(fig, use_container_width=True)


def _render_data_table(data):
    """Render FII/DII data as a styled table."""
    st.markdown("##### DAILY BREAKUP")

    if not data:
        st.info("No data available")
        return

    fii = [r for r in data if r["category"] == "FII"]
    dii = [r for r in data if r["category"] == "DII"]

    trade_date = data[0].get("date", "—")

    rows = ""
    border = f"border-bottom:1px solid #1A1A1A"
    cell = "padding:6px 12px;font-size:12px"

    for cat, items in [("FII/FPI", fii), ("DII", dii)]:
        if items:
            r = items[0]
            net_color = COLORS["green"] if r["netValue"] >= 0 else COLORS["red"]
            rows += (
                f'<tr>'
                f'<td style="{cell};{border};color:{COLORS["amber"]};font-weight:bold">{cat}</td>'
                f'<td style="{cell};{border};text-align:center;color:{COLORS["muted"]}">{trade_date}</td>'
                f'<td style="{cell};{border};text-align:right;color:{COLORS["green"]}">₹{r["buyValue"]:,.2f} Cr</td>'
                f'<td style="{cell};{border};text-align:right;color:{COLORS["red"]}">₹{r["sellValue"]:,.2f} Cr</td>'
                f'<td style="{cell};{border};text-align:right;color:{net_color};font-weight:bold">₹{r["netValue"]:+,.2f} Cr</td>'
                f'</tr>'
            )

    header_style = (f'color:{COLORS["amber"]};padding:6px 12px;font-size:10px;'
                    f'border-bottom:1px solid {COLORS["border"]}')

    html = (
        f'<div style="overflow-x:auto">'
        f'<table style="width:100%;border-collapse:collapse;font-family:monospace">'
        f'<thead><tr>'
        f'<th style="{header_style};text-align:left">CATEGORY</th>'
        f'<th style="{header_style};text-align:center">DATE</th>'
        f'<th style="{header_style};text-align:right">BUY VALUE</th>'
        f'<th style="{header_style};text-align:right">SELL VALUE</th>'
        f'<th style="{header_style};text-align:right">NET VALUE</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    st.markdown(
        f'<div style="color:{COLORS["muted"]};font-size:10px;margin-top:8px">'
        f'Source: NSE India | Values in ₹ Crores | Updates daily after market hours'
        f'</div>', unsafe_allow_html=True,
    )
