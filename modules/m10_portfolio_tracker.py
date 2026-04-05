"""Module 10: Portfolio Tracker (Bloomberg: PORT)."""

import json
from datetime import date, datetime

import plotly.graph_objects as go
import streamlit as st

from config import COLORS, NIFTY_50, NIFTY_500_SYMBOLS, SECTOR_COLORS, plotly_layout
from data.nifty500 import get_nifty_500_map
from utils.formatting import format_inr, format_pct, color_change
from utils.logger import logger

# ── Session state key ──
_STATE_KEY = "portfolio_holdings"


def render():
    """Render the Portfolio Tracker module."""
    st.markdown("### PORTFOLIO TRACKER")

    # Initialize session state (load from DB)
    user_id = st.session_state["user_id"]
    if _STATE_KEY not in st.session_state:
        from data.database import load_holdings
        st.session_state[_STATE_KEY] = load_holdings(user_id)

    # ── Controls: Add holding / Import-Export ──
    _render_controls()

    st.divider()

    holdings = st.session_state[_STATE_KEY]
    if not holdings:
        st.markdown(
            f'<div style="text-align:center;padding:40px;color:{COLORS["muted"]};font-family:monospace">'
            f'No holdings in portfolio. Use the controls above to add positions.</div>',
            unsafe_allow_html=True,
        )
        return

    try:
        # Fetch live prices for all holdings
        live_data = _fetch_live_prices(holdings)

        # ── Portfolio Summary ──
        _render_summary(holdings, live_data)

        st.divider()

        # ── Holdings Table ──
        _render_holdings_table(holdings, live_data)

        st.divider()

        # ── Charts row ──
        col_alloc, col_sector = st.columns(2)
        with col_alloc:
            _render_allocation_pie(holdings, live_data)
        with col_sector:
            _render_sector_pie(holdings, live_data)

        st.divider()

        # ── Daily P&L bar chart ──
        _render_daily_pnl_chart(holdings, live_data)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        logger.error(f"m10_portfolio_tracker | {type(e).__name__}: {e}")


# ─────────────────────────────────────────────────────────────────────
# Controls: Add / Remove / Import / Export
# ─────────────────────────────────────────────────────────────────────
def _render_controls():
    """Render add-holding form and import/export buttons."""
    user_id = st.session_state["user_id"]

    # ── Header row: labels ──
    lbl_add, _, _, _, _, lbl_import, lbl_export = st.columns([2, 1, 1, 1, 1, 1, 1])
    with lbl_add:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px">'
            f'ADD HOLDING</p>',
            unsafe_allow_html=True,
        )
    with lbl_import:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px;text-align:center">'
            f'IMPORT</p>',
            unsafe_allow_html=True,
        )
    with lbl_export:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px;text-align:center">'
            f'EXPORT</p>',
            unsafe_allow_html=True,
        )

    # ── Form row: all controls on one line ──
    st.markdown("""
<style>
[data-testid="stFileUploader"] {
    padding: 0 !important;
    margin: 0 !important;
}
[data-testid="stFileUploader"] > section {
    padding: 0 !important;
    margin: 0 !important;
}
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploadDropzone"] {
    all: unset !important;
    display: block !important;
}
[data-testid="stFileUploaderDropzone"] > div,
[data-testid="stFileUploadDropzone"] > div {
    display: none !important;
}
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stFileUploadDropzone"] button {
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

    c_sym, c_qty, c_price, c_date, c_add, c_browse, c_save = st.columns(
        [2, 1, 1, 1, 1, 1, 1]
    )

    with c_sym:
        symbol = st.selectbox(
            "SYMBOL", NIFTY_500_SYMBOLS, index=0,
            label_visibility="collapsed",
        )
    with c_qty:
        qty = st.number_input(
            "QTY", min_value=1, value=1, step=1,
            label_visibility="collapsed",
        )
    with c_price:
        avg_price = st.number_input(
            "AVG PRICE (₹)", min_value=0.01, value=100.0,
            step=0.5, format="%.2f",
            label_visibility="collapsed",
        )
    with c_date:
        buy_date = st.date_input(
            "BUY DATE", value=date.today(),
            label_visibility="collapsed",
        )
    with c_add:
        if st.button("ADD", use_container_width=True):
            holdings = st.session_state[_STATE_KEY]
            existing_idx = next(
                (i for i, h in enumerate(holdings) if h["symbol"] == symbol),
                None,
            )

            if existing_idx is not None:
                # Merge with weighted average price
                existing = holdings[existing_idx]
                old_qty = int(existing["qty"])
                old_avg = float(existing["avg_price"])
                add_qty = int(qty)
                add_avg = float(avg_price)
                merged_qty = old_qty + add_qty
                merged_avg = (old_qty * old_avg + add_qty * add_avg) / merged_qty

                from data.database import update_holding_qty_and_price
                update_holding_qty_and_price(
                    user_id, existing["_db_id"], merged_qty, merged_avg,
                )
                existing["qty"] = merged_qty
                existing["avg_price"] = merged_avg
                logger.info(
                    f"m10_portfolio | ADD (MERGE) | {symbol} "
                    f"old_qty={old_qty} add_qty={add_qty} merged_qty={merged_qty} "
                    f"old_avg={old_avg:.2f} merged_avg={merged_avg:.2f}"
                )
            else:
                new_holding = {
                    "symbol": symbol,
                    "qty": int(qty),
                    "avg_price": float(avg_price),
                    "buy_date": buy_date.isoformat(),
                }
                from data.database import save_holding
                new_holding["_db_id"] = save_holding(user_id, new_holding)
                st.session_state[_STATE_KEY].append(new_holding)
                logger.info(
                    f"m10_portfolio | ADD | {symbol} qty={qty} "
                    f"avg={avg_price} date={buy_date}"
                )
            st.rerun()

    with c_browse:
        uploaded = st.file_uploader(
            "LOAD JSON", type=["json"], label_visibility="collapsed",
        )
        if uploaded is not None:
            try:
                data = json.loads(uploaded.read())
                if not isinstance(data, list):
                    st.error("JSON must be a list of holdings")
                else:
                    required = {"symbol", "qty", "avg_price", "buy_date"}
                    invalid = [
                        i for i, h in enumerate(data)
                        if not isinstance(h, dict) or not required.issubset(h)
                    ]
                    if invalid:
                        st.error(f"Invalid holdings at indices: {invalid[:5]}. Each must have: {', '.join(sorted(required))}")
                    else:
                        from data.database import replace_all_holdings
                        replace_all_holdings(user_id, data)
                        from data.database import load_holdings
                        st.session_state[_STATE_KEY] = load_holdings(user_id)
                        logger.info(
                            f"m10_portfolio | IMPORT | {len(data)} holdings loaded"
                        )
                        st.rerun()
            except (json.JSONDecodeError, Exception) as e:
                st.error(f"Import failed: {e}")

    with c_save:
        if st.session_state[_STATE_KEY]:
            export_data = [
                {k: v for k, v in h.items() if k != "_db_id"}
                for h in st.session_state[_STATE_KEY]
            ]
            portfolio_json = json.dumps(export_data, indent=2)
            st.download_button(
                "SAVE", portfolio_json,
                file_name="portfolio.json",
                mime="application/json",
                use_container_width=True,
            )

    # ── Reduce / Remove holding ──
    holdings = st.session_state[_STATE_KEY]
    if holdings:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px;'
            f'margin-top:8px">REDUCE / REMOVE HOLDING</p>',
            unsafe_allow_html=True,
        )
        rm_c1, rm_c2, rm_c3 = st.columns([3, 1, 1])
        with rm_c1:
            rm_idx = st.selectbox(
                "SELECT HOLDING", range(len(holdings)),
                format_func=lambda i: holdings[i]["symbol"],
                label_visibility="collapsed",
            )
        selected = holdings[rm_idx]
        with rm_c2:
            reduce_qty = st.number_input(
                "QTY", min_value=1, max_value=int(selected["qty"]),
                value=int(selected["qty"]), step=1,
                label_visibility="collapsed",
                key="rm_qty",
            )
        with rm_c3:
            if st.button("REMOVE", use_container_width=True):
                new_qty = int(selected["qty"]) - int(reduce_qty)
                if "_db_id" in selected:
                    from data.database import update_holding_qty, remove_holding
                    if new_qty <= 0:
                        remove_holding(user_id, selected["_db_id"])
                        holdings.pop(rm_idx)
                        logger.info(f"m10_portfolio | REMOVE | {selected['symbol']}")
                    else:
                        update_holding_qty(user_id, selected["_db_id"], new_qty)
                        holdings[rm_idx]["qty"] = new_qty
                        logger.info(f"m10_portfolio | REDUCE | {selected['symbol']} qty={new_qty}")
                else:
                    if new_qty <= 0:
                        holdings.pop(rm_idx)
                    else:
                        holdings[rm_idx]["qty"] = new_qty
                st.rerun()


# ─────────────────────────────────────────────────────────────────────
# Live price fetching
# ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _fetch_live_prices_cached(symbols_tuple):
    """Fetch live prices for a tuple of symbols (cacheable)."""
    from data.nse_live import get_stock_quote

    result = {}
    for sym in symbols_tuple:
        quote = get_stock_quote(sym)
        if quote:
            result[sym] = {
                "ltp": quote.get("lastPrice", 0),
                "change": quote.get("change", 0),
                "pChange": quote.get("pChange", 0),
                "previousClose": quote.get("previousClose", 0),
            }
        else:
            logger.warning(f"m10_portfolio | price fetch failed for {sym}")
            result[sym] = None
    return result


def _fetch_live_prices(holdings):
    """Fetch live prices for all unique symbols in holdings."""
    symbols = list({h["symbol"] for h in holdings})
    symbols.sort()
    with st.spinner(f"Fetching live prices for {len(symbols)} symbols..."):
        return _fetch_live_prices_cached(tuple(symbols))


# ─────────────────────────────────────────────────────────────────────
# XIRR Calculation
# ─────────────────────────────────────────────────────────────────────
def _compute_xirr(holdings, live_data):
    """Compute XIRR (Extended Internal Rate of Return) using scipy.optimize.

    XIRR solves for r in: sum(cashflow_i / (1+r)^((date_i - date_0)/365)) = 0
    """
    from scipy.optimize import brentq
    from datetime import date as date_type

    cashflows = []
    dates = []

    for h in holdings:
        # Negative cashflow = money invested (buy)
        cashflows.append(-h["qty"] * h["avg_price"])
        buy_date = h.get("buy_date")
        if isinstance(buy_date, str):
            buy_date = date_type.fromisoformat(buy_date)
        dates.append(buy_date)

    # Positive cashflow = current value (as if selling today)
    total_current = 0.0
    for h in holdings:
        ld = live_data.get(h["symbol"])
        ltp = ld["ltp"] if ld else h["avg_price"]
        total_current += h["qty"] * ltp

    cashflows.append(total_current)
    dates.append(date_type.today())

    if not cashflows or len(cashflows) < 2:
        return None

    # Reference date
    d0 = min(dates)
    day_fractions = [(d - d0).days / 365.0 for d in dates]

    def npv(rate):
        return sum(cf / (1 + rate) ** t for cf, t in zip(cashflows, day_fractions))

    try:
        xirr = brentq(npv, -0.99, 10.0, maxiter=1000)
        return xirr
    except (ValueError, RuntimeError):
        return None


# ─────────────────────────────────────────────────────────────────────
# Portfolio Summary
# ─────────────────────────────────────────────────────────────────────
def _render_summary(holdings, live_data):
    """Render top-level portfolio summary metrics."""
    total_invested = 0.0
    current_value = 0.0
    day_pnl = 0.0

    for h in holdings:
        qty = h["qty"]
        avg = h["avg_price"]
        total_invested += qty * avg

        ld = live_data.get(h["symbol"])
        if ld:
            ltp = ld["ltp"]
            prev = ld["previousClose"]
            current_value += qty * ltp
            day_pnl += qty * (ltp - prev)
        else:
            # If live price unavailable, use avg_price as fallback
            current_value += qty * avg

    total_pnl = current_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0
    day_pnl_pct = (day_pnl / (current_value - day_pnl) * 100) if (current_value - day_pnl) else 0

    xirr = _compute_xirr(holdings, live_data)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    _metric_card(c1, "TOTAL INVESTED", format_inr(total_invested), COLORS["text"])
    _metric_card(c2, "CURRENT VALUE", format_inr(current_value), COLORS["amber"])
    _metric_card(
        c3, "TOTAL P&L",
        f"{format_inr(total_pnl)} ({total_pnl_pct:+.2f}%)",
        color_change(total_pnl),
    )
    if xirr is not None:
        xirr_display = f"{xirr * 100:+.2f}%"
        xirr_color = color_change(xirr)
    else:
        xirr_display = "\u2014"
        xirr_color = COLORS["muted"]
    _metric_card(c4, "XIRR", xirr_display, xirr_color)
    _metric_card(
        c5, "DAY'S P&L",
        f"{format_inr(day_pnl)} ({day_pnl_pct:+.2f}%)",
        color_change(day_pnl),
    )
    _metric_card(c6, "HOLDINGS", str(len(holdings)), COLORS["amber"])


def _metric_card(col, label, value, value_color):
    """Render a compact Bloomberg-style metric card."""
    col.markdown(
        f'<div style="text-align:center;padding:6px;border:1px solid {COLORS["border"]};'
        f'border-radius:2px;background:{COLORS["panel"]}">'
        f'<div style="color:{COLORS["muted"]};font-size:10px;font-family:monospace">{label}</div>'
        f'<div style="color:{value_color};font-size:14px;font-weight:bold;font-family:monospace;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
        f'{value}</div></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────
# Holdings Table
# ─────────────────────────────────────────────────────────────────────
def _render_holdings_table(holdings, live_data):
    """Render the holdings as a Bloomberg-style HTML table."""
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;font-weight:bold;'
        f'margin-bottom:4px">HOLDINGS</p>',
        unsafe_allow_html=True,
    )

    # Compute total current value for weight calculation
    total_current = 0.0
    for h in holdings:
        ld = live_data.get(h["symbol"])
        if ld:
            total_current += h["qty"] * ld["ltp"]
        else:
            total_current += h["qty"] * h["avg_price"]

    # Table header
    columns = [
        "SYMBOL", "SECTOR", "QTY", "AVG PRICE", "LTP", "CHANGE",
        "P&L (₹)", "P&L (%)", "VALUE", "WEIGHT %", "BUY DATE",
    ]
    header_cells = ""
    for c in columns:
        align = "left" if c in ("SYMBOL", "SECTOR", "BUY DATE") else "right"
        header_cells += (
            f'<th style="color:{COLORS["amber"]};padding:4px 8px;text-align:{align};'
            f'border-bottom:1px solid {COLORS["border"]};font-size:10px;'
            f'white-space:nowrap">{c}</th>'
        )

    # Table rows
    rows = ""
    for h in holdings:
        sym = h["symbol"]
        qty = h["qty"]
        avg = h["avg_price"]
        buy_date = h.get("buy_date", "—")
        sector = get_nifty_500_map().get(sym, "Other")

        ld = live_data.get(sym)
        if ld:
            ltp = ld["ltp"]
            change = ld["change"]
            p_change = ld["pChange"]
        else:
            ltp = avg
            change = 0
            p_change = 0

        pnl = (ltp - avg) * qty
        pnl_pct = ((ltp - avg) / avg * 100) if avg else 0
        value = ltp * qty
        weight = (value / total_current * 100) if total_current else 0

        chg_color = color_change(change)
        pnl_color = color_change(pnl)
        cell = "padding:3px 8px;font-size:11px;border-bottom:1px solid #1A1A1A;white-space:nowrap"

        rows += (
            f'<tr>'
            f'<td style="{cell};text-align:left;color:{COLORS["amber"]};font-weight:bold">{sym}</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["muted"]}">{sector}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{qty:,}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{format_inr(avg)}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{format_inr(ltp)}</td>'
            f'<td style="{cell};text-align:right;color:{chg_color}">'
            f'{change:+.2f} ({p_change:+.2f}%)</td>'
            f'<td style="{cell};text-align:right;color:{pnl_color}">{format_inr(pnl)}</td>'
            f'<td style="{cell};text-align:right;color:{pnl_color}">{pnl_pct:+.2f}%</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{format_inr(value)}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["blue"]}">{weight:.1f}%</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["muted"]}">{buy_date}</td>'
            f'</tr>'
        )

    html = (
        f'<div style="overflow-x:auto">'
        f'<table style="width:100%;border-collapse:collapse;font-family:monospace">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# Allocation Charts
# ─────────────────────────────────────────────────────────────────────
def _render_allocation_pie(holdings, live_data):
    """Render allocation pie chart by stock."""
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;font-weight:bold;'
        f'margin-bottom:4px">ALLOCATION BY STOCK</p>',
        unsafe_allow_html=True,
    )

    labels = []
    values = []
    for h in holdings:
        sym = h["symbol"]
        ld = live_data.get(sym)
        ltp = ld["ltp"] if ld else h["avg_price"]
        val = h["qty"] * ltp

        # Aggregate if same symbol appears multiple times
        if sym in labels:
            idx = labels.index(sym)
            values[idx] += val
        else:
            labels.append(sym)
            values.append(val)

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        textinfo="percent",
        textposition="inside",
        insidetextorientation="radial",
        textfont=dict(size=10, family="monospace"),
        marker=dict(
            colors=[
                COLORS["amber"], COLORS["green"], COLORS["blue"],
                COLORS["red"], "#CC66FF", "#FFCC00", "#33CCCC",
                "#FF6633", "#66FF66", "#FF99CC", "#999999",
                "#CC9966", "#996633", "#669999", "#CC6699",
            ][:len(labels)],
            line=dict(color=COLORS["bg"], width=1),
        ),
        hovertemplate="<b>%{label}</b><br>Value: ₹%{value:,.0f}<br>"
                      "Weight: %{percent}<extra></extra>",
    )])

    fig.update_layout(**plotly_layout(
        height=350,
        showlegend=True,
        legend=dict(
            orientation="v",
            x=1.02, y=0.5,
            xanchor="left", yanchor="middle",
            font=dict(size=10, family="monospace", color=COLORS["text"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=10, r=120, t=10, b=10),
    ))
    st.plotly_chart(fig, use_container_width=True)


def _render_sector_pie(holdings, live_data):
    """Render allocation pie chart by sector."""
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;font-weight:bold;'
        f'margin-bottom:4px">ALLOCATION BY SECTOR</p>',
        unsafe_allow_html=True,
    )

    sector_values = {}
    for h in holdings:
        sym = h["symbol"]
        sector = get_nifty_500_map().get(sym, "Other")
        ld = live_data.get(sym)
        ltp = ld["ltp"] if ld else h["avg_price"]
        val = h["qty"] * ltp
        sector_values[sector] = sector_values.get(sector, 0) + val

    labels = list(sector_values.keys())
    values = list(sector_values.values())
    colors = [SECTOR_COLORS.get(s, COLORS["muted"]) for s in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        textinfo="percent",
        textposition="inside",
        insidetextorientation="radial",
        textfont=dict(size=10, family="monospace"),
        marker=dict(
            colors=colors,
            line=dict(color=COLORS["bg"], width=1),
        ),
        hovertemplate="<b>%{label}</b><br>Value: ₹%{value:,.0f}<br>"
                      "Weight: %{percent}<extra></extra>",
    )])

    fig.update_layout(**plotly_layout(
        height=350,
        showlegend=True,
        legend=dict(
            orientation="v",
            x=1.02, y=0.5,
            xanchor="left", yanchor="middle",
            font=dict(size=10, family="monospace", color=COLORS["text"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=10, r=120, t=10, b=10),
    ))
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────
# Daily P&L Chart
# ─────────────────────────────────────────────────────────────────────
def _render_daily_pnl_chart(holdings, live_data):
    """Render a bar chart showing per-holding P&L for the day."""
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;font-weight:bold;'
        f'margin-bottom:4px">DAY\'S P&L BY HOLDING</p>',
        unsafe_allow_html=True,
    )

    symbols = []
    day_pnls = []
    bar_colors = []

    for h in holdings:
        sym = h["symbol"]
        ld = live_data.get(sym)
        if ld:
            dpnl = h["qty"] * ld["change"]
        else:
            dpnl = 0.0

        # Aggregate if same symbol appears multiple times
        if sym in symbols:
            idx = symbols.index(sym)
            day_pnls[idx] += dpnl
        else:
            symbols.append(sym)
            day_pnls.append(dpnl)
            bar_colors.append(COLORS["green"] if dpnl >= 0 else COLORS["red"])

    # Recompute colors after aggregation
    bar_colors = [COLORS["green"] if v >= 0 else COLORS["red"] for v in day_pnls]

    fig = go.Figure(data=[go.Bar(
        x=symbols,
        y=day_pnls,
        marker_color=bar_colors,
        text=[f"₹{v:+,.0f}" for v in day_pnls],
        textposition="outside",
        textfont=dict(size=10, family="monospace"),
        hovertemplate="<b>%{x}</b><br>Day P&L: ₹%{y:+,.2f}<extra></extra>",
    )])

    fig.update_layout(**plotly_layout(
        height=300,
        xaxis_title="",
        yaxis_title="Day's P&L (₹)",
        showlegend=False,
    ))
    st.plotly_chart(fig, use_container_width=True)
