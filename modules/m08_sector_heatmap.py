"""Module 08: Sector Heatmap (Bloomberg: IMAP)."""

import plotly.graph_objects as go
import streamlit as st

from config import COLORS, NIFTY_50, plotly_layout
from utils.logger import logger


def render():
    """Render the Sector Heatmap module."""
    st.markdown("### SECTOR HEATMAP")

    try:
        with st.spinner("Loading market data for heatmap..."):
            data = _fetch_heatmap_data()

        if not data:
            st.warning("Unable to load heatmap data")
            return

        loaded = len(data)
        total = len(NIFTY_50)

        fig = _build_treemap(data)
        st.plotly_chart(fig, use_container_width=True)

        st.caption(f"{loaded}/{total} stocks loaded | Sized equally within sectors, colored by daily % change")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        logger.error(f"m08_sector_heatmap | {type(e).__name__}: {e}")


def _fetch_heatmap_data():
    """Fetch live quotes for all Nifty 50 stocks. Returns list of dicts."""
    from data.nse_live import get_stock_quote

    records = []
    for symbol, sector in NIFTY_50.items():
        quote = get_stock_quote(symbol)
        if quote is None:
            continue
        records.append({
            "symbol": symbol,
            "sector": sector,
            "lastPrice": quote["lastPrice"],
            "pChange": quote["pChange"],
        })
    return records


def _build_treemap(data):
    """Build a Plotly treemap from heatmap data."""
    labels = []
    parents = []
    values = []
    colors = []
    custom_text = []

    # Root
    sectors_seen = set()

    for rec in data:
        sector = rec["sector"]
        symbol = rec["symbol"]
        pct = rec["pChange"]
        price = rec["lastPrice"]

        # Add sector parent if not seen
        if sector not in sectors_seen:
            labels.append(sector)
            parents.append("NIFTY 50")
            values.append(0)
            colors.append(0)
            custom_text.append("")
            sectors_seen.add(sector)

        # Add stock
        labels.append(symbol)
        parents.append(sector)
        values.append(1)  # Equal weighting
        colors.append(pct)
        custom_text.append(f"₹{price:,.2f} | {pct:+.2f}%")

    # Root node
    labels.insert(0, "NIFTY 50")
    parents.insert(0, "")
    values.insert(0, 0)
    colors.insert(0, 0)
    custom_text.insert(0, "")

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(
            colors=colors,
            colorscale=[
                [0.0, "#CC0000"],    # deep red
                [0.3, "#FF3333"],    # red
                [0.45, "#663333"],   # muted red
                [0.5, "#333333"],    # neutral
                [0.55, "#336633"],   # muted green
                [0.7, "#00CC66"],    # green
                [1.0, "#00FF88"],    # bright green
            ],
            cmid=0,
            showscale=True,
            colorbar=dict(
                title=dict(text="% Chg", font=dict(color=COLORS["amber"], size=11)),
                tickfont=dict(color=COLORS["text"], size=10),
                len=0.6,
            ),
        ),
        text=custom_text,
        textinfo="label+text",
        textfont=dict(
            family="Fira Code, Consolas, monospace",
            size=11,
            color=COLORS["text"],
        ),
        hovertemplate="<b>%{label}</b><br>%{text}<extra></extra>",
        branchvalues="remainder",
    ))

    fig.update_layout(**plotly_layout(
        height=650,
        margin=dict(l=10, r=10, t=40, b=10),
    ))

    return fig
