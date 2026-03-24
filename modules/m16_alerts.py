"""Module 16: Price & Volume Alerts (Bloomberg: ALRT)."""

from datetime import datetime

import pytz
import streamlit as st

from config import COLORS, NIFTY_50_SYMBOLS
from utils.formatting import format_inr, color_change
from utils.logger import logger

# ── Session state key ──
_STATE_KEY = "price_alerts"

# ── Alert condition definitions ──
_CONDITIONS = {
    "price_above": "Price Above",
    "price_below": "Price Below",
    "pct_change_above": "% Change Above",
    "pct_change_below": "% Change Below",
}


def render():
    """Render the Price & Volume Alerts module."""
    st.markdown("### PRICE & VOLUME ALERTS")

    # Initialize session state (load from DB)
    if _STATE_KEY not in st.session_state:
        from data.database import load_alerts
        st.session_state[_STATE_KEY] = load_alerts()

    # ── Add Alert section ──
    _render_add_alert()

    st.divider()

    # ── Check alerts on page load ──
    triggered_count = _check_all_alerts()
    if triggered_count > 0:
        st.toast(
            f"{triggered_count} alert{'s' if triggered_count > 1 else ''} triggered!",
            icon="🔔",
        )

    # ── Summary metrics ──
    _render_summary()

    st.divider()

    # ── Active Alerts table ──
    _render_active_alerts()

    st.divider()

    # ── Triggered Alerts section ──
    _render_triggered_alerts()

    st.divider()

    # ── Control buttons ──
    _render_controls()


# ─────────────────────────────────────────────────────────────────────
# Add Alert
# ─────────────────────────────────────────────────────────────────────
def _render_add_alert():
    """Render the add-alert form."""
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;font-weight:bold;'
        f'margin-bottom:4px">SET NEW ALERT</p>',
        unsafe_allow_html=True,
    )

    c_sym, c_ltp, c_cond, c_val, c_btn = st.columns([2, 1, 2, 1, 1])

    with c_sym:
        symbol = st.selectbox(
            "SYMBOL",
            options=NIFTY_50_SYMBOLS,
            index=0,
            key="m16_symbol",
            label_visibility="collapsed",
        )

    # Show current LTP for the selected symbol
    with c_ltp:
        from data.nse_live import get_stock_quote
        _quote = get_stock_quote(symbol)
        if _quote:
            _ltp = _quote["lastPrice"]
            _pchg = _quote["pChange"]
            _chg_color = COLORS["green"] if _pchg >= 0 else COLORS["red"]
            st.markdown(
                f'<div style="text-align:center;padding:4px 0">'
                f'<div style="color:{COLORS["muted"]};font-size:9px">LTP</div>'
                f'<div style="color:{COLORS["text"]};font-size:14px;font-weight:bold">'
                f'{format_inr(_ltp)}</div>'
                f'<div style="color:{_chg_color};font-size:10px">{_pchg:+.2f}%</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="text-align:center;padding:4px 0;color:{COLORS["muted"]};'
                f'font-size:11px">LTP: —</div>',
                unsafe_allow_html=True,
            )

    with c_cond:
        condition = st.selectbox(
            "CONDITION",
            options=list(_CONDITIONS.keys()),
            format_func=lambda k: _CONDITIONS[k],
            key="m16_condition",
            label_visibility="collapsed",
        )

    with c_val:
        # Default value based on LTP if available
        default_price = round(_quote["lastPrice"], 2) if _quote else 100.0
        if condition in ("pct_change_above", "pct_change_below"):
            value = st.number_input(
                "VALUE (%)",
                min_value=0.01,
                value=2.0,
                step=0.5,
                format="%.2f",
                key="m16_value",
                label_visibility="collapsed",
            )
        else:
            value = st.number_input(
                "VALUE (₹)",
                min_value=0.01,
                value=default_price,
                step=1.0,
                format="%.2f",
                key="m16_value",
                label_visibility="collapsed",
            )

    with c_btn:
        if st.button("ADD ALERT", use_container_width=True, key="m16_add_btn"):
            ist = pytz.timezone("Asia/Kolkata")
            new_alert = {
                "symbol": symbol,
                "condition": condition,
                "value": float(value),
                "created_at": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S"),
                "triggered": False,
                "triggered_at": None,
            }
            from data.database import save_alert
            new_alert["_db_id"] = save_alert(new_alert)
            st.session_state[_STATE_KEY].append(new_alert)
            logger.info(
                f"m16_alerts | ADD | {symbol} {condition} {value}"
            )
            st.rerun()


# ─────────────────────────────────────────────────────────────────────
# Summary Metrics
# ─────────────────────────────────────────────────────────────────────
def _render_summary():
    """Render summary metrics for alerts."""
    alerts = st.session_state[_STATE_KEY]
    total = len(alerts)
    active = sum(1 for a in alerts if not a["triggered"])
    triggered = sum(1 for a in alerts if a["triggered"])

    c1, c2, c3 = st.columns(3)
    _metric_card(c1, "TOTAL ALERTS", str(total), COLORS["text"])
    _metric_card(c2, "ACTIVE", str(active), COLORS["green"])
    _metric_card(c3, "TRIGGERED", str(triggered), COLORS["red"])


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
# Check Alerts
# ─────────────────────────────────────────────────────────────────────
def _check_all_alerts():
    """Check all active alerts against current prices. Returns count of newly triggered."""
    from data.nse_live import get_stock_quote

    alerts = st.session_state[_STATE_KEY]
    active_alerts = [a for a in alerts if not a["triggered"]]

    if not active_alerts:
        return 0

    # Get unique symbols to fetch
    symbols = list({a["symbol"] for a in active_alerts})
    quotes = {}
    for sym in symbols:
        quote = get_stock_quote(sym)
        if quote:
            quotes[sym] = quote

    # Evaluate each alert
    ist = pytz.timezone("Asia/Kolkata")
    triggered_count = 0

    for alert in active_alerts:
        sym = alert["symbol"]
        quote = quotes.get(sym)
        if not quote:
            continue

        ltp = quote["lastPrice"]
        pchange = quote["pChange"]
        condition = alert["condition"]
        target = alert["value"]
        fired = False

        if condition == "price_above" and ltp >= target:
            fired = True
        elif condition == "price_below" and ltp <= target:
            fired = True
        elif condition == "pct_change_above" and pchange >= target:
            fired = True
        elif condition == "pct_change_below" and pchange <= -target:
            fired = True

        if fired:
            alert["triggered"] = True
            alert["triggered_at"] = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")
            alert["trigger_price"] = ltp
            alert["trigger_pchange"] = pchange
            if "_db_id" in alert:
                from data.database import update_alert_triggered
                update_alert_triggered(alert["_db_id"], alert["triggered_at"], ltp, pchange)
            triggered_count += 1
            logger.info(
                f"m16_alerts | TRIGGERED | {sym} {condition} target={target} "
                f"ltp={ltp} pChange={pchange}"
            )

    return triggered_count


# ─────────────────────────────────────────────────────────────────────
# Active Alerts Table
# ─────────────────────────────────────────────────────────────────────
def _render_active_alerts():
    """Render table of active (not yet triggered) alerts with current prices."""
    from data.nse_live import get_stock_quote

    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;font-weight:bold;'
        f'margin-bottom:4px">ACTIVE ALERTS</p>',
        unsafe_allow_html=True,
    )

    alerts = st.session_state[_STATE_KEY]
    active = [a for a in alerts if not a["triggered"]]

    if not active:
        st.markdown(
            f'<div style="text-align:center;padding:20px;color:{COLORS["muted"]};'
            f'font-family:monospace;font-size:12px">'
            f'No active alerts. Set alerts using the form above.</div>',
            unsafe_allow_html=True,
        )
        return

    # Fetch current prices for active alert symbols
    symbols = list({a["symbol"] for a in active})
    quotes = {}
    for sym in symbols:
        quote = get_stock_quote(sym)
        if quote:
            quotes[sym] = quote

    # Table header
    columns = ["#", "SYMBOL", "CONDITION", "TARGET", "CUR PRICE", "CUR CHG%", "DISTANCE", "CREATED"]
    header_cells = ""
    for c in columns:
        align = "left" if c in ("SYMBOL", "CONDITION", "CREATED") else "right"
        if c == "#":
            align = "center"
        header_cells += (
            f'<th style="color:{COLORS["amber"]};padding:4px 8px;text-align:{align};'
            f'border-bottom:1px solid {COLORS["border"]};font-size:10px;'
            f'white-space:nowrap">{c}</th>'
        )

    # Table rows
    rows = ""
    cell = (
        f"padding:3px 8px;font-size:11px;font-family:monospace;"
        f"border-bottom:1px solid #1A1A1A;white-space:nowrap"
    )

    for i, alert in enumerate(active):
        sym = alert["symbol"]
        condition = alert["condition"]
        target = alert["value"]
        created = alert["created_at"]
        quote = quotes.get(sym)

        if quote:
            ltp = quote["lastPrice"]
            pchange = quote["pChange"]
            cur_price_str = format_inr(ltp)
            chg_color = color_change(pchange)
            cur_chg_str = f'{pchange:+.2f}%'

            # Calculate distance to trigger
            if condition == "price_above":
                distance = target - ltp
                distance_str = f'{format_inr(abs(distance))} {"above" if distance <= 0 else "away"}'
                dist_color = COLORS["green"] if distance <= 0 else COLORS["text"]
            elif condition == "price_below":
                distance = ltp - target
                distance_str = f'{format_inr(abs(distance))} {"below" if distance <= 0 else "away"}'
                dist_color = COLORS["green"] if distance <= 0 else COLORS["text"]
            elif condition == "pct_change_above":
                distance = target - pchange
                distance_str = f'{abs(distance):.2f}% {"past" if distance <= 0 else "away"}'
                dist_color = COLORS["green"] if distance <= 0 else COLORS["text"]
            elif condition == "pct_change_below":
                distance = -target - pchange
                distance_str = f'{abs(distance):.2f}% {"past" if distance >= 0 else "away"}'
                dist_color = COLORS["green"] if distance >= 0 else COLORS["text"]
            else:
                distance_str = "—"
                dist_color = COLORS["muted"]
        else:
            cur_price_str = "—"
            cur_chg_str = "—"
            chg_color = COLORS["muted"]
            distance_str = "—"
            dist_color = COLORS["muted"]

        # Format target value
        if condition in ("pct_change_above", "pct_change_below"):
            target_str = f'{target:.2f}%'
        else:
            target_str = format_inr(target)

        cond_label = _CONDITIONS.get(condition, condition)

        rows += (
            f'<tr>'
            f'<td style="{cell};text-align:center;color:{COLORS["muted"]}">{i + 1}</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["blue"]};font-weight:bold">{sym}</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["text"]}">{cond_label}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["amber"]}">{target_str}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["text"]}">{cur_price_str}</td>'
            f'<td style="{cell};text-align:right;color:{chg_color}">{cur_chg_str}</td>'
            f'<td style="{cell};text-align:right;color:{dist_color}">{distance_str}</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["muted"]}">{created}</td>'
            f'</tr>'
        )

    html = (
        f'<div style="overflow-x:auto">'
        f'<table style="width:100%;border-collapse:collapse;font-family:monospace">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    st.caption(f"{len(active)} active alert{'s' if len(active) != 1 else ''}")

    # ── Remove individual alert ──
    if active:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:12px;margin-bottom:2px;'
            f'margin-top:8px">REMOVE ALERT</p>',
            unsafe_allow_html=True,
        )
        labels = [
            f'{a["symbol"]}  |  {_CONDITIONS[a["condition"]]}  |  '
            f'{"₹" if a["condition"] not in ("pct_change_above", "pct_change_below") else ""}'
            f'{a["value"]:.2f}{"%" if a["condition"] in ("pct_change_above", "pct_change_below") else ""}'
            for a in active
        ]
        rm_c1, rm_c2 = st.columns([4, 1])
        with rm_c1:
            rm_idx = st.selectbox(
                "SELECT ALERT",
                range(len(labels)),
                format_func=lambda idx: labels[idx],
                key="m16_rm_select",
                label_visibility="collapsed",
            )
        with rm_c2:
            if st.button("REMOVE", use_container_width=True, key="m16_rm_btn"):
                # Find the actual index in the full alerts list
                alert_to_remove = active[rm_idx]
                if "_db_id" in alert_to_remove:
                    from data.database import remove_alert
                    remove_alert(alert_to_remove["_db_id"])
                st.session_state[_STATE_KEY].remove(alert_to_remove)
                logger.info(
                    f"m16_alerts | REMOVE | {alert_to_remove['symbol']} "
                    f"{alert_to_remove['condition']} {alert_to_remove['value']}"
                )
                st.rerun()


# ─────────────────────────────────────────────────────────────────────
# Triggered Alerts Table
# ─────────────────────────────────────────────────────────────────────
def _render_triggered_alerts():
    """Render table of triggered alerts with timestamps."""
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:12px;font-weight:bold;'
        f'margin-bottom:4px">TRIGGERED ALERTS</p>',
        unsafe_allow_html=True,
    )

    alerts = st.session_state[_STATE_KEY]
    triggered = [a for a in alerts if a["triggered"]]

    if not triggered:
        st.markdown(
            f'<div style="text-align:center;padding:20px;color:{COLORS["muted"]};'
            f'font-family:monospace;font-size:12px">'
            f'No triggered alerts.</div>',
            unsafe_allow_html=True,
        )
        return

    # Show most recent first
    triggered = list(reversed(triggered))

    # Table header
    columns = ["#", "SYMBOL", "CONDITION", "TARGET", "TRIGGER PRICE", "TRIGGER CHG%", "CREATED", "TRIGGERED AT"]
    header_cells = ""
    for c in columns:
        align = "left" if c in ("SYMBOL", "CONDITION", "CREATED", "TRIGGERED AT") else "right"
        if c == "#":
            align = "center"
        header_cells += (
            f'<th style="color:{COLORS["amber"]};padding:4px 8px;text-align:{align};'
            f'border-bottom:1px solid {COLORS["border"]};font-size:10px;'
            f'white-space:nowrap">{c}</th>'
        )

    # Table rows
    rows = ""
    cell = (
        f"padding:3px 8px;font-size:11px;font-family:monospace;"
        f"border-bottom:1px solid #1A1A1A;white-space:nowrap"
    )

    for i, alert in enumerate(triggered):
        sym = alert["symbol"]
        condition = alert["condition"]
        target = alert["value"]
        created = alert["created_at"]
        triggered_at = alert.get("triggered_at", "—")
        trigger_price = alert.get("trigger_price", 0)
        trigger_pchange = alert.get("trigger_pchange", 0)

        # Format target value
        if condition in ("pct_change_above", "pct_change_below"):
            target_str = f'{target:.2f}%'
        else:
            target_str = format_inr(target)

        cond_label = _CONDITIONS.get(condition, condition)
        price_color = color_change(trigger_pchange)

        rows += (
            f'<tr>'
            f'<td style="{cell};text-align:center;color:{COLORS["muted"]}">{i + 1}</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["blue"]};font-weight:bold">{sym}</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["text"]}">{cond_label}</td>'
            f'<td style="{cell};text-align:right;color:{COLORS["amber"]}">{target_str}</td>'
            f'<td style="{cell};text-align:right;color:{price_color}">'
            f'{format_inr(trigger_price)}</td>'
            f'<td style="{cell};text-align:right;color:{price_color}">'
            f'{trigger_pchange:+.2f}%</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["muted"]}">{created}</td>'
            f'<td style="{cell};text-align:left;color:{COLORS["green"]}">{triggered_at}</td>'
            f'</tr>'
        )

    html = (
        f'<div style="overflow-x:auto">'
        f'<table style="width:100%;border-collapse:collapse;font-family:monospace">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    st.caption(f"{len(triggered)} triggered alert{'s' if len(triggered) != 1 else ''}")


# ─────────────────────────────────────────────────────────────────────
# Control Buttons
# ─────────────────────────────────────────────────────────────────────
def _render_controls():
    """Render check and clear buttons."""
    c1, c2, c3 = st.columns([1, 1, 4])

    with c1:
        if st.button("CHECK ALERTS", use_container_width=True, key="m16_check_btn"):
            count = _check_all_alerts()
            if count > 0:
                st.toast(
                    f"{count} alert{'s' if count > 1 else ''} triggered!",
                    icon="🔔",
                )
            else:
                st.toast("No alerts triggered.", icon="✅")
            st.rerun()

    with c2:
        if st.button("CLEAR ALL", use_container_width=True, key="m16_clear_btn"):
            from data.database import clear_all_alerts
            clear_all_alerts()
            st.session_state[_STATE_KEY] = []
            logger.info("m16_alerts | CLEAR ALL")
            st.rerun()
