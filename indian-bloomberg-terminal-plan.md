# Indian Markets Bloomberg Terminal — Build Plan

## Project Overview

Build a Bloomberg-style terminal for Indian markets (NSE/BSE) using Python. This is a Streamlit-based web application with multiple tabbed modules, each replicating a core Bloomberg function using free, open-source Python libraries. The UI should mimic Bloomberg's signature dark terminal aesthetic (black background, green/amber/white text, dense data layout).

---

## 1. Tech Stack & Architecture

### Core Framework

| Layer | Technology | Pinned Version | Cost | Purpose |
|-------|-----------|---------------|------|---------|
| **UI Framework** | Streamlit | `1.55.0` | FREE (Apache 2.0) | Main app shell, tabs, layout, widgets. Requires Python >=3.10 |
| **Charting** | Plotly | `6.0.1` | FREE (MIT) | Interactive candlestick, line, bar charts |
| **Data Processing** | pandas | `2.2.3` | FREE (BSD) | DataFrames, calculations, transformations |
| **Data Processing** | numpy | `2.2.3` | FREE (BSD) | Numerical computing |
| **Styling** | Custom CSS injected via `st.markdown` | — | — | Bloomberg dark theme (black bg, monospace fonts, green/amber accents) |

**Recommended Python version: 3.12.x** (compatible with all libraries; Streamlit supports 3.10–3.14)

### Data Sources — Indian Market Specific (All FREE, no API key)

| Library | Pinned Version | Cost | License | What It Provides | Reliability |
|---------|---------------|------|---------|-----------------|-------------|
| **jugaad-data** | `0.31.1` | FREE | Public Domain (YOLO) | NSE live quotes, historical stock/index data, bhavcopy, F&O data, RBI economic data. Uses new NSE website. **PRIMARY SOURCE.** | Scrapes NSE. Can break if NSE changes site. Use built-in caching. |
| **nsetools** | `2.0.1` | FREE | MIT | Real-time NSE quotes, index quotes, futures quotes, stock lists by index. Lightweight. | Scrapes NSE. Actively maintained (Mar 2025 release). |
| **nsepython** | `2.97` | FREE | GPL-like | Option chain, Greeks, OI analysis. Migrated from NsepY + NSETools. **Best for F&O.** | Actively maintained. Works on AWS/Colab/servers. |
| **yfinance** | `0.2.54` | FREE | Apache 2.0 | `.NS` for NSE, `.BO` for BSE. OHLCV, financials, analyst recs. **Best for fundamentals.** | **FRAGILE** — unofficial Yahoo scraper. Gets 429 rate-limited under heavy use. Use for batch pulls, NOT live polling. Indian fundamental data may have gaps. |
| **pandas-datareader** | `0.10.0` | FREE | BSD | FRED economic data (global macro). True public API from US Fed. | Very reliable — official FRED API. |

### Analytics & Modeling (All FREE & Open Source)

| Library | Pinned Version | Cost | License | Purpose |
|---------|---------------|------|---------|---------|
| **ta** | `0.11.0` | FREE | MIT | 40+ technical indicators (RSI, MACD, Bollinger, ADX, etc.) |
| **vectorbt** | `0.26.2` | FREE (open source) | Apache 2.0 + Commons Clause | Vectorized backtesting. PRO version ($20/mo) exists but is NOT needed — open source is fully functional. Cannot resell as a product (Commons Clause). |
| **Backtrader** | `1.9.78.123` | FREE | GPL v3 | Event-driven backtesting. Note: last PyPI release was 2019, but library is stable and widely used. |
| **PyPortfolioOpt** | `1.5.6` | FREE | MIT | Mean-variance optimization, risk parity, max Sharpe, Black-Litterman, HRP. |
| **quantstats** | `0.0.64` | FREE | Apache 2.0 | Tearsheets, performance analytics, drawdown analysis, monthly returns heatmap. |
| **scipy** | `1.14.1` | FREE | BSD | Statistical functions, optimization, curve fitting. |

### Optional / Advanced

| Library | Pinned Version | Cost | License | Purpose |
|---------|---------------|------|---------|---------|
| **OpenBB** | `4.x` | FREE core / PAID workspace | AGPL v3 | 100+ data connectors. Optional — not required for this project. |
| **mplfinance** | `0.12.10b0` | FREE | BSD | Matplotlib-based financial charts (alternative to Plotly). |
| **feedparser** | `6.0.11` | FREE | BSD-2 | RSS news feeds from Moneycontrol, ET Markets, etc. |
| **beautifulsoup4** | `4.12.3` | FREE | MIT | Web scraping for data not available via APIs. |
| **APScheduler** | `3.10.4` | FREE | MIT | Scheduled data refresh, alerts. |

---

## 2. Project Structure

```
indian-terminal/
├── app.py                          # Main Streamlit entry point, tab router
├── requirements.txt                # All pip dependencies
├── config.py                       # Constants, API keys, color theme, watchlist defaults
├── theme.py                        # Bloomberg dark CSS, fonts, color variables
│
├── data/                           # Data fetching layer (each file = one data source)
│   ├── __init__.py
│   ├── nse_live.py                 # jugaad-data & nsetools wrappers for live quotes
│   ├── nse_historical.py           # Historical OHLCV, index data
│   ├── nse_fno.py                  # F&O data, option chains, OI
│   ├── fundamentals.py             # yfinance financials, ratios, earnings
│   ├── economic.py                 # RBI data via jugaad-data, FRED via pandas-datareader
│   ├── news.py                     # RSS feeds, news aggregation
│   └── cache.py                    # Simple TTL cache to avoid rate-limiting
│
├── modules/                        # Each Bloomberg function = one module
│   ├── __init__.py
│   ├── m01_market_overview.py      # WEI / MAIN — Market overview dashboard
│   ├── m02_watchlist.py            # MOST — Custom watchlist with live prices
│   ├── m03_price_charts.py         # GP — Interactive candlestick + technicals
│   ├── m04_company_description.py  # DES — Company snapshot & overview
│   ├── m05_financials.py           # FA — Income, balance sheet, cash flow, ratios
│   ├── m06_screener.py             # EQS — Multi-criteria stock screener
│   ├── m07_option_chain.py         # OMON — Option chain, OI analysis, PCR
│   ├── m08_sector_heatmap.py       # IMAP — Sectoral heatmap (Nifty sectors)
│   ├── m09_index_comparison.py     # HS — Compare indices / stocks performance
│   ├── m10_portfolio.py            # PORT — Portfolio tracker, allocation, P&L
│   ├── m11_backtesting.py          # BTST — Strategy backtesting engine
│   ├── m12_portfolio_optimizer.py  # PORT analytics — Mean-variance, risk parity, efficient frontier
│   ├── m13_economic_dashboard.py   # ECST / ECO — Macro indicators, RBI rates, economic calendar
│   ├── m14_fii_dii_tracker.py      # Custom — FII/DII daily flows (India-specific)
│   ├── m15_news_sentiment.py       # TOP / NEWS — Aggregated news with sentiment
│   └── m16_alerts.py               # ALRT — Price / volume / OI alerts
│
├── analytics/                      # Reusable calculation engines
│   ├── __init__.py
│   ├── technicals.py               # Wrapper around `ta` library
│   ├── fundamentals_calc.py        # Ratio calculations, DCF, valuation
│   ├── risk_metrics.py             # VaR, Sharpe, Sortino, max drawdown, beta
│   └── screener_engine.py          # Filtering/ranking engine for EQS
│
└── utils/
    ├── __init__.py
    ├── formatting.py               # Number formatting (₹, Cr, L), color coding
    └── constants.py                # Nifty 50 symbols, sector mappings, index lists
```

---

## 3. Module Specifications (Bloomberg Function → Python Implementation)

### MODULE 01: Market Overview Dashboard (Bloomberg: WEI / MAIN)

**What Bloomberg does:** Shows world equity indices, major movers, market breadth, sector performance at a glance.

**Our implementation:**
- Top bar: NIFTY 50, SENSEX, BANK NIFTY, NIFTY IT — live prices with change % (color coded green/red)
- Market breadth: Advances vs Declines vs Unchanged across NSE
- Sectoral indices: Table with all Nifty sectoral indices, sorted by % change
- Top gainers / Top losers: Top 5 from Nifty 500
- India VIX display
- FII/DII net flow for today (if available)

**Data source:** `nsetools` → `get_all_index_quote()`, `jugaad-data` → `NSELive().live_index()`

**UI layout:** Dense 3-column grid. Numbers in monospace. Green for positive, red for negative, amber for headers.

---

### MODULE 02: Watchlist (Bloomberg: MOST)

**What Bloomberg does:** Custom list of securities with live updating prices.

**Our implementation:**
- User can add/remove NSE symbols to a watchlist (stored in session state or a JSON file)
- Table columns: Symbol, LTP, Change, %Change, Open, High, Low, Prev Close, Volume, 52W High, 52W Low
- Color-coded rows (green/red based on change)
- Click a symbol → navigates to its price chart (Module 03)

**Data source:** `nsetools` → `get_quote()` for each symbol

---

### MODULE 03: Price Charts with Technicals (Bloomberg: GP)

**What Bloomberg does:** Interactive price chart with overlays (MA, Bollinger, MACD, RSI, volume).

**Our implementation:**
- Symbol input + period selector (1D, 1W, 1M, 3M, 6M, 1Y, 3Y, 5Y, Max)
- Candlestick chart via Plotly with volume bars below
- Overlay toggles: SMA(20/50/200), EMA(9/21), Bollinger Bands, VWAP
- Sub-chart toggles: RSI(14), MACD(12,26,9), ADX, Stochastic, OBV
- Dark theme matching Bloomberg (black bg, green/white candles)
- Support/Resistance levels (auto-detected from pivot points)

**Data source:** `jugaad-data` → `stock_df()` for historical; `ta` library for indicators

**Plotly config:** Use `plotly.graph_objects` with `Candlestick`, custom dark `layout.template`

---

### MODULE 04: Company Description (Bloomberg: DES)

**What Bloomberg does:** Company overview — business description, sector, market cap, 52-week range, key stats.

**Our implementation:**
- Company name, sector, industry, ISIN
- Key stats: Market Cap, P/E, P/B, EPS, Dividend Yield, 52W range, Beta, Book Value
- Business description (from yfinance `.info`)
- Management/officers list
- Share holding pattern (Promoter %, FII %, DII %, Public %)

**Data source:** `yfinance` → `Ticker("SYMBOL.NS").info`, `nsetools` for additional NSE-specific data

---

### MODULE 05: Financial Statements & Ratios (Bloomberg: FA)

**What Bloomberg does:** Income statement, balance sheet, cash flow — quarterly and annual. Key ratios.

**Our implementation:**
- Three tabs: Income Statement | Balance Sheet | Cash Flow
- Toggle: Annual vs Quarterly
- Display as formatted tables (₹ in Crores)
- Key Ratios panel: ROE, ROA, ROCE, Debt/Equity, Current Ratio, Interest Coverage, Operating Margin, Net Margin, EV/EBITDA
- Trend sparklines for key metrics (revenue, PAT, margins over 5 years)
- Peer comparison option (select 3-4 peers for side-by-side)

**Data source:** `yfinance` → `.financials`, `.quarterly_financials`, `.balance_sheet`, `.cashflow`

**Note:** yfinance data for Indian stocks may have gaps. Consider scraping Screener.in or Trendlyne as fallback.

---

### MODULE 06: Stock Screener (Bloomberg: EQS)

**What Bloomberg does:** Filter stocks by fundamentals, technicals, and custom criteria.

**Our implementation:**
- Universe selector: Nifty 50 / Nifty 100 / Nifty 200 / Nifty 500 / All NSE
- Filter criteria (multi-select, range sliders):
  - Market Cap (Mega/Large/Mid/Small)
  - P/E ratio range
  - P/B ratio range
  - ROE > X%
  - Debt/Equity < X
  - Dividend Yield > X%
  - Revenue growth > X% (YoY)
  - 52-week high/low proximity
  - RSI range (for oversold/overbought)
  - Sector filter
- Results table: Sortable by any column
- Export to CSV button

**Data source:** Bulk fetch via `yfinance` for fundamentals; `nsetools` for stock lists per index

**Engine:** `analytics/screener_engine.py` — takes filter dict, applies to DataFrame, returns ranked results

---

### MODULE 07: Option Chain & OI Analysis (Bloomberg: OMON)

**What Bloomberg does:** Real-time option chain — strikes, premiums, OI, Greeks.

**Our implementation:**
- Symbol input + Expiry date selector
- Option chain table: Strike | Call OI | Call Chg OI | Call LTP | Call IV | ← Strike → | Put LTP | Put IV | Put OI | Put Chg OI
- Color gradient on OI (heatmap style — higher OI = deeper color)
- PCR (Put-Call Ratio) display — by OI and by volume
- Max Pain calculation and display
- OI buildup analysis: Long buildup / Short buildup / Short covering / Long unwinding
- Straddle/Strangle premium chart by strike

**Data source:** `nsepython` → option chain APIs; `nsetools` → `get_option_chain()`

**India-specific:** This is CRITICAL for Indian F&O traders. Nifty/BankNifty weekly expiry options are hugely popular.

---

### MODULE 08: Sector Heatmap (Bloomberg: IMAP)

**What Bloomberg does:** Visual heatmap of market sectors, sized by market cap, colored by performance.

**Our implementation:**
- Treemap chart (Plotly `treemap`) showing Nifty 50 stocks
- Grouped by sector (Financial, IT, Energy, FMCG, Auto, Pharma, etc.)
- Sized by market cap
- Colored by daily % change (deep green to deep red gradient)
- Click into a sector → shows individual stocks within it
- Time period toggle: Today / 1 Week / 1 Month / 3 Months / YTD

**Data source:** `nsetools` for live data; hardcoded sector mapping in `utils/constants.py`

---

### MODULE 09: Index & Stock Comparison (Bloomberg: HS / COMP)

**What Bloomberg does:** Overlay performance of multiple securities on one normalized chart.

**Our implementation:**
- Multi-select: Pick up to 5 symbols/indices
- Normalized performance chart (rebased to 100 at start date)
- Date range picker
- Stats table below: Total Return, CAGR, Volatility, Sharpe, Max Drawdown, Beta (vs Nifty 50)
- Correlation matrix heatmap

**Data source:** `jugaad-data` or `yfinance` for historical data; `numpy` for calculations

---

### MODULE 10: Portfolio Tracker (Bloomberg: PORT)

**What Bloomberg does:** Track portfolio holdings, P&L, allocation, risk metrics.

**Our implementation:**
- Manual input: Add holdings (Symbol, Qty, Avg Price, Date)
- Store in a local JSON/CSV file
- Current valuation with live prices
- Holdings table: Symbol, Qty, Avg Price, LTP, P&L (₹ & %), Weight %
- Summary: Total Invested, Current Value, Total P&L, XIRR, Day's P&L
- Allocation pie chart (by stock, by sector)
- Daily P&L trend chart

**Data source:** User-entered portfolio + live prices from `nsetools`

---

### MODULE 11: Backtesting Engine (Bloomberg: BTST)

**What Bloomberg does:** Back-test trading strategies historically.

**Our implementation (TWO ENGINES):**

**A. Quick Backtest (vectorbt):**
- Pre-built strategies: SMA Crossover, RSI Mean Reversion, MACD Signal, Bollinger Band Bounce
- Parameter inputs (e.g., fast SMA period, slow SMA period)
- Symbol + date range selection
- Results: Total Return, Sharpe, Max Drawdown, Win Rate, Profit Factor
- Equity curve chart + drawdown chart
- Trade log table

**B. Advanced Backtest (Backtrader):**
- Custom strategy code input (Python textarea)
- Commission and slippage settings
- Multi-stock support
- Full tearsheet output via quantstats

**Data source:** `jugaad-data` or `yfinance` for historical OHLCV

---

### MODULE 12: Portfolio Optimizer (Bloomberg: PORT analytics)

**What Bloomberg does:** Optimize portfolio allocation — mean-variance, risk analysis.

**Our implementation:**
- Input: List of stocks (or load from Portfolio module)
- Lookback period for covariance estimation
- Optimization targets:
  - Max Sharpe Ratio
  - Min Volatility
  - Risk Parity
  - Max Return for given risk
- Efficient frontier plot (Plotly scatter)
- Recommended weights table
- Monte Carlo simulation (10,000 random portfolios overlay)
- Risk metrics: Portfolio VaR (95%, 99%), Expected Shortfall, Beta

**Data source:** Historical returns from `yfinance`; `PyPortfolioOpt` for optimization; `numpy` for Monte Carlo

---

### MODULE 13: Economic Dashboard (Bloomberg: ECST / ECO / BTMM)

**What Bloomberg does:** Economic data — GDP, inflation, rates, economic calendar.

**Our implementation:**
- India section:
  - RBI Repo Rate, Reverse Repo, CRR, SLR (from jugaad-data RBI module)
  - CPI Inflation trend
  - IIP (Index of Industrial Production)
  - GDP growth rate
  - USD/INR exchange rate chart
  - 10Y G-Sec yield
- Global section:
  - US Fed Funds Rate, ECB Rate
  - US 10Y Treasury yield
  - Crude Oil (Brent) price
  - Gold price
- Economic calendar: Upcoming RBI policy dates, US Fed meetings, GDP release dates

**Data source:** `jugaad-data` → RBI module; `pandas-datareader` → FRED; `yfinance` for commodities/forex

---

### MODULE 14: FII/DII Flow Tracker (India-Specific — No Bloomberg Equivalent)

**What Bloomberg does:** N/A — this is unique to Indian markets.

**Our implementation:**
- Daily FII and DII net buy/sell in Cash and F&O segments
- Trend chart: FII/DII cumulative flows over 1M, 3M, 6M, 1Y
- Correlation overlay: FII flows vs Nifty 50 movement
- Table: Date-wise breakup
- Monthly aggregation view

**Data source:** NSDL/CDSL FII data, MoneyControl scraping, or NSE bulk data downloads

---

### MODULE 15: News & Sentiment (Bloomberg: TOP / NEWS)

**What Bloomberg does:** Real-time financial news, ranked by relevance/impact.

**Our implementation:**
- RSS feed aggregation from:
  - Moneycontrol
  - Economic Times Markets
  - LiveMint
  - Business Standard
  - NSE announcements
- Display: Headline, Source, Time, Link
- Filter by: Market / Stock-specific / Sector / Global
- Basic sentiment score (positive/negative/neutral) using keyword matching or TextBlob

**Data source:** `feedparser` for RSS; `beautifulsoup4` for scraping if needed

---

### MODULE 16: Price & Volume Alerts (Bloomberg: ALRT)

**What Bloomberg does:** Custom alerts when conditions are met.

**Our implementation:**
- Set alerts: Symbol + Condition (Price Above/Below, Volume Spike > X%, % Change > X)
- Alert log: Shows triggered alerts
- In-app notification via `st.toast()` or `st.warning()`
- Optional: Email/Telegram notification via webhook (advanced)

**Data source:** Periodic polling via `nsetools` live quotes

---

## 4. UI / UX Design Specifications

### Bloomberg Dark Theme CSS

```
Background: #0A0A0A (near black)
Panel backgrounds: #1A1A1A
Borders: #333333
Primary text: #E0E0E0 (off-white)
Headers/Labels: #FF9900 (Bloomberg amber)
Positive values: #00CC66 (green)
Negative values: #FF3333 (red)
Accent/Links: #3399FF (blue)
Font: 'Fira Code', 'Consolas', 'Courier New', monospace
Font size: 13-14px for data, 11-12px for labels
```

### Layout Principles

- Dense data display — minimize whitespace (unlike typical Streamlit apps)
- Use `st.columns()` extensively for multi-column layouts
- Use `st.dataframe()` with custom styling for tables
- Inject custom CSS via `st.markdown('<style>...</style>', unsafe_allow_html=True)`
- Use `st.tabs()` for main module navigation
- Sidebar for global controls (symbol search, market status, clock)

---

## 5. Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Setup:** `python3.12 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`

- [ ] Project setup: folder structure, requirements.txt, virtual environment (Python 3.12.x)
- [ ] `theme.py`: Bloomberg dark CSS theme
- [ ] `app.py`: Main shell with tab navigation
- [ ] `data/nse_live.py`: Live quote fetching with caching
- [ ] `data/nse_historical.py`: Historical OHLCV fetching
- [ ] `utils/formatting.py`: ₹ formatting, Cr/L conversion, color coding
- [ ] `utils/constants.py`: Nifty 50/100/200/500 symbol lists, sector mappings
- [ ] **Module 01**: Market Overview Dashboard
- [ ] **Module 02**: Watchlist

### Phase 2: Core Analysis (Week 3-4)

- [ ] **Module 03**: Price Charts with Technicals (Plotly candlestick + ta indicators)
- [ ] **Module 04**: Company Description
- [ ] **Module 05**: Financial Statements & Ratios
- [ ] **Module 08**: Sector Heatmap
- [ ] **Module 09**: Index/Stock Comparison
- [ ] `data/fundamentals.py`: yfinance wrapper for Indian stocks

### Phase 3: F&O & Advanced (Week 5-6)

- [ ] `data/nse_fno.py`: Option chain, OI data
- [ ] **Module 06**: Stock Screener
- [ ] **Module 07**: Option Chain & OI Analysis
- [ ] **Module 14**: FII/DII Tracker
- [ ] `analytics/technicals.py`: Technical indicator engine
- [ ] `analytics/screener_engine.py`: Screener filtering engine

### Phase 4: Portfolio & Risk (Week 7-8)

- [ ] **Module 10**: Portfolio Tracker
- [ ] **Module 11**: Backtesting Engine (vectorbt + backtrader)
- [ ] **Module 12**: Portfolio Optimizer (PyPortfolioOpt)
- [ ] `analytics/risk_metrics.py`: VaR, Sharpe, drawdown calculations
- [ ] `analytics/fundamentals_calc.py`: Ratio calculations

### Phase 5: Macro & Polish (Week 9-10)

- [ ] `data/economic.py`: RBI + FRED data
- [ ] **Module 13**: Economic Dashboard
- [ ] **Module 15**: News & Sentiment
- [ ] **Module 16**: Alerts
- [ ] Performance optimization (caching, lazy loading)
- [ ] Error handling for all API calls
- [ ] README with screenshots and usage guide

---

## 6. Bloomberg Function → Python Mapping (Quick Reference)

| Bloomberg Cmd | Function | Python Stack | Module |
|--------------|----------|-------------|--------|
| WEI / MAIN | Market overview | nsetools, jugaad-data | M01 |
| MOST | Watchlist | nsetools | M02 |
| GP | Price chart + technicals | yfinance/jugaad + Plotly + ta | M03 |
| DES | Company description | yfinance .info | M04 |
| FA | Financial statements | yfinance financials + pandas | M05 |
| EQS | Equity screener | yfinance + pandas filtering | M06 |
| OMON | Option monitor | nsepython + nsetools | M07 |
| IMAP | Market heatmap | nsetools + Plotly treemap | M08 |
| HS / COMP | Performance comparison | yfinance + numpy | M09 |
| PORT | Portfolio | User input + nsetools live | M10 |
| BTST / EQBT | Backtesting | vectorbt / Backtrader | M11 |
| PORT (risk) | Portfolio optimization | PyPortfolioOpt + numpy | M12 |
| ECST / ECO | Economic data | jugaad-data RBI + FRED | M13 |
| — | FII/DII flows | NSE data / scraping | M14 |
| TOP / NEWS | News aggregation | feedparser + BS4 | M15 |
| ALRT | Price alerts | nsetools polling | M16 |

---

## 7. Key Dependencies (requirements.txt) — Pinned Stable Versions

**Python version: 3.12.x recommended**

All libraries below are 100% free. Total cost: ₹0.

```
# ── Core Framework ──
streamlit==1.55.0              # Latest stable (Mar 2026). Apache 2.0. FREE.
plotly==6.0.1                  # Latest stable (Jan 2026). MIT. FREE.
pandas==2.2.3                  # Latest stable. BSD. FREE.
numpy==2.2.3                   # Latest stable. BSD. FREE.
scipy==1.14.1                  # Latest stable. BSD. FREE.

# ── Indian Market Data (all scrape NSE/RBI — no API key needed) ──
jugaad-data==0.31.1            # Latest stable (Nov 2025). Public domain. FREE. PRIMARY source for NSE data.
nsetools==2.0.1                # Latest stable (Mar 2025). MIT. FREE. Live quotes + index data.
nsepython==2.97                # Latest stable. GPL-like. FREE. Best for option chains/Greeks/OI.

# ── Global/Fundamental Data ──
yfinance==0.2.54               # Latest stable. Apache 2.0. FREE but FRAGILE — unofficial Yahoo scraper.
                               # Gets rate-limited (429) under heavy use. Use for batch fundamental pulls only.
pandas-datareader==0.10.0      # Latest stable. BSD. FREE. FRED macro data (official API).

# ── Technical Analysis ──
ta==0.11.0                     # Latest stable. MIT. FREE. 40+ indicators (RSI, MACD, Bollinger, etc.)

# ── Backtesting ──
vectorbt==0.26.2               # Latest open-source stable. Apache 2.0 + Commons Clause. FREE.
                               # Note: vectorbt PRO ($20/mo) exists but is NOT needed.
backtrader==1.9.78.123         # Latest stable (last PyPI: 2019, but library is mature & stable). GPL v3. FREE.

# ── Portfolio & Risk ──
pyportfolioopt==1.5.6          # Latest stable (Feb 2026). MIT. FREE.
quantstats==0.0.64             # Latest stable. Apache 2.0. FREE.

# ── News & Scraping ──
feedparser==6.0.11             # Latest stable. BSD-2. FREE.
beautifulsoup4==4.12.3         # Latest stable. MIT. FREE.
requests==2.32.3               # Latest stable. Apache 2.0. FREE.
textblob==0.18.0               # Latest stable. MIT. FREE.

# ── Optional (install when needed) ──
# apscheduler==3.10.4          # For scheduled data refresh / alerts
# mplfinance==0.12.10b0        # Alternative charting library
# openbb>=4.0                  # 100+ data connectors (AGPL v3, free core)
```

### Version Pinning Strategy

- **Pin exact versions** (`==`) in requirements.txt for reproducibility.
- All versions above are the latest stable releases as of March 2026.
- `backtrader` hasn't been updated on PyPI since 2019 — this is normal, the library is feature-complete and stable. If you hit Python 3.12 compatibility issues, install from GitHub: `pip install git+https://github.com/mementum/backtrader.git`
- `vectorbt` open-source (0.26.x) is distinct from vectorbt PRO. The open-source version is sufficient for everything in this plan.
- Run `pip install --upgrade <package>` periodically to check for security patches, but test before upgrading in production.

---

## 8. Important Notes for Implementation

### Rate Limiting & Caching
- NSE blocks frequent requests. Use `data/cache.py` with a TTL of 15-60 seconds for live data.
- jugaad-data has built-in caching. Leverage it.
- yfinance bulk downloads are better than individual calls. Batch where possible.

### Indian Market Specifics
- Market hours: 9:15 AM to 3:30 PM IST (pre-open 9:00-9:08)
- Symbols: NSE uses plain symbols (RELIANCE, TCS, INFY). For yfinance, append `.NS` (NSE) or `.BO` (BSE).
- Currency: Always display in ₹. Large numbers in Crores (Cr) or Lakhs (L).
- F&O lot sizes: These change periodically. Fetch dynamically from NSE.
- Nifty weekly expiry: Every Thursday (critical for options module).

### Data Quality Gotchas
- yfinance Indian fundamental data can have missing fields. Always handle NaN gracefully.
- NSE website occasionally changes its API structure. jugaad-data handles this better than raw scraping.
- Historical data pre-2010 may be spotty from free sources.
- Corporate actions (splits, bonuses) need adjusted prices. yfinance auto-adjusts; jugaad-data may not.

### Performance Tips
- Use `st.cache_data` and `st.cache_resource` liberally in Streamlit
- Load heavy data (screener universe) once at startup
- Use `st.fragment` for partial reruns (Streamlit 1.33+)
- Consider `st_autorefresh` for live data updates during market hours

---

## 9. Existing Open-Source References

Study these projects for architecture ideas and code patterns:

| Project | GitHub | Why Study It |
|---------|--------|-------------|
| **OpenBB** | github.com/OpenBB-finance/OpenBB | Architecture of a modular financial terminal, data provider pattern |
| **Fincept Terminal** | github.com/Fincept-Corporation/FinceptTerminal | Indian-market focused terminal, Tauri + React + Python hybrid |
| **awesome-quant** | github.com/wilsonfreitas/awesome-quant | Master list of every quant finance library |
| **Indian-Stock-Market-API** | github.com/0xramm/Indian-Stock-Market-API | REST API wrapper for NSE/BSE via yfinance |

---

## 10. Future Enhancements (Post-MVP)

- **AI Copilot**: Add an LLM chat interface (Claude API or local Ollama) that can answer questions about your portfolio and market data
- **Broker Integration**: Connect to Zerodha Kite / Angel One / Upstox API for live order placement
- **Paper Trading**: Simulated trading with live prices
- **Telegram Bot**: Push alerts and daily summaries to Telegram
- **Database Backend**: SQLite or PostgreSQL for persistent portfolio and historical data storage
- **Multi-user Auth**: Streamlit-Authenticator for login/password
- **Mobile Responsive**: Custom CSS for mobile layout (Streamlit is desktop-first)
- **WebSocket Live Data**: Replace polling with websocket streams (Kite Ticker, Angel SmartAPI WebSocket)

---

## 11. Pricing & Reliability Audit (Verified March 2026)

### Total Cost: ₹0

Every library in this plan is free for personal use. No API keys, subscriptions, or accounts required.

### Pricing Breakdown by Category

| Category | Libraries | Cost | Notes |
|----------|----------|------|-------|
| **Core framework** | Streamlit, Plotly, pandas, numpy, scipy | FREE | All MIT/BSD/Apache. Rock-solid stability. |
| **Indian market data** | jugaad-data, nsetools, nsepython | FREE | All scrape NSE public website. No API key. Can break if NSE changes site structure. |
| **Fundamentals** | yfinance | FREE | Unofficial Yahoo scraper. Rate-limited under heavy use. Fine for batch pulls. |
| **Global macro** | pandas-datareader (FRED) | FREE | Official US Fed Reserve API. Very reliable. |
| **Technical analysis** | ta | FREE | MIT license. Stable, well-maintained. |
| **Backtesting** | vectorbt (open source), Backtrader | FREE | vectorbt PRO ($20/mo) exists but is NOT needed. Backtrader is GPL v3. |
| **Portfolio/risk** | PyPortfolioOpt, quantstats | FREE | Both MIT/Apache. Actively maintained. |
| **News/scraping** | feedparser, beautifulsoup4 | FREE | Standard Python ecosystem. |

### What You're Trading Off (vs Bloomberg at ₹25L/year)

| Bloomberg Advantage | Our Limitation | Mitigation |
|--------------------|----------------|------------|
| 99.99% uptime SLA | NSE scrapers can break anytime | Use multiple data sources as fallback (jugaad → nsetools → yfinance) |
| Real-time tick data | Minimum 15-60 sec polling delay | Acceptable for swing/positional trading. For tick data, need broker WebSocket (Zerodha Kite Ticker — free with demat) |
| Clean, normalized data | yfinance has gaps for small-cap Indian stocks | Handle NaN gracefully. Supplement with screener.in scraping if needed. |
| Analyst reports/research | No equivalent free source | Use RSS news feeds + basic sentiment as substitute |
| Fixed income / bonds / derivatives pricing | Not covered in free sources | Out of scope for v1. Can add later with paid APIs. |

### Rate Limiting Guidelines (Critical)

| Source | Safe Polling Rate | What Happens If Exceeded |
|--------|------------------|------------------------|
| NSE (via jugaad-data / nsetools) | 1 request per 15-60 sec per endpoint | IP gets temporarily blocked. jugaad-data has built-in caching to help. |
| Yahoo Finance (via yfinance) | ~2000 requests/hour (unofficial) | 429 Too Many Requests error. Worse on shared cloud IPs (Streamlit Cloud, AWS). Works fine locally. |
| FRED (via pandas-datareader) | 120 requests/min | Generous limits. Unlikely to hit unless bulk-downloading all series. |

### If You Need Paid Data Later (Future Upgrades)

| Provider | What It Offers | Cost | When To Consider |
|----------|---------------|------|------------------|
| **Zerodha Kite Ticker** | Real-time WebSocket tick data | FREE (with Zerodha demat account) | When you need true real-time streaming |
| **Angel One SmartAPI** | Live data + order placement | FREE (with Angel One account) | For broker integration / live trading |
| **EODHD** | Reliable global + Indian fundamentals | $20/mo (basic) | If yfinance becomes too unreliable |
| **Polygon.io** | US market data (tick-level) | $29/mo (starter) | If expanding beyond Indian markets |
| **Twelve Data** | Global market data + WebSocket | Free tier (800 req/day) | Reliable fallback for yfinance |
