"""Module 09: Index & Stock Comparison (Bloomberg: HS / COMP)."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import COLORS, NIFTY_500_SYMBOLS, SECTORAL_INDICES, KEY_INDICES, plotly_layout
from utils.logger import logger


# Distinct colors for comparison lines
COMPARE_COLORS = ["#3399FF", "#00CC66", "#FF9900", "#CC66FF", "#FF3333",
                  "#FFCC00", "#FF99CC", "#33CCCC", "#FF6633", "#66FF66"]

# India risk-free rate (~10Y G-Sec yield approximation)
RISK_FREE_RATE = 6.5

# Index options for comparison (sector rotation analysis)
INDEX_OPTIONS = (
    ["NIFTY 50", "NIFTY NEXT 50", "NIFTY MIDCAP 50", "INDIA VIX"]
    + SECTORAL_INDICES
)


def render():
    """Render the Index / Stock Comparison module."""
    st.markdown("### INDEX / STOCK COMPARISON")

    # ── Mode toggle ──
    mode = st.radio(
        "COMPARE", ["Stocks", "Indices"],
        horizontal=True, key="m09_mode", label_visibility="collapsed",
    )

    # ── Controls based on mode ──
    if mode == "Indices":
        symbols = st.multiselect(
            "SELECT INDICES (max 10)",
            INDEX_OPTIONS,
            default=["NIFTY BANK", "NIFTY IT", "NIFTY PHARMA", "NIFTY AUTO"],
            max_selections=10,
            key="m09_indices",
        )
    else:
        symbols = st.multiselect(
            "SELECT STOCKS (max 5)",
            NIFTY_500_SYMBOLS,
            default=["RELIANCE", "TCS", "HDFCBANK"],
            max_selections=5,
            key="m09_symbols",
        )

    col_start, col_end = st.columns(2)
    with col_start:
        start_date = st.date_input("START DATE", value=date.today() - timedelta(days=365), key="m09_start")
    with col_end:
        end_date = st.date_input("END DATE", value=date.today(), key="m09_end")

    if len(symbols) < 2:
        st.info(f"Select at least 2 {'indices' if mode == 'Indices' else 'stocks'} to compare.")
        return

    try:
        # ── Fetch data ──
        with st.spinner("Loading historical data..."):
            data_dict = _fetch_data(symbols, start_date, end_date, is_index=(mode == "Indices"))

        if len(data_dict) < 2:
            st.warning("Insufficient data for comparison. Some selections may have no history.")
            return

        # ── Charts and stats ──
        _render_normalized_chart(data_dict)
        st.markdown("---")
        _render_stats_table(data_dict)
        st.markdown("---")
        _render_correlation_matrix(data_dict)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        logger.error(f"m09_index_comparison | {type(e).__name__}: {e}")


def _fetch_data(symbols, start_date, end_date, is_index=False):
    """Fetch historical close data for each symbol/index. Returns dict[name, DataFrame]."""
    from data.nse_historical import get_stock_history, get_index_history

    fetch_fn = get_index_history if is_index else get_stock_history

    data = {}
    for sym in symbols:
        try:
            df = fetch_fn(sym, start_date, end_date)
        except Exception as e:
            logger.warning(f"m09_index_comparison | {sym} | fetch failed: {type(e).__name__}: {e}")
            continue
        if df is not None and not df.empty and len(df) > 1:
            data[sym] = df
    return data


def _render_normalized_chart(data_dict):
    """Plot normalized performance chart (base 100)."""
    fig = go.Figure()

    for i, (sym, df) in enumerate(data_dict.items()):
        normalized = (df["Close"] / df["Close"].iloc[0]) * 100
        color = COMPARE_COLORS[i % len(COMPARE_COLORS)]
        fig.add_trace(go.Scatter(
            x=df["Date"], y=normalized,
            mode="lines", name=sym,
            line=dict(color=color, width=2),
        ))

    fig.update_layout(**plotly_layout(
        height=450,
        yaxis_title="Normalized (Base = 100)",
        hovermode="x unified",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=11, color=COLORS["text"]),
        ),
    ))

    # Add base-100 reference line
    fig.add_hline(y=100, line_dash="dash", line_color="#555555", line_width=0.8)

    st.plotly_chart(fig, use_container_width=True)


def _render_stats_table(data_dict):
    """Compute and display comparison statistics."""
    st.markdown("##### PERFORMANCE STATISTICS")

    rows = ""
    for sym, df in data_dict.items():
        close = df["Close"]
        first = close.iloc[0]
        last = close.iloc[-1]
        n_days = (df["Date"].iloc[-1] - df["Date"].iloc[0]).days

        total_return = (last / first - 1) * 100
        cagr = ((last / first) ** (365.0 / max(n_days, 1)) - 1) * 100 if n_days > 0 else 0

        returns = close.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100 if len(returns) > 1 else 0
        sharpe = (cagr - RISK_FREE_RATE) / volatility if volatility > 0 else 0

        cummax = close.cummax()
        drawdown = (close - cummax) / cummax
        max_dd = drawdown.min() * 100

        ret_color = COLORS["green"] if total_return >= 0 else COLORS["red"]
        cagr_color = COLORS["green"] if cagr >= 0 else COLORS["red"]

        def _td(val, color=COLORS["text"]):
            return (
                f'<td style="padding:4px 8px;text-align:right;color:{color};'
                f'font-family:monospace;border-bottom:1px solid #1A1A1A;font-size:12px">{val}</td>'
            )

        rows += (
            f'<tr>'
            f'<td style="padding:4px 8px;color:#3399FF;border-bottom:1px solid #1A1A1A;font-size:12px;font-weight:bold">{sym}</td>'
            + _td(f"{total_return:+.2f}%", ret_color)
            + _td(f"{cagr:+.2f}%", cagr_color)
            + _td(f"{volatility:.2f}%")
            + _td(f"{sharpe:.3f}")
            + _td(f"{max_dd:.2f}%", COLORS["red"])
            + f'</tr>'
        )

    headers = ["SYMBOL", "TOTAL RETURN", "CAGR", "VOLATILITY", "SHARPE", "MAX DD"]
    header_cells = ""
    for i, h in enumerate(headers):
        align = "left" if i == 0 else "right"
        header_cells += (
            f'<th style="padding:6px 8px;text-align:{align};color:#FF9900;'
            f'border-bottom:1px solid #FF9900;font-size:10px;text-transform:uppercase">{h}</th>'
        )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;border:1px solid #333">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )


def _render_correlation_matrix(data_dict):
    """Compute and display a correlation heatmap."""
    st.markdown("##### CORRELATION MATRIX")

    # Build returns DataFrame
    returns_df = pd.DataFrame()
    for sym, df in data_dict.items():
        r = df.set_index("Date")["Close"]
        r = r[~r.index.duplicated(keep="last")]  # Remove duplicate dates
        r = r.pct_change().dropna()
        r.name = sym
        returns_df = pd.concat([returns_df, r], axis=1)

    if returns_df.empty or len(returns_df.columns) < 2:
        st.info("Not enough data for correlation")
        return

    corr = returns_df.corr()

    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.index,
        text=[[f"{v:.3f}" for v in row] for row in corr.values],
        texttemplate="%{text}",
        textfont=dict(size=12, color=COLORS["text"]),
        colorscale=[
            [0.0, "#3333CC"],
            [0.5, "#333333"],
            [1.0, "#CC3333"],
        ],
        zmid=0.5,
        zmin=0, zmax=1,
        showscale=True,
        colorbar=dict(
            tickfont=dict(color=COLORS["text"], size=10),
            len=0.6,
        ),
    ))

    fig.update_layout(**plotly_layout(
        height=350,
        xaxis=dict(side="bottom", tickfont=dict(size=11)),
        yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
    ))

    st.plotly_chart(fig, use_container_width=True)
