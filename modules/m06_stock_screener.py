"""Module 06: Stock Screener (Bloomberg: EQS)."""

import pandas as pd
import streamlit as st

from config import COLORS, NIFTY_50, NIFTY_50_SYMBOLS, NIFTY_100_SYMBOLS, NIFTY_200_SYMBOLS
from utils.logger import logger


def render():
    """Render the Stock Screener module."""
    st.markdown("### STOCK SCREENER")

    # ── Universe selector ──
    col_univ, _ = st.columns([2, 4])
    with col_univ:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">UNIVERSE</p>',
            unsafe_allow_html=True,
        )
        universe = st.selectbox(
            "UNIVERSE", ["Nifty 50", "Nifty 100", "Nifty 200"],
            index=0, key="m06_universe", label_visibility="collapsed",
        )

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

    col_revg, col_rsi, col_52w = st.columns(3)
    with col_revg:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">REVENUE GROWTH (%)</p>',
            unsafe_allow_html=True,
        )
        rev_growth_range = st.slider(
            "REVENUE GROWTH (%)", -100.0, 200.0, (-100.0, 200.0),
            label_visibility="collapsed",
        )
    with col_rsi:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">RSI (14)</p>',
            unsafe_allow_html=True,
        )
        rsi_range = st.slider(
            "RSI (14)", 0.0, 100.0, (0.0, 100.0),
            label_visibility="collapsed",
        )
    with col_52w:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">52W PROXIMITY (% OF HIGH)</p>',
            unsafe_allow_html=True,
        )
        min_52w_prox = st.slider(
            "52W PROXIMITY (%)", 0, 100, 0,
            help="Show stocks within N% of 52-week high",
            label_visibility="collapsed",
        )

    col_sort, col_run = st.columns([3, 1])
    with col_sort:
        sort_by = st.selectbox(
            "SORT BY",
            ["Mkt Cap (Cr)", "P/E", "P/B", "ROE (%)", "D/E", "Div Yield (%)",
             "Price", "Beta", "Rev Growth (%)", "RSI", "52W Prox (%)"],
        )
    with col_run:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("🔍 RUN SCREENER", use_container_width=True)

    st.divider()

    # ── Run screener ──
    if run_btn or "screener_results" in st.session_state:
        if run_btn:
            with st.spinner(f"Fetching fundamentals for {universe}..."):
                data = _fetch_screener_data(
                    universe=universe,
                    selected_sectors_tuple=tuple(selected_sectors) if selected_sectors else None,
                )
            if data is not None and not data.empty:
                st.session_state["screener_results"] = data
            else:
                st.warning("No data returned from screener")
                return

        df = st.session_state.get("screener_results")
        if df is None or df.empty:
            return

        # Apply filters (fill NaN with 0 for numeric comparisons)
        filtered = df.copy()
        for col in ["P/E", "P/B", "ROE (%)", "D/E", "Div Yield (%)", "Rev Growth (%)",
                     "RSI", "52W Prox (%)"]:
            if col in filtered.columns:
                filtered[col] = pd.to_numeric(filtered[col], errors="coerce").fillna(0.0)
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
        if rev_growth_range != (-100.0, 200.0):
            filtered = filtered[
                (filtered["Rev Growth (%)"] >= rev_growth_range[0])
                & (filtered["Rev Growth (%)"] <= rev_growth_range[1])
            ]
        if rsi_range != (0.0, 100.0):
            filtered = filtered[
                (filtered["RSI"] >= rsi_range[0]) & (filtered["RSI"] <= rsi_range[1])
            ]
        if min_52w_prox > 0:
            filtered = filtered[filtered["52W Prox (%)"] >= min_52w_prox]

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
        st.info("Configure filters above and click **RUN SCREENER** to scan stocks.")


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_screener_data(universe="Nifty 50", selected_sectors_tuple=None):
    """Fetch fundamental data for the selected universe via yfinance."""
    from analytics.screener_engine import fetch_screener_data

    # Resolve symbol list based on universe
    if universe == "Nifty 200":
        all_symbols = NIFTY_200_SYMBOLS
    elif universe == "Nifty 100":
        all_symbols = NIFTY_100_SYMBOLS
    else:
        all_symbols = NIFTY_50_SYMBOLS

    # Build sector dict — NIFTY_50 has known mappings; others get empty string
    sector_map = {s: NIFTY_50.get(s, "") for s in all_symbols}

    # Filter symbols by sector if needed
    if selected_sectors_tuple:
        symbols = [s for s in all_symbols if sector_map.get(s, "") in selected_sectors_tuple]
    else:
        symbols = list(all_symbols)

    if not symbols:
        return pd.DataFrame()

    logger.info(f"m06_screener | fetching {len(symbols)} symbols ({universe})")
    records = fetch_screener_data(symbols, sector_map)

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # ── Compute 52W Proximity (%) ──
    if "52W High" in df.columns and "Price" in df.columns:
        high = pd.to_numeric(df["52W High"], errors="coerce")
        price = pd.to_numeric(df["Price"], errors="coerce")
        df["52W Prox (%)"] = (price / high * 100).round(1).fillna(0.0)
    else:
        df["52W Prox (%)"] = 0.0

    # ── Compute RSI (14) from recent price data (batch download) ──
    df["RSI"] = 0.0
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        from ta.momentum import RSIIndicator

        end = datetime.now()
        start = end - timedelta(days=40)  # ~30 trading days
        tickers_ns = [f"{s}.NS" for s in df["Symbol"].tolist()]

        try:
            batch = yf.download(
                tickers_ns,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                progress=False,
                threads=True,
            )
            if batch is not None and not batch.empty:
                close_data = batch["Close"] if "Close" in batch.columns else batch.get("Adj Close")
                if close_data is not None:
                    for idx, row in df.iterrows():
                        ticker_ns = f"{row['Symbol']}.NS"
                        try:
                            if ticker_ns in close_data.columns:
                                series = close_data[ticker_ns].dropna()
                            else:
                                continue
                            if len(series) >= 15:
                                rsi_val = RSIIndicator(series, window=14).rsi().iloc[-1]
                                df.at[idx, "RSI"] = round(rsi_val, 1) if pd.notna(rsi_val) else 0.0
                        except Exception:
                            pass  # leave as 0.0
        except Exception:
            logger.warning("m06_screener | batch RSI download failed")
    except ImportError:
        logger.warning("m06_screener | yfinance/ta not available for RSI calc")

    return df


def _render_results_table(df):
    """Render screener results as a styled HTML table."""
    cols = ["Symbol", "Sector", "Price", "Mkt Cap (Cr)", "P/E", "P/B",
            "ROE (%)", "D/E", "Div Yield (%)", "Rev Growth (%)", "RSI",
            "52W Prox (%)", "EPS", "Beta"]
    display_cols = [c for c in cols if c in df.columns]

    header = "".join(
        f'<th style="color:{COLORS["amber"]};padding:4px 8px;'
        f'text-align:{"left" if c in ("Symbol", "Sector") else "right"};'
        f'border-bottom:1px solid {COLORS["border"]};font-size:11px">{c}</th>'
        for c in display_cols
    )

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
