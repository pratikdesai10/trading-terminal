"""Module 02: Watchlist (Bloomberg: MOST)."""

import streamlit as st

from config import DEFAULT_WATCHLIST, NIFTY_500_SYMBOLS
from utils.formatting import format_inr, format_volume
from utils.logger import logger


def render():
    """Render the Watchlist module."""
    st.markdown("### WATCHLIST")

    # ── Initialize watchlist in session state (load from DB) ──
    if "watchlist" not in st.session_state:
        from data.database import load_watchlist
        db_wl = load_watchlist()
        st.session_state.watchlist = db_wl if db_wl else list(DEFAULT_WATCHLIST)

    # ── Add / Remove controls ──
    col_add, col_remove = st.columns([2, 1])
    with col_add:
        new_symbol = st.selectbox(
            "ADD SYMBOL",
            options=[s for s in NIFTY_500_SYMBOLS if s not in st.session_state.watchlist],
            index=None,
            placeholder="Select symbol to add...",
            key="wl_add_symbol",
        )
        if new_symbol and st.button("ADD", key="wl_add_btn"):
            st.session_state.watchlist.append(new_symbol)
            from data.database import add_watchlist_symbol
            add_watchlist_symbol(new_symbol)
            st.rerun()

    with col_remove:
        rm_symbol = st.selectbox(
            "REMOVE SYMBOL",
            options=st.session_state.watchlist,
            index=None,
            placeholder="Select to remove...",
            key="wl_rm_symbol",
        )
        if rm_symbol and st.button("REMOVE", key="wl_rm_btn"):
            st.session_state.watchlist.remove(rm_symbol)
            from data.database import remove_watchlist_symbol
            remove_watchlist_symbol(rm_symbol)
            st.rerun()

    st.markdown("---")

    # ── Fetch and display watchlist data ──
    if not st.session_state.watchlist:
        st.info("Watchlist is empty. Add symbols above.")
        return

    try:
        _render_watchlist_table(st.session_state.watchlist)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        logger.error(f"m02_watchlist | {type(e).__name__}: {e}")


def _render_watchlist_table(symbols):
    """Fetch quotes and render a dense Bloomberg-style table."""
    from data.nse_live import get_stock_quote

    rows = ""
    for symbol in symbols:
        quote = get_stock_quote(symbol)
        if quote is None:
            rows += (
                f'<tr>'
                f'<td style="padding:4px 8px;color:#3399FF;border-bottom:1px solid #1A1A1A">{symbol}</td>'
                + '<td style="padding:4px 8px;text-align:right;color:#888;border-bottom:1px solid #1A1A1A">—</td>' * 9
                + f'</tr>'
            )
            continue

        ltp = quote["lastPrice"]
        change = quote["change"]
        pchange = quote["pChange"]
        color = "#00CC66" if change > 0 else "#FF3333" if change < 0 else "#E0E0E0"

        def _td(val, align="right", clr="#E0E0E0"):
            return (
                f'<td style="padding:4px 8px;text-align:{align};color:{clr};'
                f'font-family:monospace;border-bottom:1px solid #1A1A1A;font-size:12px;white-space:nowrap">'
                f'{val}</td>'
            )

        rows += (
            f'<tr>'
            f'<td style="padding:4px 8px;color:#3399FF;border-bottom:1px solid #1A1A1A;font-size:12px;font-weight:bold">{symbol}</td>'
            + _td(f'{ltp:,.2f}', clr=color)
            + _td(f'{change:+.2f}', clr=color)
            + _td(f'{pchange:+.2f}%', clr=color)
            + _td(f'{quote["open"]:,.2f}')
            + _td(f'{quote["dayHigh"]:,.2f}')
            + _td(f'{quote["dayLow"]:,.2f}')
            + _td(f'{quote["previousClose"]:,.2f}')
            + _td(format_volume(quote["totalTradedVolume"]))
            + _td(f'{quote["yearHigh"]:,.2f}')
            + _td(f'{quote["yearLow"]:,.2f}')
            + f'</tr>'
        )

    headers = ["SYMBOL", "LTP", "CHG", "CHG%", "OPEN", "HIGH", "LOW", "PREV CL", "VOL", "52W H", "52W L"]
    header_cells = ""
    for i, h in enumerate(headers):
        align = "left" if i == 0 else "right"
        header_cells += (
            f'<th style="padding:6px 8px;text-align:{align};color:#FF9900;'
            f'border-bottom:1px solid #FF9900;font-size:10px;text-transform:uppercase;'
            f'letter-spacing:0.5px;white-space:nowrap">{h}</th>'
        )

    st.markdown(
        f'<div style="overflow-x:auto">'
        f'<table style="width:100%;border-collapse:collapse;border:1px solid #333333">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>',
        unsafe_allow_html=True,
    )

    st.caption(f"{len(symbols)} symbols | Data refreshes every 60s")
