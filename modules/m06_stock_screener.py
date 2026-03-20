"""Module 06: Stock Screener (Bloomberg: EQS)."""

import pandas as pd
import streamlit as st

from config import COLORS, NIFTY_50
from utils.logger import logger


def render():
    """Render the Stock Screener module."""
    st.markdown("### STOCK SCREENER")

    # ── Filters ──
    sectors = sorted(set(NIFTY_50.values()))

    col_sector, col_pe, col_pb = st.columns(3)
    with col_sector:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">SECTOR FILTER</p>',
            unsafe_allow_html=True,
        )
        selected_sectors = st.multiselect(
            "SECTOR FILTER", sectors, default=[], label_visibility="collapsed",
            placeholder="All sectors",
        )
    with col_pe:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">P/E RANGE</p>',
            unsafe_allow_html=True,
        )
        pe_range = st.slider("P/E RANGE", 0.0, 200.0, (0.0, 200.0), label_visibility="collapsed")
    with col_pb:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">P/B RANGE</p>',
            unsafe_allow_html=True,
        )
        pb_range = st.slider("P/B RANGE", 0.0, 50.0, (0.0, 50.0), label_visibility="collapsed")

    col_roe, col_de, col_div = st.columns(3)
    with col_roe:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">MIN ROE (%)</p>',
            unsafe_allow_html=True,
        )
        min_roe = st.number_input("MIN ROE (%)", value=0.0, step=1.0, label_visibility="collapsed")
    with col_de:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">MAX D/E</p>',
            unsafe_allow_html=True,
        )
        max_de = st.number_input("MAX D/E", value=500.0, step=10.0, label_visibility="collapsed")
    with col_div:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">MIN DIV YIELD (%)</p>',
            unsafe_allow_html=True,
        )
        min_div = st.number_input("MIN DIV YIELD (%)", value=0.0, step=0.1, label_visibility="collapsed")

    col_sort, col_run = st.columns([3, 1])
    with col_sort:
        sort_by = st.selectbox(
            "SORT BY",
            ["Mkt Cap (Cr)", "P/E", "P/B", "ROE (%)", "D/E", "Div Yield (%)", "Price", "Beta"],
        )
    with col_run:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("🔍 RUN SCREENER", use_container_width=True)

    st.divider()

    # ── Run screener ──
    if run_btn or "screener_results" in st.session_state:
        if run_btn:
            with st.spinner("Fetching fundamentals for Nifty 50..."):
                data = _fetch_screener_data(selected_sectors)
            if data is not None and not data.empty:
                st.session_state["screener_results"] = data
            else:
                st.warning("No data returned from screener")
                return

        df = st.session_state.get("screener_results")
        if df is None or df.empty:
            return

        # Apply filters
        filtered = df.copy()
        if pe_range != (0.0, 200.0):
            filtered = filtered[(filtered["P/E"] >= pe_range[0]) & (filtered["P/E"] <= pe_range[1])]
        if pb_range != (0.0, 50.0):
            filtered = filtered[(filtered["P/B"] >= pb_range[0]) & (filtered["P/B"] <= pb_range[1])]
        if min_roe > 0:
            filtered = filtered[filtered["ROE (%)"] >= min_roe]
        if max_de < 500:
            filtered = filtered[filtered["D/E"] <= max_de]
        if min_div > 0:
            filtered = filtered[filtered["Div Yield (%)"] >= min_div]

        # Sort
        ascending = sort_by in ["P/E", "P/B", "D/E", "Beta"]
        filtered = filtered.sort_values(sort_by, ascending=ascending).reset_index(drop=True)

        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px">'
            f'{len(filtered)} / {len(df)} stocks match filters</p>',
            unsafe_allow_html=True,
        )

        if filtered.empty:
            st.info("No stocks match current filters. Try relaxing criteria.")
            return

        # Build HTML table
        _render_results_table(filtered)

        # Export
        csv = filtered.to_csv(index=False)
        st.download_button("📥 EXPORT CSV", csv, "screener_results.csv", "text/csv")
    else:
        st.info("Configure filters above and click **RUN SCREENER** to scan Nifty 50 stocks.")


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_screener_data(selected_sectors_tuple=None):
    """Fetch fundamental data for Nifty 50 via yfinance."""
    from analytics.screener_engine import fetch_screener_data

    # Filter symbols by sector if needed
    if selected_sectors_tuple:
        symbols = [s for s, sec in NIFTY_50.items() if sec in selected_sectors_tuple]
    else:
        symbols = list(NIFTY_50.keys())

    if not symbols:
        return pd.DataFrame()

    logger.info(f"m06_screener | fetching {len(symbols)} symbols")
    records = fetch_screener_data(symbols, NIFTY_50)
    if records:
        return pd.DataFrame(records)
    return pd.DataFrame()


def _render_results_table(df):
    """Render screener results as a styled HTML table."""
    cols = ["Symbol", "Sector", "Price", "Mkt Cap (Cr)", "P/E", "P/B",
            "ROE (%)", "D/E", "Div Yield (%)", "EPS", "Beta"]
    display_cols = [c for c in cols if c in df.columns]

    header = "".join(f'<th style="color:{COLORS["amber"]};padding:4px 8px;text-align:right;'
                     f'border-bottom:1px solid {COLORS["border"]};font-size:11px">{c}</th>'
                     for c in display_cols)

    rows = ""
    for _, row in df.iterrows():
        cells = ""
        for c in display_cols:
            val = row[c]
            align = "left" if c in ("Symbol", "Sector") else "right"
            color = COLORS["text"]
            if c == "Symbol":
                color = COLORS["amber"]
            elif c == "ROE (%)":
                color = COLORS["green"] if val > 15 else (COLORS["red"] if val < 0 else COLORS["text"])
            elif c == "D/E":
                color = COLORS["red"] if val > 200 else COLORS["text"]

            if isinstance(val, float):
                if c in ("Price", "Mkt Cap (Cr)", "EPS"):
                    formatted = f"{val:,.1f}"
                else:
                    formatted = f"{val:.1f}"
            else:
                formatted = str(val)

            cells += (f'<td style="padding:3px 8px;text-align:{align};color:{color};'
                      f'font-size:11px;border-bottom:1px solid #1A1A1A">{formatted}</td>')
        rows += f"<tr>{cells}</tr>"

    html = (f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;'
            f'font-family:monospace">'
            f'<thead><tr>{header}</tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')
    st.markdown(html, unsafe_allow_html=True)
