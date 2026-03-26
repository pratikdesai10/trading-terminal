"""Module 08: Sector Heatmap (Bloomberg: IMAP)."""

import plotly.graph_objects as go
import streamlit as st

from config import COLORS, NIFTY_50, NIFTY_100_SYMBOLS, plotly_layout
from data.nifty500 import get_nifty_500_map
from utils.logger import logger


def render():
    """Render the Sector Heatmap module."""
    st.markdown("### SECTOR HEATMAP")

    # ── Controls: universe + sector filter ──
    col_univ, col_sector = st.columns([1, 3])

    with col_univ:
        universe = st.selectbox(
            "UNIVERSE", ["Nifty 50", "Nifty 100", "Nifty 500"],
            index=0, key="m08_universe", label_visibility="collapsed",
        )

    # Build symbol-to-sector map based on universe
    if universe == "Nifty 500":
        symbol_sector_map = get_nifty_500_map()
    elif universe == "Nifty 100":
        n500 = get_nifty_500_map()
        symbol_sector_map = {s: n500.get(s, NIFTY_50.get(s, "Other")) for s in NIFTY_100_SYMBOLS}
    else:
        symbol_sector_map = dict(NIFTY_50)

    all_sectors = sorted(set(symbol_sector_map.values()))

    with col_sector:
        selected_sectors = st.multiselect(
            "SECTORS", all_sectors, default=all_sectors,
            key="m08_sectors", label_visibility="collapsed",
        )

    if not selected_sectors:
        selected_sectors = all_sectors

    # Filter symbols by sector
    filtered = {s: sec for s, sec in symbol_sector_map.items() if sec in selected_sectors}
    total = len(filtered)

    if total > 150:
        st.warning(f"Loading {total} stocks — this may take a moment. Consider filtering by sector.")

    try:
        # Convert to hashable tuples for cache key
        symbols_tuple = tuple(sorted(filtered.keys()))
        sectors_tuple = tuple(sorted(selected_sectors))

        with st.spinner(f"Loading {total} stocks in parallel..."):
            data = _fetch_heatmap_data(symbols_tuple, symbol_sector_map)

        if not data:
            st.warning("Unable to load heatmap data")
            return

        loaded = len(data)
        fig = _build_treemap(data, universe)
        st.plotly_chart(fig, use_container_width=True)

        st.caption(f"{loaded}/{total} stocks loaded | Sized equally within sectors, colored by daily % change")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        logger.error(f"m08_sector_heatmap | {type(e).__name__}: {e}")


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_heatmap_data(symbols_tuple, _symbol_sector_map):
    """Fetch live quotes for given symbols in parallel. Returns list of dicts."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from data.nse_live import get_stock_quote

    records = []
    max_workers = min(20, len(symbols_tuple))
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sym = {
                executor.submit(get_stock_quote, symbol): symbol
                for symbol in symbols_tuple
            }
            for future in as_completed(future_to_sym):
                symbol = future_to_sym[future]
                try:
                    quote = future.result(timeout=10)
                    if quote is not None:
                        records.append({
                            "symbol": symbol,
                            "sector": _symbol_sector_map.get(symbol, "Other"),
                            "lastPrice": quote["lastPrice"],
                            "pChange": quote["pChange"],
                        })
                except Exception as e:
                    logger.warning(f"_fetch_heatmap_data | {symbol} | {type(e).__name__}: {e}")
    except Exception as e:
        logger.error(f"_fetch_heatmap_data | batch fetch failed: {type(e).__name__}: {e}")

    return records


def _build_treemap(data, universe_label="NIFTY 50"):
    """Build a Plotly treemap from heatmap data."""
    labels = []
    parents = []
    values = []
    colors = []
    custom_text = []

    sectors_seen = set()

    for rec in data:
        sector = rec["sector"]
        symbol = rec["symbol"]
        pct = rec["pChange"]
        price = rec["lastPrice"]

        # Add sector parent if not seen
        if sector not in sectors_seen:
            labels.append(sector)
            parents.append(universe_label)
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
    labels.insert(0, universe_label)
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
