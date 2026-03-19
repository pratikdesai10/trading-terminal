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
  - `cache.py` — Simple TTL cache decorator for non-Streamlit contexts.
- **`modules/`** — Each Bloomberg function is one module file (m01, m02, ..., m16). Each exposes a `render()` function.
- **`analytics/`** — Reusable calculation engines (technicals, risk, screener). Not yet built.
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

Currently on **Phase 1** (M01 + M02). See plan for Phases 2-5.
