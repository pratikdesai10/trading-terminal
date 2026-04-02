"""Module 17: Paper Trading (Simulated Trading)."""

from datetime import datetime, timedelta

import pytz
import streamlit as st

from config import COLORS, NIFTY_500_SYMBOLS
from data.database import PAPER_DEFAULT_BALANCE
from utils.formatting import format_inr, color_change
from utils.logger import logger

# ── Session state keys ──
_BAL_KEY = "paper_balance"
_ORD_KEY = "paper_orders"


def render():
    """Render the Paper Trading module."""
    st.markdown("### PAPER TRADING")

    _init_state()

    # ── Order form ──
    _render_order_form()

    st.divider()

    # ── Live dashboard (auto-refresh summary + positions) ──
    auto_refresh = st.checkbox("Auto-refresh P&L (2s)", value=True, key="m17_auto_refresh")
    if auto_refresh:
        _live_dashboard()
    else:
        _render_summary()
        st.divider()
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
# Live Dashboard (auto-refreshing fragment)
# ─────────────────────────────────────────────────────────────────────
@st.fragment(run_every=timedelta(seconds=2))
def _live_dashboard():
    """Auto-refreshing summary + positions — reruns every 2s independently.

    Reloads orders and balance from DB on each tick so P&L reflects live prices.
    """
    from data.database import load_paper_orders, load_paper_balance
    user_id = st.session_state["user_id"]
    orders = load_paper_orders(user_id)
    balance = load_paper_balance(user_id)
    _render_summary(orders=orders, balance=balance)
    st.divider()
    _render_positions(orders=orders)


# ─────────────────────────────────────────────────────────────────────
# Initialization
# ─────────────────────────────────────────────────────────────────────
def _init_state():
    """Load paper trading state from DB into session_state."""
    user_id = st.session_state["user_id"]
    if _BAL_KEY not in st.session_state:
        from data.database import load_paper_balance
        st.session_state[_BAL_KEY] = load_paper_balance(user_id)
    if _ORD_KEY not in st.session_state:
        from data.database import load_paper_orders
        st.session_state[_ORD_KEY] = load_paper_orders(user_id)


# ─────────────────────────────────────────────────────────────────────
# Position computation (derived from order history)
# Net qty: positive = long, negative = short.
# BUY always adds qty, SELL always subtracts.
# First SELL with no prior BUY opens a short (negative qty).
# ─────────────────────────────────────────────────────────────────────
def _compute_positions(orders):
    """Aggregate BUY/SELL orders into net positions.

    Net qty > 0  → long position (avg_cost = avg buy price)
    Net qty < 0  → short position (avg_cost = avg short/sell price)
    Net qty == 0 → closed, excluded from result.

    Returns dict: symbol -> {"qty": int, "avg_cost": float, "invested": float}
    """
    positions = {}
    for order in reversed(orders):  # chronological (oldest first)
        sym = order["symbol"]
        if sym not in positions:
            positions[sym] = {"qty": 0, "avg_cost": 0.0, "invested": 0.0}
        pos = positions[sym]
        qty = order["qty"]
        price = order["price"]
        total = order["total"]

        if order["side"] == "BUY":
            prev_qty = pos["qty"]
            if prev_qty >= 0:
                # Adding to long or opening long from flat
                new_qty = prev_qty + qty
                pos["invested"] = pos["invested"] + total
                pos["avg_cost"] = pos["invested"] / new_qty if new_qty else 0
                pos["qty"] = new_qty
            else:
                # Covering a short position
                new_qty = prev_qty + qty
                if new_qty >= 0:
                    # Fully covered (possibly flipped to long)
                    pos["qty"] = new_qty
                    pos["invested"] = price * new_qty if new_qty > 0 else 0.0
                    pos["avg_cost"] = price if new_qty > 0 else 0.0
                else:
                    # Still short after cover
                    pos["qty"] = new_qty
                    # avg_cost stays the same (still short at same avg price)
        else:  # SELL
            prev_qty = pos["qty"]
            if prev_qty <= 0:
                # Adding to short or opening short from flat
                new_qty = prev_qty - qty
                # avg_cost for short = weighted avg sell price
                prev_short = abs(prev_qty)
                new_short = prev_short + qty
                pos["avg_cost"] = (
                    (pos["avg_cost"] * prev_short + price * qty) / new_short
                    if new_short else 0
                )
                pos["invested"] = pos["avg_cost"] * new_short
                pos["qty"] = new_qty
            else:
                # Reducing / closing long
                new_qty = prev_qty - qty
                if new_qty >= 0:
                    pos["qty"] = new_qty
                    pos["invested"] = pos["avg_cost"] * new_qty
                else:
                    # Crossed zero: sold more than held → now short
                    excess = abs(new_qty)
                    pos["qty"] = new_qty
                    pos["avg_cost"] = price
                    pos["invested"] = price * excess

    return {s: p for s, p in positions.items() if p["qty"] != 0}


def _compute_realized_pnl(orders):
    """Compute realized P&L by replaying BUY/SELL order history.

    A trade is closed when:
      - Long: SELL reduces or closes a long position → pnl = (sell - avg_buy) * qty
      - Short: BUY reduces or closes a short position → pnl = (avg_sell - buy) * qty

    Returns (total_realized, trades_list).
    """
    positions = {}
    trades = []

    for order in reversed(orders):  # chronological
        sym = order["symbol"]
        if sym not in positions:
            positions[sym] = {"qty": 0, "avg_cost": 0.0, "invested": 0.0}
        pos = positions[sym]
        qty = order["qty"]
        price = order["price"]
        total = order["total"]

        if order["side"] == "BUY":
            prev_qty = pos["qty"]
            if prev_qty < 0:
                # Covering a short — realize P&L on covered portion
                covered = min(qty, abs(prev_qty))
                pnl = (pos["avg_cost"] - price) * covered
                trades.append({
                    "symbol": sym,
                    "type": "SHORT",
                    "qty": covered,
                    "open_price": pos["avg_cost"],
                    "close_price": price,
                    "pnl": pnl,
                    "timestamp": order["timestamp"],
                })
                new_qty = prev_qty + qty
                if new_qty >= 0:
                    pos["qty"] = new_qty
                    pos["invested"] = price * new_qty if new_qty > 0 else 0.0
                    pos["avg_cost"] = price if new_qty > 0 else 0.0
                else:
                    pos["qty"] = new_qty
            else:
                # Adding to long
                new_qty = prev_qty + qty
                pos["invested"] = pos["invested"] + total
                pos["avg_cost"] = pos["invested"] / new_qty if new_qty else 0
                pos["qty"] = new_qty

        else:  # SELL
            prev_qty = pos["qty"]
            if prev_qty > 0:
                # Closing / reducing long — realize P&L on sold portion
                sold = min(qty, prev_qty)
                pnl = (price - pos["avg_cost"]) * sold
                trades.append({
                    "symbol": sym,
                    "type": "LONG",
                    "qty": sold,
                    "open_price": pos["avg_cost"],
                    "close_price": price,
                    "pnl": pnl,
                    "timestamp": order["timestamp"],
                })
                new_qty = prev_qty - qty
                if new_qty >= 0:
                    pos["qty"] = new_qty
                    pos["invested"] = pos["avg_cost"] * new_qty
                else:
                    # Crossed zero into short
                    excess = abs(new_qty)
                    pos["qty"] = new_qty
                    pos["avg_cost"] = price
                    pos["invested"] = price * excess
            else:
                # Opening / adding to short
                prev_short = abs(prev_qty)
                new_short = prev_short + qty
                pos["avg_cost"] = (
                    (pos["avg_cost"] * prev_short + price * qty) / new_short
                    if new_short else 0
                )
                pos["invested"] = pos["avg_cost"] * new_short
                pos["qty"] = prev_qty - qty

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
            "SYMBOL", NIFTY_500_SYMBOLS, index=0,
            key="m17_symbol", label_visibility="collapsed",
        )

    # Fetch current LTP
    from data.nse_live import get_stock_quote
    import pytz as _pytz
    _ist = _pytz.timezone("Asia/Kolkata")
    _now = datetime.now(_ist)
    _market_open = _now.weekday() < 5 and (9 * 60 + 15) <= (_now.hour * 60 + _now.minute) < (15 * 60 + 30)
    quote = get_stock_quote(symbol)
    ltp = quote["lastPrice"] if quote else 0

    with c_ltp:
        if quote:
            pchg = quote["pChange"]
            chg_color = COLORS["green"] if pchg >= 0 else COLORS["red"]
            price_label = "LTP" if _market_open else "PREV CLOSE"
            st.markdown(
                f'<div style="text-align:center;padding:4px 0">'
                f'<div style="color:{COLORS["muted"]};font-size:9px">{price_label}</div>'
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
            net_qty = positions.get(symbol, {}).get("qty", 0)

            # Validate
            if side == "BUY":
                if net_qty >= 0:
                    # Opening / adding to long — need cash
                    if total > balance:
                        st.error(
                            f"Insufficient balance. Need {format_inr(total)}, "
                            f"have {format_inr(balance)}."
                        )
                        return
                # If net_qty < 0: covering a short — cash comes back, always valid
            else:  # SELL
                if net_qty <= 0:
                    # Opening / adding to short — need cash as collateral
                    if total > balance:
                        st.error(
                            f"Insufficient balance for short collateral. "
                            f"Need {format_inr(total)}, have {format_inr(balance)}."
                        )
                        return
                # If net_qty > 0: selling a long — always valid (can sell up to held qty freely)

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

            # Update balance: BUY costs cash (or returns it when covering short),
            # SELL returns cash (or costs it as short collateral).
            # In both cases the accounting is the same: BUY → debit, SELL → credit.
            if side == "BUY":
                new_balance = balance - total
            else:
                new_balance = balance + total

            # Persist
            from data.database import save_paper_order, update_paper_balance
            user_id = st.session_state["user_id"]
            save_paper_order(user_id, order)
            update_paper_balance(user_id, new_balance)

            # Update session state
            st.session_state[_ORD_KEY].insert(0, order)  # newest first
            st.session_state[_BAL_KEY] = new_balance

            # Human-readable action label for toast
            if side == "BUY":
                action = "COVER SHORT" if net_qty < 0 else "BUY"
            else:
                action = "SELL SHORT" if net_qty <= 0 else "SELL"

            logger.info(
                f"m17_paper | {side} ({action}) | {symbol} qty={qty} price={ltp:.2f} "
                f"total={total:.2f} balance={new_balance:.2f}"
            )
            st.toast(
                f"{action} {qty} x {symbol} @ {format_inr(ltp)}",
                icon="✅",
            )
            st.rerun()

    # Show order preview with context hint
    if ltp > 0:
        positions_preview = _compute_positions(st.session_state[_ORD_KEY])
        net_qty_preview = positions_preview.get(symbol, {}).get("qty", 0)
        if side == "BUY":
            hint = "COVER SHORT" if net_qty_preview < 0 else "BUY LONG"
        else:
            hint = "SELL SHORT" if net_qty_preview <= 0 else "SELL LONG"
        preview_total = ltp * qty
        st.markdown(
            f'<div style="color:{COLORS["muted"]};font-size:11px;font-family:monospace;'
            f'margin-top:4px">'
            f'{hint}: {qty} x {symbol} @ {format_inr(ltp)} = {format_inr(preview_total)}'
            f'  |  Balance: {format_inr(st.session_state[_BAL_KEY])}'
            f'</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────
# Summary Metrics
# ─────────────────────────────────────────────────────────────────────
def _render_summary(orders=None, balance=None):
    """Render 6 summary metric cards."""
    if balance is None:
        balance = st.session_state[_BAL_KEY]
    if orders is None:
        orders = st.session_state[_ORD_KEY]

    positions = _compute_positions(orders)
    realized_pnl, trades = _compute_realized_pnl(orders)

    # Compute unrealized P&L from live prices
    unrealized_pnl = 0.0
    current_value = 0.0
    if positions:
        from data.nse_live import get_stock_quote
        for sym, pos in positions.items():
            net_qty = pos["qty"]
            avg_cost = pos["avg_cost"]
            quote = get_stock_quote(sym)
            ltp = quote["lastPrice"] if quote else avg_cost
            if net_qty > 0:
                # Long: current value = ltp * qty
                cv = net_qty * ltp
                current_value += cv
                unrealized_pnl += (ltp - avg_cost) * net_qty
            else:
                # Short: notional value = collateral (avg_cost * abs_qty)
                abs_qty = abs(net_qty)
                cv = avg_cost * abs_qty  # collateral stays as "value"
                current_value += cv
                unrealized_pnl += (avg_cost - ltp) * abs_qty

    total_pnl = realized_pnl + unrealized_pnl
    portfolio_value = balance + current_value
    total_return_pct = (portfolio_value / PAPER_DEFAULT_BALANCE - 1) * 100

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
def _render_positions(orders=None):
    """Render open positions table with live P&L."""
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;font-weight:bold;'
        f'margin-bottom:4px">OPEN POSITIONS</p>',
        unsafe_allow_html=True,
    )

    if orders is None:
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

    columns = ["SYMBOL", "DIR", "QTY", "AVG PRICE", "LTP", "VALUE", "P&L (₹)", "P&L (%)"]
    header_cells = ""
    for c in columns:
        align = "left" if c in ("SYMBOL", "DIR") else "right"
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
        net_qty = pos["qty"]
        avg_cost = pos["avg_cost"]
        quote = get_stock_quote(sym)
        ltp = quote["lastPrice"] if quote else avg_cost

        if net_qty > 0:
            direction = "LONG"
            dir_color = COLORS["green"]
            display_qty = net_qty
            value = display_qty * ltp
            pnl = (ltp - avg_cost) * display_qty
        else:
            direction = "SHORT"
            dir_color = COLORS["red"]
            display_qty = abs(net_qty)
            value = display_qty * ltp
            pnl = (avg_cost - ltp) * display_qty  # profit when price falls

        pnl_pct = (pnl / (avg_cost * display_qty) * 100) if (avg_cost and display_qty) else 0
        pnl_color = color_change(pnl)

        rows += (
            f'<tr>'
            f'<td style="{cell};text-align:left;color:{COLORS["blue"]};font-weight:bold">{sym}</td>'
            f'<td style="{cell};text-align:left;color:{dir_color};font-weight:bold">{direction}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{display_qty:,}</td>'
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
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:4px;'
        f'margin-top:12px">CLOSED TRADES</p>',
        unsafe_allow_html=True,
    )
    columns = ["#", "SYMBOL", "TYPE", "QTY", "OPEN PRICE", "CLOSE PRICE", "P&L", "DATE"]
    header_cells = ""
    for c in columns:
        align = "left" if c in ("SYMBOL", "TYPE", "DATE") else "right"
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
        trade_type = t.get("type", "LONG")
        type_color = COLORS["green"] if trade_type == "LONG" else COLORS["red"]
        rows += (
            f'<tr>'
            f'<td style="{cell};text-align:center;color:{COLORS["muted"]}">{i + 1}</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["blue"]};font-weight:bold">'
            f'{t["symbol"]}</td>'
            f'<td style="{cell};text-align:left;color:{type_color};font-weight:bold">'
            f'{trade_type}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{t["qty"]:,}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">'
            f'{format_inr(t["open_price"])}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">'
            f'{format_inr(t["close_price"])}</td>'
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
            user_id = st.session_state["user_id"]
            clear_paper_trading(user_id)
            st.session_state[_BAL_KEY] = PAPER_DEFAULT_BALANCE
            st.session_state[_ORD_KEY] = []
            logger.info("m17_paper | RESET")
            st.toast("Paper portfolio reset.", icon="🔄")
            st.rerun()
