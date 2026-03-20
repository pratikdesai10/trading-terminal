"""Module 03: Price Charts with Technicals (Bloomberg: GP)."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from config import COLORS, NIFTY_50_SYMBOLS, plotly_layout
from utils.logger import logger


PERIOD_DAYS = {
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
    "3Y": 365 * 3,
    "5Y": 365 * 5,
}


def render():
    """Render the Price Charts module."""
    st.markdown("### PRICE CHARTS")

    # ── Controls ──
    col_sym, col_period = st.columns([2, 1])
    with col_sym:
        symbol = st.selectbox("SYMBOL", NIFTY_50_SYMBOLS, index=0, key="m03_symbol")
    with col_period:
        period = st.selectbox("PERIOD", list(PERIOD_DAYS.keys()), index=3, key="m03_period")

    # ── Overlay toggles ──
    st.markdown(
        '<p style="color:#FF9900;font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">OVERLAYS</p>',
        unsafe_allow_html=True,
    )
    ov_cols = st.columns(6)
    show_sma20 = ov_cols[0].checkbox("SMA 20", key="m03_sma20")
    show_sma50 = ov_cols[1].checkbox("SMA 50", value=True, key="m03_sma50")
    show_sma200 = ov_cols[2].checkbox("SMA 200", key="m03_sma200")
    show_ema9 = ov_cols[3].checkbox("EMA 9", key="m03_ema9")
    show_ema21 = ov_cols[4].checkbox("EMA 21", key="m03_ema21")
    show_bb = ov_cols[5].checkbox("Bollinger", key="m03_bb")

    # ── Sub-chart toggles ──
    st.markdown(
        '<p style="color:#FF9900;font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">SUB-CHARTS</p>',
        unsafe_allow_html=True,
    )
    sc_cols = st.columns(6)
    show_rsi = sc_cols[0].checkbox("RSI (14)", key="m03_rsi")
    show_macd = sc_cols[1].checkbox("MACD", key="m03_macd")

    # ── Fetch data ──
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=PERIOD_DAYS[period])

        from data.nse_historical import get_stock_history
        df = get_stock_history(symbol, start_date, end_date)

        if df is None or df.empty:
            st.warning(f"No data available for {symbol}")
            return

        # ── Build chart ──
        overlays = {
            "sma20": show_sma20, "sma50": show_sma50, "sma200": show_sma200,
            "ema9": show_ema9, "ema21": show_ema21, "bb": show_bb,
        }
        fig = _build_chart(df, overlays, show_rsi, show_macd)
        st.plotly_chart(fig, use_container_width=True)

        # ── Summary stats ──
        _render_summary(df, symbol)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        logger.error(f"m03_price_charts | {type(e).__name__}: {e}")


def _build_chart(df, overlays, show_rsi, show_macd):
    """Build the candlestick chart with overlays and sub-charts."""
    # Determine subplot rows
    n_rows = 2  # candlestick + volume always
    row_heights = [0.55, 0.15]
    if show_rsi:
        n_rows += 1
        row_heights.append(0.15)
    if show_macd:
        n_rows += 1
        row_heights.append(0.15)

    fig = make_subplots(
        rows=n_rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.03, row_heights=row_heights,
    )

    # ── Candlestick ──
    fig.add_trace(
        go.Candlestick(
            x=df["Date"], open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"],
            increasing_line_color=COLORS["green"],
            decreasing_line_color=COLORS["red"],
            increasing_fillcolor=COLORS["green"],
            decreasing_fillcolor=COLORS["red"],
            name="OHLC",
            showlegend=False,
        ),
        row=1, col=1,
    )

    # ── Overlays ──
    _add_overlays(fig, df, overlays)

    # ── Volume ──
    vol_colors = [
        COLORS["green"] if c >= o else COLORS["red"]
        for c, o in zip(df["Close"], df["Open"])
    ]
    fig.add_trace(
        go.Bar(x=df["Date"], y=df["Volume"], marker_color=vol_colors,
               opacity=0.6, name="Volume", showlegend=False),
        row=2, col=1,
    )

    # ── RSI ──
    current_row = 3
    if show_rsi:
        _add_rsi(fig, df, current_row)
        current_row += 1

    # ── MACD ──
    if show_macd:
        _add_macd(fig, df, current_row)

    # ── Layout ──
    chart_height = 500 + (150 if show_rsi else 0) + (150 if show_macd else 0)
    fig.update_layout(**plotly_layout(
        height=chart_height,
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=10, color=COLORS["text"]),
            bgcolor="rgba(0,0,0,0)",
        ),
    ))

    # Style all y-axes
    for i in range(1, n_rows + 1):
        yaxis = f"yaxis{i}" if i > 1 else "yaxis"
        fig.update_layout(**{yaxis: dict(gridcolor="#1A1A1A", zerolinecolor="#333333")})

    return fig


def _add_overlays(fig, df, overlays):
    """Add SMA, EMA, Bollinger Band overlay traces."""
    from ta.trend import sma_indicator, ema_indicator
    from ta.volatility import BollingerBands

    close = df["Close"]

    overlay_config = [
        ("sma20", lambda: sma_indicator(close, window=20), "SMA 20", "#FFCC00"),
        ("sma50", lambda: sma_indicator(close, window=50), "SMA 50", "#3399FF"),
        ("sma200", lambda: sma_indicator(close, window=200), "SMA 200", "#FF6633"),
        ("ema9", lambda: ema_indicator(close, window=9), "EMA 9", "#CC66FF"),
        ("ema21", lambda: ema_indicator(close, window=21), "EMA 21", "#33CCCC"),
    ]

    for key, calc_fn, name, color in overlay_config:
        if overlays.get(key):
            values = calc_fn()
            fig.add_trace(
                go.Scatter(x=df["Date"], y=values, mode="lines",
                           name=name, line=dict(color=color, width=1)),
                row=1, col=1,
            )

    if overlays.get("bb"):
        bb = BollingerBands(close, window=20, window_dev=2)
        fig.add_trace(
            go.Scatter(x=df["Date"], y=bb.bollinger_hband(), mode="lines",
                       name="BB Upper", line=dict(color="#888888", width=1, dash="dot"),
                       showlegend=False),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=df["Date"], y=bb.bollinger_lband(), mode="lines",
                       name="BB Lower", line=dict(color="#888888", width=1, dash="dot"),
                       fill="tonexty", fillcolor="rgba(136,136,136,0.1)",
                       showlegend=False),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=df["Date"], y=bb.bollinger_mavg(), mode="lines",
                       name="BB Mid", line=dict(color="#888888", width=1),
                       showlegend=True),
            row=1, col=1,
        )


def _add_rsi(fig, df, row):
    """Add RSI sub-chart."""
    from ta.momentum import rsi

    rsi_values = rsi(df["Close"], window=14)
    fig.add_trace(
        go.Scatter(x=df["Date"], y=rsi_values, mode="lines",
                   name="RSI (14)", line=dict(color=COLORS["blue"], width=1.5)),
        row=row, col=1,
    )
    # Overbought / Oversold lines
    fig.add_hline(y=70, line_dash="dash", line_color=COLORS["red"],
                  line_width=0.8, row=row, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color=COLORS["green"],
                  line_width=0.8, row=row, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=row, col=1)


def _add_macd(fig, df, row):
    """Add MACD sub-chart."""
    from ta.trend import macd, macd_signal, macd_diff

    close = df["Close"]
    macd_line = macd(close)
    signal_line = macd_signal(close)
    histogram = macd_diff(close)

    fig.add_trace(
        go.Scatter(x=df["Date"], y=macd_line, mode="lines",
                   name="MACD", line=dict(color=COLORS["blue"], width=1.5)),
        row=row, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["Date"], y=signal_line, mode="lines",
                   name="Signal", line=dict(color=COLORS["amber"], width=1.5)),
        row=row, col=1,
    )

    hist_colors = [COLORS["green"] if v >= 0 else COLORS["red"] for v in histogram.fillna(0)]
    fig.add_trace(
        go.Bar(x=df["Date"], y=histogram, marker_color=hist_colors,
               name="Histogram", showlegend=False, opacity=0.6),
        row=row, col=1,
    )
    fig.update_yaxes(title_text="MACD", row=row, col=1)


def _render_summary(df, symbol):
    """Show quick summary stats below the chart."""
    last = df["Close"].iloc[-1]
    first = df["Close"].iloc[0]
    high = df["High"].max()
    low = df["Low"].min()
    avg_vol = df["Volume"].mean()
    pct_change = (last / first - 1) * 100

    color = COLORS["green"] if pct_change >= 0 else COLORS["red"]

    cols = st.columns(5)
    labels = ["LAST", "PERIOD HIGH", "PERIOD LOW", "PERIOD CHG%", "AVG VOLUME"]
    values = [
        f"₹{last:,.2f}",
        f"₹{high:,.2f}",
        f"₹{low:,.2f}",
        f'<span style="color:{color}">{pct_change:+.2f}%</span>',
        f"{avg_vol:,.0f}",
    ]
    for col, label, val in zip(cols, labels, values):
        col.markdown(
            f'<div style="background:#1A1A1A;padding:8px;border:1px solid #333;border-radius:4px;text-align:center">'
            f'<div style="color:#FF9900;font-size:10px;text-transform:uppercase">{label}</div>'
            f'<div style="color:#E0E0E0;font-size:16px;font-family:monospace">{val}</div></div>',
            unsafe_allow_html=True,
        )
