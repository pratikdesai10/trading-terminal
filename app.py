"""Indian Markets Bloomberg Terminal — Main Application."""

import streamlit as st
from datetime import datetime
import pytz

from theme import apply_theme

# ── Page config (must be first Streamlit command) ──
st.set_page_config(
    page_title="Indian Bloomberg Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Apply Bloomberg dark theme ──
apply_theme()

# ── Header ──
ist = pytz.timezone("Asia/Kolkata")
now = datetime.now(ist)
market_open = now.hour * 60 + now.minute >= 9 * 60 + 15
market_close = now.hour * 60 + now.minute >= 15 * 60 + 30
is_weekday = now.weekday() < 5

if is_weekday and market_open and not market_close:
    market_status = '<span style="color:#00CC66">● MARKET OPEN</span>'
else:
    market_status = '<span style="color:#FF3333">● MARKET CLOSED</span>'

st.markdown(
    f'<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid #333333;margin-bottom:10px">'
    f'<span style="color:#FF9900;font-size:16px;font-weight:bold;font-family:monospace;letter-spacing:1px">INDIAN BLOOMBERG TERMINAL</span>'
    f'<span style="font-family:monospace;font-size:12px">'
    f'{market_status}'
    f'<span style="color:#888;margin-left:16px">{now.strftime("%d %b %Y  %H:%M:%S IST")}</span>'
    f'</span></div>',
    unsafe_allow_html=True,
)

# ── Tab navigation ──
tab_overview, tab_watchlist = st.tabs([
    "M01 OVERVIEW",
    "M02 WATCHLIST",
])

with tab_overview:
    from modules.m01_market_overview import render as render_overview
    render_overview()

with tab_watchlist:
    from modules.m02_watchlist import render as render_watchlist
    render_watchlist()
