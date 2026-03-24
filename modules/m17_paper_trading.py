"""Module 17: Paper Trading (Simulated Trading)."""

from datetime import datetime

import pytz
import streamlit as st

from config import COLORS, NIFTY_200_SYMBOLS, plotly_layout
from utils.formatting import format_inr, color_change
from utils.logger import logger

# ── Session state keys ──
_BAL_KEY = "paper_balance"
_ORD_KEY = "paper_orders"

_DEFAULT_BALANCE = 1_000_000.0


def render():
    """Render the Paper Trading module."""
    st.markdown("### PAPER TRADING")

    _init_state()

    # ── Order form ──
    _render_order_form()

    st.divider()

    # ── Summary metrics ──
    _render_summary()

    st.divider()

    # ── Open positions ──
    _render_positions()

    st.divider()

    # ── Order book ──
    _render_order_book()

    st.divider()

    # ── Performance stats ──
    _render_performance()

    st.divider()

    # ── Controls ──
    _render_controls()


# ─────────────────────────────────────────────────────────────────────
# Initialization
# ─────────────────────────────────────────────────────────────────────
def _init_state():
    """Load paper trading state from DB into session_state."""
    if _BAL_KEY not in st.session_state:
        from data.database import load_paper_balance
        st.session_state[_BAL_KEY] = load_paper_balance()
    if _ORD_KEY not in st.session_state:
        from data.database import load_paper_orders
        st.session_state[_ORD_KEY] = load_paper_orders()


# ─────────────────────────────────────────────────────────────────────
# Position computation (derived from order history)
# ─────────────────────────────────────────────────────────────────────
def _compute_positions(orders):
    """Aggregate orders into net positions with avg cost.

    Process orders in chronological order (oldest first).
    Returns dict: symbol -> {"qty": int, "avg_cost": float, "invested": float}
    """
    positions = {}
    # Orders are stored newest-first, reverse for chronological processing
    for order in reversed(orders):
        sym = order["symbol"]
        if sym not in positions:
            positions[sym] = {"qty": 0, "avg_cost": 0.0, "invested": 0.0}
        pos = positions[sym]
        if order["side"] == "BUY":
            new_invested = pos["invested"] + order["total"]
            new_qty = pos["qty"] + order["qty"]
            pos["qty"] = new_qty
            pos["invested"] = new_invested
            pos["avg_cost"] = new_invested / new_qty if new_qty > 0 else 0
        else:  # SELL
            pos["qty"] -= order["qty"]
            pos["invested"] = pos["avg_cost"] * pos["qty"] if pos["qty"] > 0 else 0
    # Filter out closed positions
    return {s: p for s, p in positions.items() if p["qty"] > 0}


def _compute_realized_pnl(orders):
    """Compute realized P&L by replaying order history.

    Returns (total_realized, trades_list) where trades_list contains
    individual sell trade P&L entries.
    """
    positions = {}
    trades = []

    for order in reversed(orders):  # chronological
        sym = order["symbol"]
        if sym not in positions:
            positions[sym] = {"qty": 0, "avg_cost": 0.0, "invested": 0.0}
        pos = positions[sym]
        if order["side"] == "BUY":
            new_invested = pos["invested"] + order["total"]
            new_qty = pos["qty"] + order["qty"]
            pos["qty"] = new_qty
            pos["invested"] = new_invested
            pos["avg_cost"] = new_invested / new_qty if new_qty > 0 else 0
        else:  # SELL
            pnl = (order["price"] - pos["avg_cost"]) * order["qty"]
            trades.append({
                "symbol": sym,
                "qty": order["qty"],
                "buy_avg": pos["avg_cost"],
                "sell_price": order["price"],
                "pnl": pnl,
                "timestamp": order["timestamp"],
            })
            pos["qty"] -= order["qty"]
            pos["invested"] = pos["avg_cost"] * pos["qty"] if pos["qty"] > 0 else 0

    total_realized = sum(t["pnl"] for t in trades)
    return total_realized, trades


# ─────────────────────────────────────────────────────────────────────
# Order Form
# ─────────────────────────────────────────────────────────────────────
def _render_order_form():
    """Render the buy/sell order form."""
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;font-weight:bold;'
        f'margin-bottom:4px">PLACE ORDER</p>',
        unsafe_allow_html=True,
    )

    c_sym, c_ltp, c_side, c_qty, c_btn = st.columns([2, 1, 1, 1, 1])

    with c_sym:
        symbol = st.selectbox(
            "SYMBOL", NIFTY_200_SYMBOLS, index=0,
            key="m17_symbol", label_visibility="collapsed",
        )

    # Fetch current LTP
    from data.nse_live import get_stock_quote
    quote = get_stock_quote(symbol)
    ltp = quote["lastPrice"] if quote else 0

    with c_ltp:
        if quote:
            pchg = quote["pChange"]
            chg_color = COLORS["green"] if pchg >= 0 else COLORS["red"]
            st.markdown(
                f'<div style="text-align:center;padding:4px 0">'
                f'<div style="color:{COLORS["muted"]};font-size:9px">LTP</div>'
                f'<div style="color:{COLORS["text"]};font-size:14px;font-weight:bold">'
                f'{format_inr(ltp)}</div>'
                f'<div style="color:{chg_color};font-size:10px">{pchg:+.2f}%</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="text-align:center;padding:4px 0;color:{COLORS["muted"]};'
                f'font-size:11px">LTP: —</div>',
                unsafe_allow_html=True,
            )

    with c_side:
        side = st.selectbox(
            "SIDE", ["BUY", "SELL"], key="m17_side",
            label_visibility="collapsed",
        )

    with c_qty:
        qty = st.number_input(
            "QTY", min_value=1, value=1, step=1,
            key="m17_qty", label_visibility="collapsed",
        )

    with c_btn:
        if st.button("EXECUTE", use_container_width=True, key="m17_exec_btn"):
            if ltp <= 0:
                st.error("Cannot execute: price unavailable.")
                return

            total = ltp * qty
            balance = st.session_state[_BAL_KEY]
            positions = _compute_positions(st.session_state[_ORD_KEY])

            # Validate
            if side == "BUY":
                if total > balance:
                    st.error(
                        f"Insufficient balance. Need {format_inr(total)}, "
                        f"have {format_inr(balance)}."
                    )
                    return
            else:  # SELL
                held_qty = positions.get(symbol, {}).get("qty", 0)
                if qty > held_qty:
                    st.error(
                        f"Insufficient holdings. Have {held_qty} shares of {symbol}, "
                        f"trying to sell {qty}."
                    )
                    return

            # Execute
            ist = pytz.timezone("Asia/Kolkata")
            order = {
                "symbol": symbol,
                "side": side,
                "qty": int(qty),
                "price": float(ltp),
                "total": float(total),
                "timestamp": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S"),
            }

            # Update balance
            if side == "BUY":
                new_balance = balance - total
            else:
                new_balance = balance + total

            # Persist
            from data.database import save_paper_order, update_paper_balance
            save_paper_order(order)
            update_paper_balance(new_balance)

            # Update session state
            st.session_state[_ORD_KEY].insert(0, order)  # newest first
            st.session_state[_BAL_KEY] = new_balance

            logger.info(
                f"m17_paper | {side} | {symbol} qty={qty} price={ltp:.2f} "
                f"total={total:.2f} balance={new_balance:.2f}"
            )
            st.toast(
                f"{side} {qty} x {symbol} @ {format_inr(ltp)}",
                icon="✅",
            )
            st.rerun()

    # Show order preview
    if ltp > 0:
        preview_total = ltp * qty
        st.markdown(
            f'<div style="color:{COLORS["muted"]};font-size:11px;font-family:monospace;'
            f'margin-top:4px">'
            f'Order: {side} {qty} x {symbol} @ {format_inr(ltp)} = {format_inr(preview_total)}'
            f'  |  Balance: {format_inr(st.session_state[_BAL_KEY])}'
            f'</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────
# Summary Metrics
# ─────────────────────────────────────────────────────────────────────
def _render_summary():
    """Render 6 summary metric cards."""
    balance = st.session_state[_BAL_KEY]
    orders = st.session_state[_ORD_KEY]
    positions = _compute_positions(orders)
    realized_pnl, trades = _compute_realized_pnl(orders)

    # Compute current value of open positions
    invested = 0.0
    current_value = 0.0
    if positions:
        from data.nse_live import get_stock_quote
        for sym, pos in positions.items():
            invested += pos["invested"]
            quote = get_stock_quote(sym)
            if quote:
                current_value += pos["qty"] * quote["lastPrice"]
            else:
                current_value += pos["invested"]

    unrealized_pnl = current_value - invested
    total_pnl = realized_pnl + unrealized_pnl
    portfolio_value = balance + current_value
    total_return_pct = (portfolio_value / _DEFAULT_BALANCE - 1) * 100

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    _metric_card(c1, "CASH BALANCE", format_inr(balance), COLORS["text"])
    _metric_card(c2, "PORTFOLIO VALUE", format_inr(portfolio_value), COLORS["amber"])
    _metric_card(
        c3, "TOTAL P&L",
        f"{format_inr(total_pnl)} ({total_return_pct:+.2f}%)",
        color_change(total_pnl),
    )
    _metric_card(
        c4, "UNREALIZED P&L",
        format_inr(unrealized_pnl),
        color_change(unrealized_pnl),
    )
    _metric_card(
        c5, "REALIZED P&L",
        format_inr(realized_pnl),
        color_change(realized_pnl),
    )
    _metric_card(c6, "TOTAL ORDERS", str(len(orders)), COLORS["amber"])


def _metric_card(col, label, value, value_color):
    """Render a compact Bloomberg-style metric card."""
    col.markdown(
        f'<div style="text-align:center;padding:6px;border:1px solid {COLORS["border"]};'
        f'border-radius:2px;background:{COLORS["panel"]}">'
        f'<div style="color:{COLORS["muted"]};font-size:10px;font-family:monospace">{label}</div>'
        f'<div style="color:{value_color};font-size:16px;font-weight:bold;font-family:monospace">'
        f'{value}</div></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────
# Open Positions
# ─────────────────────────────────────────────────────────────────────
def _render_positions():
    """Render open positions table with live P&L."""
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;font-weight:bold;'
        f'margin-bottom:4px">OPEN POSITIONS</p>',
        unsafe_allow_html=True,
    )

    orders = st.session_state[_ORD_KEY]
    positions = _compute_positions(orders)

    if not positions:
        st.markdown(
            f'<div style="text-align:center;padding:20px;color:{COLORS["muted"]};'
            f'font-family:monospace;font-size:12px">'
            f'No open positions.</div>',
            unsafe_allow_html=True,
        )
        return

    from data.nse_live import get_stock_quote

    columns = ["SYMBOL", "QTY", "AVG COST", "LTP", "VALUE", "P&L (₹)", "P&L (%)"]
    header_cells = ""
    for c in columns:
        align = "left" if c == "SYMBOL" else "right"
        header_cells += (
            f'<th style="color:{COLORS["amber"]};padding:4px 8px;text-align:{align};'
            f'border-bottom:1px solid {COLORS["border"]};font-size:10px;'
            f'white-space:nowrap">{c}</th>'
        )

    rows = ""
    cell = (
        f"padding:3px 8px;font-size:11px;font-family:monospace;"
        f"border-bottom:1px solid #1A1A1A;white-space:nowrap"
    )

    for sym, pos in sorted(positions.items()):
        qty = pos["qty"]
        avg_cost = pos["avg_cost"]
        quote = get_stock_quote(sym)
        ltp = quote["lastPrice"] if quote else avg_cost
        value = qty * ltp
        pnl = (ltp - avg_cost) * qty
        pnl_pct = ((ltp - avg_cost) / avg_cost * 100) if avg_cost else 0
        pnl_color = color_change(pnl)

        rows += (
            f'<tr>'
            f'<td style="{cell};text-align:left;color:{COLORS["blue"]};font-weight:bold">{sym}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{qty:,}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{format_inr(avg_cost)}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{format_inr(ltp)}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{format_inr(value)}</td>'
            f'<td style="{cell};text-align:right;color:{pnl_color}">{format_inr(pnl)}</td>'
            f'<td style="{cell};text-align:right;color:{pnl_color}">{pnl_pct:+.2f}%</td>'
            f'</tr>'
        )

    html = (
        f'<div style="overflow-x:auto">'
        f'<table style="width:100%;border-collapse:collapse;font-family:monospace">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    st.caption(f"{len(positions)} open position{'s' if len(positions) != 1 else ''}")


# ─────────────────────────────────────────────────────────────────────
# Order Book
# ─────────────────────────────────────────────────────────────────────
def _render_order_book():
    """Render all orders (most recent first)."""
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;font-weight:bold;'
        f'margin-bottom:4px">ORDER BOOK</p>',
        unsafe_allow_html=True,
    )

    orders = st.session_state[_ORD_KEY]
    if not orders:
        st.markdown(
            f'<div style="text-align:center;padding:20px;color:{COLORS["muted"]};'
            f'font-family:monospace;font-size:12px">'
            f'No orders placed yet.</div>',
            unsafe_allow_html=True,
        )
        return

    columns = ["#", "TIMESTAMP", "SYMBOL", "SIDE", "QTY", "PRICE", "TOTAL", "STATUS"]
    header_cells = ""
    for c in columns:
        align = "left" if c in ("TIMESTAMP", "SYMBOL", "STATUS") else "right"
        if c in ("#", "SIDE"):
            align = "center"
        header_cells += (
            f'<th style="color:{COLORS["amber"]};padding:4px 8px;text-align:{align};'
            f'border-bottom:1px solid {COLORS["border"]};font-size:10px;'
            f'white-space:nowrap">{c}</th>'
        )

    rows = ""
    cell = (
        f"padding:3px 8px;font-size:11px;font-family:monospace;"
        f"border-bottom:1px solid #1A1A1A;white-space:nowrap"
    )

    for i, order in enumerate(orders):
        side_color = COLORS["green"] if order["side"] == "BUY" else COLORS["red"]
        rows += (
            f'<tr>'
            f'<td style="{cell};text-align:right;color:{COLORS["muted"]}">{i + 1}</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["muted"]}">{order["timestamp"]}</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["blue"]};font-weight:bold">'
            f'{order["symbol"]}</td>'
            f'<td style="{cell};text-align:center;color:{side_color};font-weight:bold">'
            f'{order["side"]}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{order["qty"]:,}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">'
            f'{format_inr(order["price"])}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">'
            f'{format_inr(order["total"])}</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["green"]}">'
            f'{order.get("status", "FILLED")}</td>'
            f'</tr>'
        )

    html = (
        f'<div style="overflow-x:auto;max-height:400px;overflow-y:auto">'
        f'<table style="width:100%;border-collapse:collapse;font-family:monospace">'
        f'<thead style="position:sticky;top:0;background:{COLORS["bg"]}">'
        f'<tr>{header_cells}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    st.caption(f"{len(orders)} order{'s' if len(orders) != 1 else ''}")


# ─────────────────────────────────────────────────────────────────────
# Performance Stats
# ─────────────────────────────────────────────────────────────────────
def _render_performance():
    """Render realized P&L stats."""
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;font-weight:bold;'
        f'margin-bottom:4px">TRADE PERFORMANCE</p>',
        unsafe_allow_html=True,
    )

    orders = st.session_state[_ORD_KEY]
    realized_pnl, trades = _compute_realized_pnl(orders)

    if not trades:
        st.markdown(
            f'<div style="text-align:center;padding:20px;color:{COLORS["muted"]};'
            f'font-family:monospace;font-size:12px">'
            f'No closed trades yet. Sell positions to see performance.</div>',
            unsafe_allow_html=True,
        )
        return

    winners = [t for t in trades if t["pnl"] > 0]
    losers = [t for t in trades if t["pnl"] < 0]
    win_rate = len(winners) / len(trades) * 100 if trades else 0
    best = max(trades, key=lambda t: t["pnl"])
    worst = min(trades, key=lambda t: t["pnl"])
    avg_pnl = realized_pnl / len(trades) if trades else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    _metric_card(c1, "REALIZED P&L", format_inr(realized_pnl), color_change(realized_pnl))
    _metric_card(c2, "WIN RATE", f"{win_rate:.1f}%",
                 COLORS["green"] if win_rate >= 50 else COLORS["red"])
    _metric_card(c3, "BEST TRADE",
                 f"{best['symbol']} {format_inr(best['pnl'])}",
                 COLORS["green"])
    _metric_card(c4, "WORST TRADE",
                 f"{worst['symbol']} {format_inr(worst['pnl'])}",
                 COLORS["red"])
    _metric_card(c5, "AVG P&L/TRADE", format_inr(avg_pnl), color_change(avg_pnl))

    # Trades table
    if trades:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:4px;'
            f'margin-top:12px">CLOSED TRADES</p>',
            unsafe_allow_html=True,
        )
        columns = ["#", "SYMBOL", "QTY", "BUY AVG", "SELL PRICE", "P&L", "DATE"]
        header_cells = ""
        for c in columns:
            align = "left" if c in ("SYMBOL", "DATE") else "right"
            if c == "#":
                align = "center"
            header_cells += (
                f'<th style="color:{COLORS["amber"]};padding:4px 8px;text-align:{align};'
                f'border-bottom:1px solid {COLORS["border"]};font-size:10px;'
                f'white-space:nowrap">{c}</th>'
            )

        rows = ""
        cell = (
            f"padding:3px 8px;font-size:11px;font-family:monospace;"
            f"border-bottom:1px solid #1A1A1A;white-space:nowrap"
        )
        for i, t in enumerate(reversed(trades)):  # most recent first
            pnl_color = color_change(t["pnl"])
            rows += (
                f'<tr>'
                f'<td style="{cell};text-align:center;color:{COLORS["muted"]}">{i + 1}</td>'
                f'<td style="{cell};text-align:left;color:{COLORS["blue"]};font-weight:bold">'
                f'{t["symbol"]}</td>'
                f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{t["qty"]:,}</td>'
                f'<td style="{cell};text-align:right;color:{COLORS["text"]}">'
                f'{format_inr(t["buy_avg"])}</td>'
                f'<td style="{cell};text-align:right;color:{COLORS["text"]}">'
                f'{format_inr(t["sell_price"])}</td>'
                f'<td style="{cell};text-align:right;color:{pnl_color}">'
                f'{format_inr(t["pnl"])}</td>'
                f'<td style="{cell};text-align:left;color:{COLORS["muted"]}">'
                f'{t["timestamp"]}</td>'
                f'</tr>'
            )

        html = (
            f'<div style="overflow-x:auto;max-height:300px;overflow-y:auto">'
            f'<table style="width:100%;border-collapse:collapse;font-family:monospace">'
            f'<thead style="position:sticky;top:0;background:{COLORS["bg"]}">'
            f'<tr>{header_cells}</tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
        )
        st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# Controls
# ─────────────────────────────────────────────────────────────────────
def _render_controls():
    """Render reset button."""
    c1, _, _ = st.columns([1, 1, 4])
    with c1:
        if st.button("RESET PAPER PORTFOLIO", use_container_width=True, key="m17_reset_btn"):
            from data.database import clear_paper_trading
            clear_paper_trading()
            st.session_state[_BAL_KEY] = _DEFAULT_BALANCE
            st.session_state[_ORD_KEY] = []
            logger.info("m17_paper | RESET")
            st.toast("Paper portfolio reset.", icon="🔄")
            st.rerun()
