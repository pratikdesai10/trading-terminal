"""Module 13: Economic Dashboard (Bloomberg: ECOW / WECO)."""

import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from config import COLORS, plotly_layout
from utils.logger import logger


def render():
    """Render the Economic Dashboard module."""
    st.markdown("### ECONOMIC DASHBOARD")

    # ── Section 1: India — RBI Key Rates ──
    _render_rbi_rates()

    st.markdown("---")

    # ── Section 2: USD/INR Chart ──
    col_fx, col_gsec = st.columns([3, 2])
    with col_fx:
        _render_usdinr_chart()
    with col_gsec:
        _render_india_macro_panel()

    st.markdown("---")

    # ── Section 3: Global Rates & Commodities ──
    _render_global_panel()

    st.markdown("---")

    # ── Section 4: Economic Calendar ──
    _render_economic_calendar()


# ─────────────────────────────────────────────
# Section 1: RBI Key Rates
# ─────────────────────────────────────────────

def _render_rbi_rates():
    """Display RBI key rates as Bloomberg-style metric cards."""
    from data.economic import get_rbi_rates

    st.markdown("##### RBI KEY RATES")

    rates = get_rbi_rates()
    rate_keys = ["Repo Rate", "SDF Rate", "MSF Rate", "CRR", "SLR", "Bank Rate"]
    cols = st.columns(len(rate_keys))

    for col, key in zip(cols, rate_keys):
        with col:
            rate_info = rates.get(key)
            if rate_info:
                val = rate_info["value"]
                updated = rate_info["updated"]
                note = rate_info["note"]
                col.markdown(
                    f'<div style="background:#1A1A1A;padding:10px;border:1px solid #333333;'
                    f'border-radius:4px;text-align:center">'
                    f'<div style="color:#FF9900;font-size:10px;text-transform:uppercase;'
                    f'letter-spacing:0.5px;margin-bottom:4px">{key}</div>'
                    f'<div style="color:#E0E0E0;font-size:22px;font-family:monospace;'
                    f'font-weight:bold">{val:.2f}%</div>'
                    f'<div style="color:#888888;font-size:9px;margin-top:4px">'
                    f'Updated: {updated}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────
# Section 2: USD/INR Chart + India Macro Panel
# ─────────────────────────────────────────────

def _render_usdinr_chart():
    """Render 1Y USD/INR exchange rate chart."""
    from data.economic import get_forex_data

    st.markdown("##### USD/INR EXCHANGE RATE")

    df = get_forex_data(pair="USDINR=X", period="1y")
    if df.empty:
        st.warning("USD/INR data unavailable")
        return

    # Current values
    last_price = float(df["Close"].iloc[-1])
    first_price = float(df["Close"].iloc[0])
    pct_change = (last_price / first_price - 1) * 100
    high_52w = float(df["High"].max())
    low_52w = float(df["Low"].min())

    color = COLORS["green"] if pct_change <= 0 else COLORS["red"]  # INR strengthening = green

    # Summary bar
    c1, c2, c3, c4 = st.columns(4)
    _stat_card(c1, "LAST", f"{last_price:.4f}")
    _stat_card(c2, "1Y CHG", f"{pct_change:+.2f}%", color=color)
    _stat_card(c3, "52W HIGH", f"{high_52w:.4f}")
    _stat_card(c4, "52W LOW", f"{low_52w:.4f}")

    # Line chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Close"],
        mode="lines",
        line=dict(color=COLORS["amber"], width=1.5),
        fill="tozeroy",
        fillcolor="rgba(255,153,0,0.05)",
        name="USD/INR",
        hovertemplate="%{x|%d %b %Y}<br>%{y:.4f}<extra></extra>",
    ))
    fig.update_layout(**plotly_layout(
        height=350,
        title="",
        yaxis_title="INR per USD",
        xaxis=dict(gridcolor="#1A1A1A", zerolinecolor="#333333"),
        yaxis=dict(gridcolor="#1A1A1A", zerolinecolor="#333333"),
    ))
    st.plotly_chart(fig, use_container_width=True)


def _render_india_macro_panel():
    """Render India macro indicators — 10Y G-Sec yield proxy and key facts."""
    from data.economic import get_rbi_rates

    st.markdown("##### INDIA MACRO SNAPSHOT")

    rates = get_rbi_rates()

    # RBI rate table
    rows = ""
    for key in ["Repo Rate", "SDF Rate", "MSF Rate", "CRR", "SLR"]:
        info = rates.get(key, {})
        val = info.get("value", 0)
        note = info.get("note", "")
        rows += (
            f'<tr>'
            f'<td style="padding:5px 8px;color:#E0E0E0;border-bottom:1px solid #1A1A1A;'
            f'font-size:12px">{key}</td>'
            f'<td style="padding:5px 8px;text-align:right;color:#E0E0E0;font-family:monospace;'
            f'border-bottom:1px solid #1A1A1A;font-size:12px">{val:.2f}%</td>'
            f'<td style="padding:5px 8px;text-align:left;color:#888888;'
            f'border-bottom:1px solid #1A1A1A;font-size:10px">{note}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;font-size:12px">'
        f'<thead><tr>'
        f'<th style="padding:6px 8px;text-align:left;color:#FF9900;border-bottom:1px solid #FF9900;'
        f'font-size:10px;text-transform:uppercase">Indicator</th>'
        f'<th style="padding:6px 8px;text-align:right;color:#FF9900;border-bottom:1px solid #FF9900;'
        f'font-size:10px;text-transform:uppercase">Rate</th>'
        f'<th style="padding:6px 8px;text-align:left;color:#FF9900;border-bottom:1px solid #FF9900;'
        f'font-size:10px;text-transform:uppercase">Note</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )

    st.markdown("")

    # Key facts box
    st.markdown(
        '<div style="background:#1A1A1A;padding:10px;border:1px solid #333333;border-radius:4px;'
        'font-size:11px;color:#888888;line-height:1.6">'
        '<span style="color:#FF9900;font-size:10px;text-transform:uppercase">Note</span><br>'
        'RBI rates are hardcoded values. The Monetary Policy Committee (MPC) meets bi-monthly '
        'to review and set the policy repo rate. SDF and MSF rates are derived from the repo rate.'
        '</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# Section 3: Global Rates & Commodities
# ─────────────────────────────────────────────

def _render_global_panel():
    """Render global indicators: Crude Oil, Gold, US 10Y Yield with sparkline charts."""
    from data.economic import get_commodity_data, get_treasury_yield, get_current_quote

    st.markdown("##### GLOBAL RATES & COMMODITIES")

    # Fetch all data
    assets = [
        {"name": "Brent Crude Oil", "symbol": "BZ=F", "unit": "$/bbl",
         "fetch": lambda: get_commodity_data("BZ=F", "1y")},
        {"name": "Gold (COMEX)", "symbol": "GC=F", "unit": "$/oz",
         "fetch": lambda: get_commodity_data("GC=F", "1y")},
        {"name": "US 10Y Treasury", "symbol": "^TNX", "unit": "%",
         "fetch": lambda: get_treasury_yield("^TNX", "1y")},
    ]

    cols = st.columns(len(assets))

    for col, asset in zip(cols, assets):
        with col:
            _render_asset_card(asset)


def _render_asset_card(asset):
    """Render a single global asset card with sparkline chart."""
    from data.economic import get_commodity_data, get_treasury_yield

    st.markdown(
        f'<div style="color:#FF9900;font-size:10px;text-transform:uppercase;'
        f'letter-spacing:0.5px;margin-bottom:4px">{asset["name"]}</div>',
        unsafe_allow_html=True,
    )

    # Fetch historical data
    df = asset["fetch"]()
    if df.empty:
        st.markdown(
            '<div style="background:#1A1A1A;padding:12px;border:1px solid #333;'
            'border-radius:4px;text-align:center;color:#888">Data unavailable</div>',
            unsafe_allow_html=True,
        )
        return

    # Current values
    last_price = float(df["Close"].iloc[-1])
    first_price = float(df["Close"].iloc[0])
    pct_change = (last_price / first_price - 1) * 100
    high = float(df["High"].max())
    low = float(df["Low"].min())

    price_color = COLORS["green"] if pct_change >= 0 else COLORS["red"]
    unit = asset["unit"]

    # Value display
    if unit == "%":
        price_str = f"{last_price:.2f}%"
    else:
        price_str = f"${last_price:,.2f}"

    st.markdown(
        f'<div style="background:#1A1A1A;padding:8px;border:1px solid #333;border-radius:4px">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
        f'<span style="color:#E0E0E0;font-size:18px;font-family:monospace;font-weight:bold">'
        f'{price_str}</span>'
        f'<span style="color:{price_color};font-size:12px;font-family:monospace">'
        f'{pct_change:+.2f}%</span>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;margin-top:4px">'
        f'<span style="color:#888;font-size:9px">H: {high:,.2f}</span>'
        f'<span style="color:#888;font-size:9px">L: {low:,.2f}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Sparkline chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Close"],
        mode="lines",
        line=dict(color=price_color, width=1.5),
        fill="tozeroy",
        fillcolor=f"rgba({_hex_to_rgb(price_color)},0.05)",
        hovertemplate="%{x|%d %b %Y}<br>%{y:,.2f}<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(**plotly_layout(
        height=180,
        margin=dict(l=0, r=0, t=10, b=20),
        xaxis=dict(
            showticklabels=True, showgrid=False,
            tickfont=dict(size=9, color="#666"),
            gridcolor="#1A1A1A",
        ),
        yaxis=dict(
            showticklabels=True, showgrid=True,
            tickfont=dict(size=9, color="#666"),
            gridcolor="#1A1A1A",
        ),
    ))
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# Section 4: Economic Calendar
# ─────────────────────────────────────────────

def _render_economic_calendar():
    """Render upcoming economic events table."""
    from data.economic import get_economic_calendar
    from datetime import datetime

    st.markdown("##### ECONOMIC CALENDAR — UPCOMING EVENTS")

    events = get_economic_calendar()

    if not events:
        st.info("No upcoming events found.")
        return

    # Limit to next 12 events
    events = events[:12]

    rows = ""
    for ev in events:
        date_str = ev["date"]
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = dt.strftime("%d %b %Y")
            day_of_week = dt.strftime("%a")
        except ValueError:
            formatted_date = date_str
            day_of_week = ""

        event_name = ev["event"]
        note = ev["note"]

        # Color-code by type
        if "RBI" in event_name:
            event_color = COLORS["amber"]
            tag = "IND"
            tag_color = COLORS["amber"]
        else:
            event_color = COLORS["blue"]
            tag = "US"
            tag_color = COLORS["blue"]

        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;color:#E0E0E0;border-bottom:1px solid #1A1A1A;'
            f'font-family:monospace;font-size:12px">{formatted_date}</td>'
            f'<td style="padding:6px 8px;color:#888;border-bottom:1px solid #1A1A1A;'
            f'font-size:11px">{day_of_week}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #1A1A1A">'
            f'<span style="background:{tag_color};color:#0A0A0A;padding:1px 6px;'
            f'border-radius:2px;font-size:9px;font-weight:bold;margin-right:8px">{tag}</span>'
            f'<span style="color:{event_color};font-size:12px">{event_name}</span></td>'
            f'<td style="padding:6px 8px;color:#888;border-bottom:1px solid #1A1A1A;'
            f'font-size:11px">{note}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr>'
        f'<th style="padding:6px 8px;text-align:left;color:#FF9900;border-bottom:1px solid #FF9900;'
        f'font-size:10px;text-transform:uppercase;width:120px">Date</th>'
        f'<th style="padding:6px 8px;text-align:left;color:#FF9900;border-bottom:1px solid #FF9900;'
        f'font-size:10px;text-transform:uppercase;width:50px">Day</th>'
        f'<th style="padding:6px 8px;text-align:left;color:#FF9900;border-bottom:1px solid #FF9900;'
        f'font-size:10px;text-transform:uppercase">Event</th>'
        f'<th style="padding:6px 8px;text-align:left;color:#FF9900;border-bottom:1px solid #FF9900;'
        f'font-size:10px;text-transform:uppercase">Notes</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _stat_card(container, label, value, color=None):
    """Render a small stat card in the given container."""
    val_color = color if color else COLORS["text"]
    container.markdown(
        f'<div style="background:#1A1A1A;padding:6px 8px;border:1px solid #333;'
        f'border-radius:4px;text-align:center">'
        f'<div style="color:#FF9900;font-size:9px;text-transform:uppercase">{label}</div>'
        f'<div style="color:{val_color};font-size:14px;font-family:monospace">{value}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _hex_to_rgb(hex_color):
    """Convert hex color '#RRGGBB' to 'R,G,B' string for rgba()."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"{r},{g},{b}"
