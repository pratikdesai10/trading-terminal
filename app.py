"""Indian Markets Bloomberg Terminal — Main Application."""

import streamlit as st
from datetime import datetime
import pytz

from theme import apply_theme
from utils.logger import new_request_id, logger

# ── Page config (must be first Streamlit command) ──
st.set_page_config(
    page_title="Indian Bloomberg Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Apply Bloomberg dark theme ──
apply_theme()

# ── Request tracing ──
rid = new_request_id()
logger.info(f"PAGE RENDER START | request_id={rid}")

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
(tab_overview, tab_watchlist, tab_charts, tab_company, tab_financials,
 tab_screener, tab_options, tab_heatmap, tab_comparison, tab_portfolio,
 tab_backtest, tab_optimizer, tab_economic, tab_fii, tab_news, tab_alerts) = st.tabs([
    "M01 OVERVIEW",
    "M02 WATCHLIST",
    "M03 CHARTS",
    "M04 COMPANY",
    "M05 FINANCIALS",
    "M06 SCREENER",
    "M07 OPTIONS",
    "M08 HEATMAP",
    "M09 COMPARISON",
    "M10 PORTFOLIO",
    "M11 BACKTEST",
    "M12 OPTIMIZER",
    "M13 ECONOMIC",
    "M14 FII/DII",
    "M15 NEWS",
    "M16 ALERTS",
])

with tab_overview:
    from modules.m01_market_overview import render as render_overview
    render_overview()

with tab_watchlist:
    from modules.m02_watchlist import render as render_watchlist
    render_watchlist()

with tab_charts:
    from modules.m03_price_charts import render as render_charts
    render_charts()

with tab_company:
    from modules.m04_company_description import render as render_company
    render_company()

with tab_financials:
    from modules.m05_financials import render as render_financials
    render_financials()

with tab_screener:
    from modules.m06_stock_screener import render as render_screener
    render_screener()

with tab_options:
    from modules.m07_option_chain import render as render_options
    render_options()

with tab_heatmap:
    from modules.m08_sector_heatmap import render as render_heatmap
    render_heatmap()

with tab_comparison:
    from modules.m09_index_comparison import render as render_comparison
    render_comparison()

with tab_portfolio:
    from modules.m10_portfolio_tracker import render as render_portfolio
    render_portfolio()

with tab_backtest:
    from modules.m11_backtesting import render as render_backtest
    render_backtest()

with tab_optimizer:
    from modules.m12_portfolio_optimizer import render as render_optimizer
    render_optimizer()

with tab_economic:
    from modules.m13_economic_dashboard import render as render_economic
    render_economic()

with tab_fii:
    from modules.m14_fii_dii_tracker import render as render_fii
    render_fii()

with tab_news:
    from modules.m15_news_sentiment import render as render_news
    render_news()

with tab_alerts:
    from modules.m16_alerts import render as render_alerts
    render_alerts()
