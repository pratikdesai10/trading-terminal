# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Bloomberg-style terminal for Indian markets (NSE/BSE) built with Python + Streamlit. Apache 2.0 license. Full spec in `indian-bloomberg-terminal-plan.md`.

## Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run the app
streamlit run app.py

# Run on specific port
streamlit run app.py --server.port 8502
```

## Architecture

- **`app.py`** — Main Streamlit entry point with tab navigation.
- **`theme.py`** — Bloomberg dark CSS injected globally (black #0A0A0A bg, amber #FF9900 headers, green/red for +/-).
- **`config.py`** — Nifty 50 symbols, sector mappings, color constants, cache TTLs, key indices.
- **`data/`** — Data fetching layer. Each file wraps one data source. Uses `st.cache_data` for caching.
  - `nse_live.py` — jugaad-data (primary) + nsetools (fallback) for live quotes/indices.
  - `nse_historical.py` — jugaad-data (primary) + yfinance (fallback) for OHLCV.
  - `fundamentals.py` — yfinance wrapper for company info, financials, balance sheet, cashflow (cached 24h).
  - `nse_fno.py` — Option chain data (jugaad-data primary, nsepython fallback). PCR, max pain calculations.
  - `economic.py` — RBI rates (hardcoded), forex/commodity/yield data via yfinance. Economic calendar dates.
  - `cache.py` — Simple TTL cache decorator for non-Streamlit contexts.
  - `database.py` — SQLite persistence layer. CRUD for portfolio, watchlist, alerts, paper trading. Auto-creates `terminal.db`.
  - `llm_agent.py` — LLM agent logic for AI Copilot. Tool definitions, provider abstraction (Anthropic/Ollama), agentic tool-use loop.
- **`modules/`** — Each Bloomberg function is one module file (m01, m02, ..., m18). Each exposes a `render()` function.
- **`analytics/`** — Reusable calculation engines.
  - `screener_engine.py` — Fundamental data fetching via yfinance for stock screener.
  - `risk_metrics.py` — VaR, CVaR/ES, Sharpe, Sortino, max drawdown calculations (pure numpy).
- **`utils/`** — `formatting.py` has ₹ formatting, Crore/Lakh conversion, color-coded display helpers.

## Conventions

- All monetary values in ₹ Crores.
- Indian number grouping (12,34,567).
- Dense, monospace Bloomberg-style UI — minimize whitespace.
- Green (#00CC66) for positive, Red (#FF3333) for negative, Amber (#FF9900) for headers.
- Data sources: jugaad-data primary, nsetools secondary, yfinance fallback.
- yfinance is fragile — use for batch pulls, never for live polling.
- Each module is a self-contained file with a `render()` function called from `app.py`.

## Build Phases

**Phase 1** complete: M01 (Market Overview) + M02 (Watchlist).
**Phase 2** complete: M03 (Charts) + M04 (Company) + M05 (Financials) + M08 (Heatmap) + M09 (Comparison) + data/fundamentals.py.
**Phase 3** complete: M06 (Stock Screener) + M07 (Option Chain & OI) + M14 (FII/DII Tracker) + analytics/screener_engine.py + data/nse_fno.py.
**Phase 4** complete: M10 (Portfolio Tracker) + M11 (Backtesting Engine) + M12 (Portfolio Optimizer) + analytics/risk_metrics.py.
**Phase 5** complete: M13 (Economic Dashboard) + M15 (News & Sentiment) + M16 (Price Alerts) + data/economic.py.
**Phase 6** complete: Advanced indicators, expanded universe (Nifty 100/200), peer comparison, trend sparklines, Black-Litterman, XIRR, custom strategy sandbox.
**Phase 7** complete: SQLite persistence (data/database.py) for portfolio, watchlist, alerts + M17 (Paper Trading) with virtual cash, order execution, position tracking, realized P&L.
**Phase 8** complete: M18 (AI Copilot) — LLM chat interface with 12 agentic tools for querying market data, portfolio, options, fundamentals. Supports Claude API (primary) and Ollama (local fallback). data/llm_agent.py.
All 18 modules built and operational. Data persists across page refreshes via SQLite (data/terminal.db).
