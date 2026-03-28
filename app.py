"""Indian Markets Bloomberg Terminal — Main Application."""

import importlib

import streamlit as st
from datetime import datetime
import pytz

from theme import apply_theme
from utils.logger import new_request_id, logger
from utils.formatting import escape_html

# ── Page config (must be first Streamlit command) ──
st.set_page_config(
    page_title="Indian Bloomberg Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Apply Bloomberg dark theme ──
apply_theme()

# ── Initialize database (once per session) ──
if "db_initialized" not in st.session_state:
    from data.database import init_db
    init_db()
    st.session_state.db_initialized = True

# ── Authentication gate ──
from auth.auth import require_auth, logout

user = require_auth()  # renders login page and st.stop() if not authenticated
user_id = user["user_id"]
st.session_state["user_id"] = user_id

# ── Request tracing ──
rid = new_request_id()
logger.info(f"PAGE RENDER START | request_id={rid} | user={user['username']}")

# ── Header ──
ist = pytz.timezone("Asia/Kolkata")
now = datetime.now(ist)
market_open = now.hour * 60 + now.minute >= 9 * 60 + 15
market_close = now.hour * 60 + now.minute >= 15 * 60 + 30
is_weekday = now.weekday() < 5

if is_weekday and market_open and not market_close:
    status_class = "status-open"
    status_text = "● MARKET OPEN"
else:
    status_class = "status-closed"
    status_text = "● MARKET CLOSED"

col_header, col_user = st.columns([9, 1])
with col_header:
    st.markdown(
        f'<div class="terminal-header">'
        f'<span class="title">INDIAN BLOOMBERG TERMINAL</span>'
        f'<span class="info">'
        f'<span class="{status_class}">{status_text}</span>'
        f'<span class="datetime">{now.strftime("%d %b %Y  %H:%M:%S IST")}</span>'
        f'</span></div>',
        unsafe_allow_html=True,
    )
with col_user:
    st.markdown(
        f'<div style="text-align:right;padding:4px 0;font-family:monospace;font-size:11px">'
        f'<span style="color:#888888">USER:</span> '
        f'<span style="color:#FF9900">{escape_html(user["username"].upper())}</span></div>',
        unsafe_allow_html=True,
    )
    if st.button("LOGOUT", key="logout_btn", use_container_width=True):
        logout()

# ── Tab navigation (lazy rendering — only active tab executes) ──
TAB_CONFIG = [
    ("M01 OVERVIEW",   "modules.m01_market_overview"),
    ("M02 WATCHLIST",  "modules.m02_watchlist"),
    ("M03 CHARTS",     "modules.m03_price_charts"),
    ("M04 COMPANY",    "modules.m04_company_description"),
    ("M05 FINANCIALS", "modules.m05_financials"),
    ("M06 SCREENER",   "modules.m06_stock_screener"),
    ("M07 OPTIONS",    "modules.m07_option_chain"),
    ("M08 HEATMAP",    "modules.m08_sector_heatmap"),
    ("M09 COMPARISON", "modules.m09_index_comparison"),
    ("M10 PORTFOLIO",  "modules.m10_portfolio_tracker"),
    ("M11 BACKTEST",   "modules.m11_backtesting"),
    ("M12 OPTIMIZER",  "modules.m12_portfolio_optimizer"),
    ("M13 ECONOMIC",   "modules.m13_economic_dashboard"),
    ("M14 FII/DII",    "modules.m14_fii_dii_tracker"),
    ("M15 NEWS",       "modules.m15_news_sentiment"),
    ("M16 ALERTS",     "modules.m16_alerts"),
    ("M17 PAPER",      "modules.m17_paper_trading"),
]

TAB_LABELS = [label for label, _ in TAB_CONFIG]
TAB_MODULES = {label: mod for label, mod in TAB_CONFIG}

selected_tab = st.radio(
    "Module",
    TAB_LABELS,
    horizontal=True,
    label_visibility="collapsed",
    key="active_tab",
)

# Detect tab switch
_prev_tab_key = "_prev_active_tab"
_tab_switched = st.session_state.get(_prev_tab_key) != selected_tab
st.session_state[_prev_tab_key] = selected_tab

# Single container that owns ALL module output.
# On tab switch: immediately replace its entire contents with a loading screen,
# wiping the previous module's widgets before the new one starts rendering.
_module_area = st.empty()

if _tab_switched:
    with _module_area.container():
        st.markdown(
            f'<div style="text-align:center;padding:80px 0;font-family:monospace">'
            f'<div style="color:#FF9900;font-size:13px;letter-spacing:2px">LOADING {selected_tab}...</div>'
            f'<div style="color:#444444;font-size:11px;margin-top:8px">Please wait</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# Only import and render the selected module
try:
    mod = importlib.import_module(TAB_MODULES[selected_tab])
    _module_area.empty()
    with _module_area.container():
        mod.render()
except Exception as e:
    logger.error(f"MODULE CRASH | {selected_tab} | {type(e).__name__}: {e}")
    _module_area.empty()
    with _module_area.container():
        st.error(f"**{selected_tab}** failed to load: {type(e).__name__}: {e}")
        st.info("Try switching to another module or refreshing the page.")
