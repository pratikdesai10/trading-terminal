"""Live NSE data fetching via jugaad-data and nsetools."""

import pandas as pd
import streamlit as st

from utils.logger import logger


@st.cache_data(ttl=60, show_spinner=False)
def get_stock_quote(symbol):
    """Get live quote for a single NSE stock."""
    logger.info(f"get_stock_quote | symbol={symbol} | trying jugaad-data")
    try:
        from jugaad_data.nse import NSELive
        nse = NSELive()
        data = nse.stock_quote(symbol)
        if data and "priceInfo" in data:
            price_info = data["priceInfo"]
            info = data.get("info", {})
            result = {
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
            logger.info(f"get_stock_quote | symbol={symbol} | OK via jugaad-data | ltp={result['lastPrice']}")
            return result
        else:
            logger.warning(f"get_stock_quote | symbol={symbol} | jugaad-data returned no priceInfo, keys={list(data.keys()) if data else 'None'}")
    except Exception as e:
        logger.warning(f"get_stock_quote | symbol={symbol} | jugaad-data failed: {type(e).__name__}: {e}")

    # Fallback: nsetools
    logger.info(f"get_stock_quote | symbol={symbol} | trying nsetools fallback")
    try:
        from nsetools import Nse
        nse = Nse()
        q = nse.get_quote(symbol)
        if q:
            result = {
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
            logger.info(f"get_stock_quote | symbol={symbol} | OK via nsetools | ltp={result['lastPrice']}")
            return result
        else:
            logger.warning(f"get_stock_quote | symbol={symbol} | nsetools returned None")
    except Exception as e:
        logger.warning(f"get_stock_quote | symbol={symbol} | nsetools failed: {type(e).__name__}: {e}")

    logger.error(f"get_stock_quote | symbol={symbol} | ALL SOURCES FAILED")
    return None


@st.cache_data(ttl=60, show_spinner=False)
def get_index_quote(index_name):
    """Get live quote for an NSE index."""
    logger.info(f"get_index_quote | index={index_name}")
    try:
        from jugaad_data.nse import NSELive
        nse = NSELive()
        data = nse.live_index(index_name)
        if data and "data" in data:
            # Find the index row — NSE uses "symbol" field, not "index"
            for item in data["data"]:
                if item.get("symbol") == index_name or item.get("identifier") == index_name:
                    # Advance/decline is at top level, not per-item
                    adv_data = data.get("advance", {})
                    result = {
                        "indexName": index_name,
                        "last": _safe_float(item.get("lastPrice", item.get("last", 0))),
                        "change": _safe_float(item.get("change", item.get("variation", 0))),
                        "pChange": _safe_float(item.get("pChange", item.get("percentChange", 0))),
                        "open": _safe_float(item.get("open", 0)),
                        "high": _safe_float(item.get("dayHigh", item.get("high", 0))),
                        "low": _safe_float(item.get("dayLow", item.get("low", 0))),
                        "previousClose": _safe_float(item.get("previousClose", 0)),
                        "advances": _safe_int(adv_data.get("advances", 0)),
                        "declines": _safe_int(adv_data.get("declines", 0)),
                        "unchanged": _safe_int(adv_data.get("unchanged", 0)),
                    }
                    logger.info(f"get_index_quote | index={index_name} | OK | last={result['last']} | chg={result['pChange']}%")
                    return result
            logger.warning(f"get_index_quote | index={index_name} | symbol not found in {len(data['data'])} items")
        else:
            logger.warning(f"get_index_quote | index={index_name} | no 'data' key in response")
    except Exception as e:
        logger.error(f"get_index_quote | index={index_name} | FAILED: {type(e).__name__}: {e}")
    return None


@st.cache_data(ttl=60, show_spinner=False)
def get_market_breadth():
    """Get market breadth (advances, declines, unchanged) for NIFTY 50."""
    logger.info("get_market_breadth | fetching NIFTY 50 breadth")
    try:
        from jugaad_data.nse import NSELive
        nse = NSELive()
        data = nse.live_index("NIFTY 50")
        if data and "advance" in data:
            adv = data["advance"]
            result = {
                "advances": _safe_int(adv.get("advances", 0)),
                "declines": _safe_int(adv.get("declines", 0)),
                "unchanged": _safe_int(adv.get("unchanged", 0)),
            }
            logger.info(f"get_market_breadth | OK | adv={result['advances']} dec={result['declines']} unc={result['unchanged']}")
            return result
    except Exception as e:
        logger.error(f"get_market_breadth | FAILED: {type(e).__name__}: {e}")

    # Fallback: try from index quote
    quote = get_index_quote("NIFTY 50")
    if quote:
        return {
            "advances": quote.get("advances", 0),
            "declines": quote.get("declines", 0),
            "unchanged": quote.get("unchanged", 0),
        }
    logger.warning("get_market_breadth | ALL SOURCES FAILED")
    return {"advances": 0, "declines": 0, "unchanged": 0}


@st.cache_data(ttl=60, show_spinner=False)
def get_top_gainers_losers(index_name="NIFTY 50", n=5):
    """Get top N gainers and losers from an index. Returns (gainers_df, losers_df)."""
    logger.info(f"get_top_gainers_losers | index={index_name} | n={n}")
    try:
        from jugaad_data.nse import NSELive
        nse = NSELive()
        data = nse.live_index(index_name)
        if data and "data" in data:
            records = []
            for item in data["data"]:
                sym = item.get("symbol", "")
                # Skip the index row itself
                if not sym or sym == index_name or sym.startswith("NIFTY"):
                    continue
                try:
                    records.append({
                        "Symbol": sym,
                        "LTP": _safe_float(item.get("lastPrice", 0)),
                        "Change": _safe_float(item.get("change", 0)),
                        "% Change": _safe_float(item.get("pChange", 0)),
                    })
                except (ValueError, TypeError):
                    continue

            if records:
                df = pd.DataFrame(records)
                df = df.sort_values("% Change", ascending=False)
                gainers = df.head(n).reset_index(drop=True)
                losers = df.tail(n).sort_values("% Change").reset_index(drop=True)
                logger.info(f"get_top_gainers_losers | {len(records)} stocks found")
                return gainers, losers
            else:
                logger.warning(f"get_top_gainers_losers | no stock records parsed")
        else:
            logger.warning(f"get_top_gainers_losers | no 'data' key in response")
    except Exception as e:
        logger.error(f"get_top_gainers_losers | FAILED: {type(e).__name__}: {e}")
    return pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_sectoral_indices():
    """Fetch sectoral index performance. Returns a DataFrame sorted by % Change."""
    from config import SECTORAL_INDICES
    logger.info(f"get_sectoral_indices | fetching {len(SECTORAL_INDICES)} indices")

    records = []
    failed = []
    for idx_name in SECTORAL_INDICES:
        quote = get_index_quote(idx_name)
        if quote:
            records.append({
                "Index": idx_name.replace("NIFTY ", ""),
                "Last": quote["last"],
                "Change": quote["change"],
                "% Change": quote["pChange"],
            })
        else:
            failed.append(idx_name)

    if failed:
        logger.warning(f"get_sectoral_indices | failed indices: {failed}")
    logger.info(f"get_sectoral_indices | {len(records)}/{len(SECTORAL_INDICES)} loaded")

    if records:
        df = pd.DataFrame(records)
        return df.sort_values("% Change", ascending=False).reset_index(drop=True)
    return pd.DataFrame()


def _safe_float(val, default=0.0):
    """Safely convert a value to float, handling commas and strings."""
    if val is None:
        return default
    try:
        if isinstance(val, str):
            val = val.replace(",", "").strip()
            if val == "" or val == "-":
                return default
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=0):
    """Safely convert a value to int."""
    try:
        return int(_safe_float(val, default))
    except (ValueError, TypeError):
        return default
