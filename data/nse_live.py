"""Live NSE data fetching via jugaad-data and nsetools."""

import pandas as pd
import streamlit as st

from data.cache import ttl_cache


@st.cache_data(ttl=60, show_spinner=False)
def get_stock_quote(symbol):
    """Get live quote for a single NSE stock.

    Returns dict with keys: symbol, lastPrice, change, pChange, open, dayHigh,
    dayLow, previousClose, totalTradedVolume, yearHigh, yearLow, etc.
    """
    try:
        from jugaad_data.nse import NSELive
        nse = NSELive()
        data = nse.stock_quote(symbol)
        if data and "priceInfo" in data:
            price_info = data["priceInfo"]
            info = data.get("info", {})
            sec_info = data.get("securityInfo", {})
            return {
                "symbol": symbol,
                "companyName": info.get("compName", symbol),
                "lastPrice": price_info.get("lastPrice", 0),
                "change": price_info.get("change", 0),
                "pChange": price_info.get("pChange", 0),
                "open": price_info.get("open", 0),
                "dayHigh": price_info.get("intraDayHighLow", {}).get("max", 0),
                "dayLow": price_info.get("intraDayHighLow", {}).get("min", 0),
                "previousClose": price_info.get("previousClose", 0),
                "totalTradedVolume": data.get("preOpenMarket", {}).get("totalTradedVolume", 0),
                "yearHigh": price_info.get("weekHighLow", {}).get("max", 0),
                "yearLow": price_info.get("weekHighLow", {}).get("min", 0),
            }
    except Exception:
        pass

    # Fallback: nsetools
    try:
        from nsetools import Nse
        nse = Nse()
        q = nse.get_quote(symbol)
        if q:
            return {
                "symbol": symbol,
                "companyName": q.get("companyName", symbol),
                "lastPrice": q.get("lastPrice", 0),
                "change": q.get("change", 0),
                "pChange": q.get("pChange", 0),
                "open": q.get("open", 0),
                "dayHigh": q.get("dayHigh", 0),
                "dayLow": q.get("dayLow", 0),
                "previousClose": q.get("previousClose", 0),
                "totalTradedVolume": q.get("totalTradedVolume", 0),
                "yearHigh": q.get("high52", 0),
                "yearLow": q.get("low52", 0),
            }
    except Exception:
        pass

    return None


@st.cache_data(ttl=60, show_spinner=False)
def get_index_quote(index_name):
    """Get live quote for an NSE index.

    Returns dict with keys: indexName, last, change, pChange, open, high, low,
    previousClose, advances, declines, unchanged.
    """
    try:
        from jugaad_data.nse import NSELive
        nse = NSELive()
        data = nse.live_index(index_name)
        if data and "data" in data:
            for item in data["data"]:
                if item.get("index") == index_name:
                    return {
                        "indexName": index_name,
                        "last": float(item.get("last", 0)),
                        "change": float(item.get("variation", 0)),
                        "pChange": float(item.get("percentChange", 0)),
                        "open": float(item.get("open", 0)),
                        "high": float(item.get("high", 0)),
                        "low": float(item.get("low", 0)),
                        "previousClose": float(item.get("previousClose", 0)),
                        "advances": int(item.get("advances", 0)),
                        "declines": int(item.get("declines", 0)),
                        "unchanged": int(item.get("unchanged", 0)),
                    }
    except Exception:
        pass
    return None


@st.cache_data(ttl=60, show_spinner=False)
def get_all_indices():
    """Fetch all NSE index quotes. Returns a DataFrame."""
    try:
        from jugaad_data.nse import NSELive
        nse = NSELive()
        data = nse.live_index("NIFTY 50")
        if data and "data" in data:
            records = []
            for item in data["data"]:
                try:
                    records.append({
                        "Index": item.get("index", ""),
                        "Last": float(item.get("last", 0)),
                        "Change": float(item.get("variation", 0)),
                        "% Change": float(item.get("percentChange", 0)),
                        "Open": float(item.get("open", 0)),
                        "High": float(item.get("high", 0)),
                        "Low": float(item.get("low", 0)),
                        "Prev Close": float(item.get("previousClose", 0)),
                    })
                except (ValueError, TypeError):
                    continue
            if records:
                return pd.DataFrame(records)
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_market_breadth():
    """Get market breadth (advances, declines, unchanged) for NIFTY 50."""
    quote = get_index_quote("NIFTY 50")
    if quote:
        return {
            "advances": quote.get("advances", 0),
            "declines": quote.get("declines", 0),
            "unchanged": quote.get("unchanged", 0),
        }
    return {"advances": 0, "declines": 0, "unchanged": 0}


@st.cache_data(ttl=60, show_spinner=False)
def get_top_gainers_losers(index_name="NIFTY 50", n=5):
    """Get top N gainers and losers from an index. Returns (gainers_df, losers_df)."""
    try:
        from jugaad_data.nse import NSELive
        nse = NSELive()
        data = nse.live_index(index_name)
        if data and "data" in data:
            records = []
            for item in data["data"]:
                sym = item.get("symbol", "")
                if not sym or sym == index_name:
                    continue
                try:
                    records.append({
                        "Symbol": sym,
                        "LTP": float(item.get("lastPrice", str(item.get("last", "0"))).replace(",", "")),
                        "Change": float(item.get("change", str(item.get("variation", "0"))).replace(",", "")),
                        "% Change": float(item.get("pChange", str(item.get("percentChange", "0"))).replace(",", "")),
                    })
                except (ValueError, TypeError):
                    continue

            if records:
                df = pd.DataFrame(records)
                df = df.sort_values("% Change", ascending=False)
                gainers = df.head(n).reset_index(drop=True)
                losers = df.tail(n).sort_values("% Change").reset_index(drop=True)
                return gainers, losers
    except Exception:
        pass
    return pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_sectoral_indices():
    """Fetch sectoral index performance. Returns a DataFrame sorted by % Change."""
    from config import SECTORAL_INDICES

    records = []
    for idx_name in SECTORAL_INDICES:
        quote = get_index_quote(idx_name)
        if quote:
            records.append({
                "Index": idx_name.replace("NIFTY ", ""),
                "Last": quote["last"],
                "Change": quote["change"],
                "% Change": quote["pChange"],
            })
    if records:
        df = pd.DataFrame(records)
        return df.sort_values("% Change", ascending=False).reset_index(drop=True)
    return pd.DataFrame()
