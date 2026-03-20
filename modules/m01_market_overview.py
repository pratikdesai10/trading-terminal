"""Module 01: Market Overview Dashboard (Bloomberg: WEI / MAIN)."""

import streamlit as st

from config import COLORS
from utils.formatting import format_inr, format_pct, format_number, colored_text
from utils.logger import logger


def render():
    """Render the Market Overview dashboard."""
    st.markdown("### MARKET OVERVIEW")

    try:
        # ── Top bar: Key indices ──
        _render_key_indices()

        st.markdown("---")

        # ── Three-column layout ──
        col_left, col_mid, col_right = st.columns([1, 1, 1])

        with col_left:
            _render_market_breadth()
            st.markdown("")
            _render_india_vix()

        with col_mid:
            _render_sectoral_performance()

        with col_right:
            _render_top_movers()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        logger.error(f"m01_market_overview | {type(e).__name__}: {e}")


def _render_key_indices():
    """Display NIFTY 50, SENSEX, BANK NIFTY, NIFTY IT as metric cards."""
    from data.nse_live import get_index_quote

    indices = ["NIFTY 50", "NIFTY BANK", "NIFTY IT", "NIFTY NEXT 50"]
    cols = st.columns(len(indices))

    for col, idx_name in zip(cols, indices):
        with col:
            quote = get_index_quote(idx_name)
            if quote:
                st.metric(
                    label=idx_name,
                    value=f"{quote['last']:,.2f}",
                    delta=f"{quote['change']:+.2f} ({quote['pChange']:+.2f}%)",
                )
            else:
                st.metric(label=idx_name, value="—", delta="N/A")


def _render_market_breadth():
    """Show Advances / Declines / Unchanged."""
    from data.nse_live import get_market_breadth

    st.markdown("##### MARKET BREADTH")

    breadth = get_market_breadth()
    adv = breadth["advances"]
    dec = breadth["declines"]
    unc = breadth["unchanged"]
    total = adv + dec + unc

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div style="text-align:center">'
            f'<div style="color:#FF9900;font-size:10px;text-transform:uppercase">ADV</div>'
            f'<div style="color:#00CC66;font-size:20px;font-family:monospace">{adv}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div style="text-align:center">'
            f'<div style="color:#FF9900;font-size:10px;text-transform:uppercase">DEC</div>'
            f'<div style="color:#FF3333;font-size:20px;font-family:monospace">{dec}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div style="text-align:center">'
            f'<div style="color:#FF9900;font-size:10px;text-transform:uppercase">UNC</div>'
            f'<div style="color:#E0E0E0;font-size:20px;font-family:monospace">{unc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Breadth bar
    if total > 0:
        adv_pct = adv / total * 100
        dec_pct = dec / total * 100
        st.markdown(
            f'<div style="display:flex;height:8px;border-radius:4px;overflow:hidden;margin-top:8px">'
            f'<div style="width:{adv_pct}%;background:#00CC66"></div>'
            f'<div style="width:{dec_pct}%;background:#FF3333"></div>'
            f'<div style="flex:1;background:#555555"></div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_india_vix():
    """Display India VIX."""
    from data.nse_live import get_index_quote

    st.markdown("##### INDIA VIX")
    quote = get_index_quote("INDIA VIX")
    if quote:
        vix = quote["last"]
        change = quote["pChange"]
        color = "#00CC66" if change <= 0 else "#FF3333"  # Lower VIX = calmer
        st.markdown(
            f'<div style="background:#1A1A1A;padding:12px;border:1px solid #333333;border-radius:4px">'
            f'<span style="font-size:24px;font-family:monospace;color:{color}">{vix:.2f}</span>'
            f'<span style="font-size:13px;margin-left:10px;color:{color}">{change:+.2f}%</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("VIX data unavailable")


def _render_sectoral_performance():
    """Show sectoral indices sorted by % change."""
    from data.nse_live import get_sectoral_indices

    st.markdown("##### SECTORAL INDICES")

    df = get_sectoral_indices()
    if df.empty:
        st.info("Sectoral data unavailable")
        return

    # Build styled HTML table
    rows = ""
    for _, row in df.iterrows():
        pct = row["% Change"]
        color = "#00CC66" if pct > 0 else "#FF3333" if pct < 0 else "#E0E0E0"
        rows += (
            f'<tr>'
            f'<td style="padding:4px 8px;color:#E0E0E0;border-bottom:1px solid #1A1A1A">{row["Index"]}</td>'
            f'<td style="padding:4px 8px;text-align:right;color:#E0E0E0;font-family:monospace;border-bottom:1px solid #1A1A1A">{row["Last"]:,.2f}</td>'
            f'<td style="padding:4px 8px;text-align:right;color:{color};font-family:monospace;border-bottom:1px solid #1A1A1A">{pct:+.2f}%</td>'
            f'</tr>'
        )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;font-size:12px">'
        f'<thead><tr>'
        f'<th style="padding:6px 8px;text-align:left;color:#FF9900;border-bottom:1px solid #FF9900;font-size:10px;text-transform:uppercase">Sector</th>'
        f'<th style="padding:6px 8px;text-align:right;color:#FF9900;border-bottom:1px solid #FF9900;font-size:10px;text-transform:uppercase">Last</th>'
        f'<th style="padding:6px 8px;text-align:right;color:#FF9900;border-bottom:1px solid #FF9900;font-size:10px;text-transform:uppercase">Chg%</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )


def _render_top_movers():
    """Show top 5 gainers and losers."""
    from data.nse_live import get_top_gainers_losers

    gainers, losers = get_top_gainers_losers("NIFTY 50", n=5)

    st.markdown("##### TOP GAINERS")
    if not gainers.empty:
        _movers_table(gainers)
    else:
        st.info("Data unavailable")

    st.markdown("")
    st.markdown("##### TOP LOSERS")
    if not losers.empty:
        _movers_table(losers)
    else:
        st.info("Data unavailable")


def _movers_table(df):
    """Render a compact movers table."""
    rows = ""
    for _, row in df.iterrows():
        pct = row["% Change"]
        color = "#00CC66" if pct > 0 else "#FF3333"
        rows += (
            f'<tr>'
            f'<td style="padding:3px 6px;color:#E0E0E0;border-bottom:1px solid #1A1A1A;font-size:12px">{row["Symbol"]}</td>'
            f'<td style="padding:3px 6px;text-align:right;color:#E0E0E0;font-family:monospace;border-bottom:1px solid #1A1A1A;font-size:12px">{row["LTP"]:,.2f}</td>'
            f'<td style="padding:3px 6px;text-align:right;color:{color};font-family:monospace;border-bottom:1px solid #1A1A1A;font-size:12px">{pct:+.2f}%</td>'
            f'</tr>'
        )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr>'
        f'<th style="padding:4px 6px;text-align:left;color:#FF9900;border-bottom:1px solid #FF9900;font-size:10px;text-transform:uppercase">Symbol</th>'
        f'<th style="padding:4px 6px;text-align:right;color:#FF9900;border-bottom:1px solid #FF9900;font-size:10px;text-transform:uppercase">LTP</th>'
        f'<th style="padding:4px 6px;text-align:right;color:#FF9900;border-bottom:1px solid #FF9900;font-size:10px;text-transform:uppercase">Chg%</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )
