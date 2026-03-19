"""Historical OHLCV data fetching — jugaad-data primary, yfinance fallback."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st


@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_history(symbol, start_date=None, end_date=None):
    """Fetch historical OHLCV data for an NSE stock.

    Args:
        symbol: NSE symbol (e.g., "RELIANCE").
        start_date: Start date (default: 1 year ago).
        end_date: End date (default: today).

    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume.
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=365)

    # Ensure date types
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

    # Primary: jugaad-data
    df = _fetch_jugaad(symbol, start_date, end_date)
    if df is not None and not df.empty:
        return df

    # Fallback: yfinance
    df = _fetch_yfinance(symbol, start_date, end_date)
    if df is not None and not df.empty:
        return df

    return pd.DataFrame()


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
                df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].sort_values("Date")
                df = df.reset_index(drop=True)
                return df
    except Exception:
        pass
    return None


def _fetch_yfinance(symbol, start_date, end_date):
    """Fetch from yfinance as fallback."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.NS")
        df = ticker.history(start=str(start_date), end=str(end_date))
        if df is not None and not df.empty:
            df = df.reset_index()
            df = df.rename(columns={"index": "Date"})
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
            df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
            return df
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_index_history(index_name, start_date=None, end_date=None):
    """Fetch historical data for an NSE index.

    Args:
        index_name: Index name (e.g., "NIFTY 50").
        start_date: Start date (default: 1 year ago).
        end_date: End date (default: today).

    Returns:
        DataFrame with columns: Date, Open, High, Low, Close.
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=365)

    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

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
                return df
    except Exception:
        pass

    # yfinance fallback for indices
    yf_map = {
        "NIFTY 50": "^NSEI",
        "NIFTY BANK": "^NSEBANK",
        "INDIA VIX": "^INDIAVIX",
        "NIFTY IT": "^CNXIT",
        "NIFTY NEXT 50": "^NSMIDCP",
    }
    yf_symbol = yf_map.get(index_name)
    if yf_symbol:
        try:
            import yfinance as yf
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(start=str(start_date), end=str(end_date))
            if df is not None and not df.empty:
                df = df.reset_index()
                df = df.rename(columns={"index": "Date"})
                if "Date" in df.columns:
                    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
                cols = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in df.columns]
                return df[cols]
        except Exception:
            pass

    return pd.DataFrame()
