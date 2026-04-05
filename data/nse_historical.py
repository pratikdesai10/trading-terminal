"""Historical OHLCV data fetching — yfinance primary (adjusted), jugaad-data fallback."""

from datetime import date, timedelta

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


@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_history(symbol, start_date=None, end_date=None):
    """Fetch historical OHLCV data for an NSE stock.

    Returns DataFrame with columns: Date, Open, High, Low, Close, Volume.
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=365)

    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

    logger.info(f"get_stock_history | symbol={symbol} | {start_date} to {end_date}")

    # Primary: yfinance (returns split/bonus-adjusted prices by default)
    df = _fetch_yfinance(symbol, start_date, end_date)
    if df is not None and not df.empty:
        logger.info(f"get_stock_history | symbol={symbol} | OK via yfinance | {len(df)} rows")
        return df

    # Fallback: jugaad-data (unadjusted — may show cliffs on splits/bonuses)
    df = _fetch_jugaad(symbol, start_date, end_date)
    if df is not None and not df.empty:
        logger.info(f"get_stock_history | symbol={symbol} | OK via jugaad-data | {len(df)} rows")
        return df

    # NOTE: raise instead of returning an empty DataFrame so st.cache_data does
    # NOT memoize the failure. Empty DataFrames ARE cached (they are valid
    # return values); exceptions are not. Callers must wrap in try/except.
    logger.error(f"get_stock_history | symbol={symbol} | ALL SOURCES FAILED")
    raise RuntimeError(f"get_stock_history: all sources failed for {symbol}")


def _fetch_jugaad(symbol, start_date, end_date):
    """Fetch from jugaad-data."""
    try:
        from jugaad_data.nse import stock_df
        df = stock_df(
            symbol=symbol,
            from_date=start_date,
            to_date=end_date,
            series="EQ",
        )
        if df is not None and not df.empty:
            # jugaad-data column names vary between versions
            df = df.rename(columns={
                "DATE": "Date",
                "OPEN": "Open",
                "HIGH": "High",
                "LOW": "Low",
                "CLOSE": "Close",
                "VOLUME": "Volume",
                "CH_OPENING_PRICE": "Open",
                "CH_TRADE_HIGH_PRICE": "High",
                "CH_TRADE_LOW_PRICE": "Low",
                "CH_CLOSING_PRICE": "Close",
                "CH_TOT_TRADED_QTY": "Volume",
                "CH_TIMESTAMP": "Date",
            })
            required = ["Date", "Open", "High", "Low", "Close"]
            if all(col in df.columns for col in required):
                df["Date"] = pd.to_datetime(df["Date"])
                if "Volume" not in df.columns:
                    df["Volume"] = 0
                df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].sort_values("Date")
                df = df.reset_index(drop=True)
                return df
            else:
                logger.warning(f"_fetch_jugaad | {symbol} | missing columns, got: {list(df.columns)}")
    except Exception as e:
        logger.warning(f"_fetch_jugaad | {symbol} | {type(e).__name__}: {e}")
    return None


def _fetch_yfinance(symbol, start_date, end_date):
    """Fetch from yfinance as fallback."""
    from data.fundamentals import _yf_call_with_backoff
    try:
        ticker = _yf.Ticker(f"{symbol}.NS", session=_SESSION)
        df = _yf_call_with_backoff(
            lambda: ticker.history(start=str(start_date), end=str(end_date)),
            label=f"history({symbol})",
        )
        if df is not None and not df.empty:
            # yfinance may return MultiIndex columns for single-ticker downloads
            # (e.g. ("Close", "ABB.NS")) — flatten to simple column names
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]
            df = df.reset_index()
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
            elif "index" in df.columns:
                df = df.rename(columns={"index": "Date"})
                df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
            if "Volume" not in df.columns:
                df["Volume"] = 0
            available = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in df.columns]
            return df[available]
    except Exception as e:
        logger.warning(f"_fetch_yfinance | {symbol} | {type(e).__name__}: {e}")
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_index_history(index_name, start_date=None, end_date=None):
    """Fetch historical data for an NSE index.

    Returns DataFrame with columns: Date, Open, High, Low, Close.
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=365)

    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

    logger.info(f"get_index_history | index={index_name} | {start_date} to {end_date}")

    # jugaad-data index history
    try:
        from jugaad_data.nse import index_df
        df = index_df(
            symbol=index_name,
            from_date=start_date,
            to_date=end_date,
        )
        if df is not None and not df.empty:
            df = df.rename(columns={
                "HistoricalDate": "Date",
                "OPEN": "Open",
                "HIGH": "High",
                "LOW": "Low",
                "CLOSE": "Close",
            })
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                cols = [c for c in ["Date", "Open", "High", "Low", "Close"] if c in df.columns]
                df = df[cols].sort_values("Date").reset_index(drop=True)
                logger.info(f"get_index_history | index={index_name} | OK via jugaad-data | {len(df)} rows")
                return df
    except Exception as e:
        logger.warning(f"get_index_history | index={index_name} | jugaad-data failed: {type(e).__name__}: {e}")

    # yfinance fallback for indices
    yf_map = {
        "NIFTY 50": "^NSEI",
        "NIFTY BANK": "^NSEBANK",
        "INDIA VIX": "^INDIAVIX",
        "NIFTY IT": "^CNXIT",
        "NIFTY NEXT 50": "^NSMIDCP",
        "NIFTY PHARMA": "^CNXPHARMA",
        "NIFTY AUTO": "^CNXAUTO",
        "NIFTY FMCG": "^CNXFMCG",
        "NIFTY METAL": "^CNXMETAL",
        "NIFTY REALTY": "^CNXREALTY",
        "NIFTY ENERGY": "^CNXENERGY",
        "NIFTY MEDIA": "^CNXMEDIA",
        "NIFTY PSU BANK": "^CNXPSUBANK",
        "NIFTY PRIVATE BANK": "^NIFTYPVTBANK",
        "NIFTY HEALTHCARE INDEX": "^CNXHEALTH",
        "NIFTY FINANCIAL SERVICES": "^CNXFIN",
        "NIFTY CONSUMER DURABLES": "^CNXCONSUM",
        "NIFTY OIL & GAS": "^CNXOILGAS",
        "NIFTY MIDCAP 50": "^NSEMDCP50",
    }
    yf_symbol = yf_map.get(index_name)
    if yf_symbol:
        from data.fundamentals import _yf_call_with_backoff
        try:
            ticker = _yf.Ticker(yf_symbol, session=_SESSION)
            df = _yf_call_with_backoff(
                lambda: ticker.history(start=str(start_date), end=str(end_date)),
                label=f"index_history({index_name})",
            )
            if df is not None and not df.empty:
                df = df.reset_index()
                if "Date" in df.columns:
                    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
                elif "index" in df.columns:
                    df = df.rename(columns={"index": "Date"})
                    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
                cols = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in df.columns]
                logger.info(f"get_index_history | index={index_name} | OK via yfinance | {len(df)} rows")
                return df[cols]
        except Exception as e:
            logger.warning(f"get_index_history | index={index_name} | yfinance failed: {type(e).__name__}: {e}")

    logger.error(f"get_index_history | index={index_name} | ALL SOURCES FAILED")
    raise RuntimeError(f"get_index_history: all sources failed for {index_name}")
