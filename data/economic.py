"""Data layer for economic indicators — RBI rates, forex, commodities, yields."""

import pandas as pd
import streamlit as st
import yfinance as _yf

from utils.logger import logger

try:
    from curl_cffi import requests as _curl_requests
    _SESSION = _curl_requests.Session(impersonate="chrome")
except Exception:
    import requests as _requests
    _SESSION = _requests.Session()
    _SESSION.headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


# ── RBI Key Rates (hardcoded — APIs unreliable) ──

_RBI_RATES = {
    "Repo Rate": {"value": 6.25, "updated": "2025-02-07", "note": "Cut from 6.50% (Feb 2025 MPC)"},
    "SDF Rate": {"value": 6.00, "updated": "2025-02-07", "note": "Standing Deposit Facility"},
    "MSF Rate": {"value": 6.50, "updated": "2025-02-07", "note": "Marginal Standing Facility"},
    "CRR": {"value": 4.00, "updated": "2024-12-14", "note": "Cash Reserve Ratio"},
    "SLR": {"value": 18.00, "updated": "2024-04-01", "note": "Statutory Liquidity Ratio"},
    "Bank Rate": {"value": 6.50, "updated": "2025-02-07", "note": "Same as MSF Rate"},
}

# ── RBI MPC Meeting Dates 2026 ──
_RBI_MPC_DATES = [
    {"date": "2026-04-08", "event": "RBI MPC Decision", "note": "Apr 2026 Policy Review"},
    {"date": "2026-06-04", "event": "RBI MPC Decision", "note": "Jun 2026 Policy Review"},
    {"date": "2026-08-05", "event": "RBI MPC Decision", "note": "Aug 2026 Policy Review"},
    {"date": "2026-10-01", "event": "RBI MPC Decision", "note": "Oct 2026 Policy Review"},
    {"date": "2026-12-03", "event": "RBI MPC Decision", "note": "Dec 2026 Policy Review"},
]

# ── US Fed FOMC Meeting Dates 2026 ──
_FOMC_DATES = [
    {"date": "2026-03-18", "event": "US Fed FOMC Decision", "note": "Mar 2026 Meeting"},
    {"date": "2026-05-06", "event": "US Fed FOMC Decision", "note": "May 2026 Meeting"},
    {"date": "2026-06-17", "event": "US Fed FOMC Decision", "note": "Jun 2026 Meeting"},
    {"date": "2026-07-29", "event": "US Fed FOMC Decision", "note": "Jul 2026 Meeting"},
    {"date": "2026-09-16", "event": "US Fed FOMC Decision", "note": "Sep 2026 Meeting"},
    {"date": "2026-11-04", "event": "US Fed FOMC Decision", "note": "Nov 2026 Meeting"},
    {"date": "2026-12-16", "event": "US Fed FOMC Decision", "note": "Dec 2026 Meeting"},
]

# ── yfinance ticker symbols ──
TICKER_MAP = {
    "USD/INR": "USDINR=X",
    "Brent Crude": "BZ=F",
    "Gold": "GC=F",
    "US 10Y Yield": "^TNX",
}


def get_rbi_rates():
    """Return current RBI key rates as a dict.

    Each key maps to {"value": float, "updated": str, "note": str}.
    """
    logger.info("get_rbi_rates | returning hardcoded RBI rates")
    return dict(_RBI_RATES)


def get_economic_calendar():
    """Return upcoming RBI MPC and US FOMC dates as a list of dicts.

    Each dict: {"date": str, "event": str, "note": str}.
    Only returns dates that are on or after today.
    """
    from datetime import date

    today = date.today().isoformat()
    all_events = _RBI_MPC_DATES + _FOMC_DATES
    upcoming = [e for e in all_events if e["date"] >= today]
    upcoming.sort(key=lambda x: x["date"])

    logger.info(f"get_economic_calendar | {len(upcoming)} upcoming events")
    return upcoming


@st.cache_data(ttl=300, show_spinner=False)
def get_forex_data(pair="USDINR=X", period="1y"):
    """Fetch forex historical data via yfinance.

    Args:
        pair: yfinance ticker symbol (default USDINR=X).
        period: yfinance period string (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y).

    Returns:
        pandas DataFrame with Date, Open, High, Low, Close, Volume columns,
        or empty DataFrame on failure.
    """
    logger.info(f"get_forex_data | pair={pair} period={period}")
    try:
        df = _yf.Ticker(pair, session=_SESSION).history(period=period)
        if df is None or df.empty:
            logger.warning(f"get_forex_data | pair={pair} | empty response")
            return pd.DataFrame()

        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        logger.info(f"get_forex_data | pair={pair} | OK | rows={len(df)}")
        return df
    except Exception as e:
        logger.error(f"get_forex_data | pair={pair} | FAILED: {type(e).__name__}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_commodity_data(symbol="BZ=F", period="1y"):
    """Fetch commodity price data via yfinance.

    Args:
        symbol: yfinance ticker symbol (BZ=F for Brent, GC=F for Gold).
        period: yfinance period string.

    Returns:
        pandas DataFrame with OHLCV data, or empty DataFrame on failure.
    """
    logger.info(f"get_commodity_data | symbol={symbol} period={period}")
    try:
        df = _yf.Ticker(symbol, session=_SESSION).history(period=period)
        if df is None or df.empty:
            logger.warning(f"get_commodity_data | symbol={symbol} | empty response")
            return pd.DataFrame()

        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        logger.info(f"get_commodity_data | symbol={symbol} | OK | rows={len(df)}")
        return df
    except Exception as e:
        logger.error(f"get_commodity_data | symbol={symbol} | FAILED: {type(e).__name__}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_treasury_yield(symbol="^TNX", period="1y"):
    """Fetch US Treasury yield data via yfinance.

    Args:
        symbol: yfinance ticker symbol (^TNX for 10Y).
        period: yfinance period string.

    Returns:
        pandas DataFrame with yield data, or empty DataFrame on failure.
    """
    logger.info(f"get_treasury_yield | symbol={symbol} period={period}")
    try:
        df = _yf.Ticker(symbol, session=_SESSION).history(period=period)
        if df is None or df.empty:
            logger.warning(f"get_treasury_yield | symbol={symbol} | empty response")
            return pd.DataFrame()

        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        logger.info(f"get_treasury_yield | symbol={symbol} | OK | rows={len(df)}")
        return df
    except Exception as e:
        logger.error(f"get_treasury_yield | symbol={symbol} | FAILED: {type(e).__name__}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_current_quote(symbol):
    """Fetch the latest price/value for a yfinance ticker.

    Returns dict with 'price', 'change', 'pct_change', 'name', or None on failure.
    """
    logger.info(f"get_current_quote | symbol={symbol}")
    try:
        ticker = _yf.Ticker(symbol, session=_SESSION)
        info = ticker.info
        if not info or not isinstance(info, dict):
            logger.warning(f"get_current_quote | symbol={symbol} | no info")
            return None

        price = info.get("regularMarketPrice") or info.get("previousClose")
        prev = info.get("regularMarketPreviousClose") or info.get("previousClose")
        if price is None:
            logger.warning(f"get_current_quote | symbol={symbol} | no price data")
            return None

        change = (price - prev) if prev else 0
        pct_change = (change / prev * 100) if prev and prev != 0 else 0

        result = {
            "price": price,
            "change": change,
            "pct_change": pct_change,
            "name": info.get("shortName", symbol),
        }
        logger.info(f"get_current_quote | symbol={symbol} | OK | price={price}")
        return result
    except Exception as e:
        logger.error(f"get_current_quote | symbol={symbol} | FAILED: {type(e).__name__}: {e}")
        return None
