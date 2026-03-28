"""Live NSE data fetching via jugaad-data and nsetools."""

import time

import pandas as pd
import streamlit as st

from utils.logger import logger


def _retry_call(func, *args, max_attempts=2, delay=0.3, label=""):
    """Retry an API call with backoff. Returns result or raises last exception."""
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args)
        except Exception as e:
            last_exc = e
            if attempt < max_attempts:
                logger.info(f"retry | {label} | attempt {attempt} failed: {type(e).__name__} | retrying")
                time.sleep(delay * attempt)
    raise last_exc


@st.cache_resource(ttl=1800)
def _get_nse_client():
    """Singleton NSELive client — reused across calls, refreshed every 30 min."""
    from jugaad_data.nse import NSELive
    return NSELive()


@st.cache_data(ttl=60, show_spinner=False)
def get_stock_quote(symbol):
    """Get live quote for a single NSE stock."""
    logger.info(f"get_stock_quote | symbol={symbol} | trying jugaad-data")
    try:
        nse = _get_nse_client()
        data = _retry_call(nse.stock_quote, symbol, label=f"stock_quote({symbol})")
        if data and "priceInfo" in data:
            price_info = data["priceInfo"]
            info = data.get("info", {})
            last_price = price_info.get("lastPrice", 0)
            prev_close = price_info.get("previousClose", 0)
            # After market hours NSE returns lastPrice=0; fall back to previousClose
            if not last_price and prev_close:
                last_price = prev_close
            result = {
                "symbol": symbol,
                "companyName": info.get("compName", symbol),
                "lastPrice": last_price,
                "change": price_info.get("change", 0),
                "pChange": price_info.get("pChange", 0),
                "open": price_info.get("open", 0),
                "dayHigh": price_info.get("intraDayHighLow", {}).get("max", 0),
                "dayLow": price_info.get("intraDayHighLow", {}).get("min", 0),
                "previousClose": prev_close,
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
            last_price = q.get("lastPrice", 0)
            prev_close = q.get("previousClose", 0)
            if not last_price and prev_close:
                last_price = prev_close
            result = {
                "symbol": symbol,
                "companyName": q.get("companyName", symbol),
                "lastPrice": last_price,
                "change": q.get("change", 0),
                "pChange": q.get("pChange", 0),
                "open": q.get("open", 0),
                "dayHigh": q.get("dayHigh", 0),
                "dayLow": q.get("dayLow", 0),
                "previousClose": prev_close,
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
        nse = _get_nse_client()
        data = _retry_call(nse.live_index, index_name, label=f"live_index({index_name})")
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
def get_market_breadth(index_name="NIFTY 500"):
    """Get market breadth (advances, declines, unchanged) for an index."""
    logger.info(f"get_market_breadth | fetching {index_name} breadth")
    try:
        nse = _get_nse_client()
        data = _retry_call(nse.live_index, index_name, label=f"breadth({index_name})")
        if data and "advance" in data:
            adv = data["advance"]
            result = {
                "advances": _safe_int(adv.get("advances", 0)),
                "declines": _safe_int(adv.get("declines", 0)),
                "unchanged": _safe_int(adv.get("unchanged", 0)),
            }
            logger.info(f"get_market_breadth | {index_name} | OK | adv={result['advances']} dec={result['declines']} unc={result['unchanged']}")
            return result
    except Exception as e:
        logger.error(f"get_market_breadth | {index_name} | FAILED: {type(e).__name__}: {e}")

    # Fallback: try NIFTY 50 if broader index failed
    if index_name != "NIFTY 50":
        logger.info(f"get_market_breadth | falling back to NIFTY 50")
        return get_market_breadth("NIFTY 50")

    logger.warning("get_market_breadth | ALL SOURCES FAILED")
    return {"advances": 0, "declines": 0, "unchanged": 0}


@st.cache_data(ttl=60, show_spinner=False)
def get_top_gainers_losers(index_name="NIFTY 50", n=5):
    """Get top N gainers and losers from an index. Returns (gainers_df, losers_df)."""
    logger.info(f"get_top_gainers_losers | index={index_name} | n={n}")
    try:
        nse = _get_nse_client()
        data = _retry_call(nse.live_index, index_name, label=f"gainers_losers({index_name})")
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
    """Fetch sectoral index performance in parallel. Returns a DataFrame sorted by % Change."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from config import SECTORAL_INDICES
    logger.info(f"get_sectoral_indices | fetching {len(SECTORAL_INDICES)} indices")

    records = []
    failed = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_idx = {
            executor.submit(get_index_quote, idx_name): idx_name
            for idx_name in SECTORAL_INDICES
        }
        for future in as_completed(future_to_idx):
            idx_name = future_to_idx[future]
            try:
                quote = future.result(timeout=10)
                if quote:
                    records.append({
                        "Index": idx_name.replace("NIFTY ", ""),
                        "Last": quote["last"],
                        "Change": quote["change"],
                        "% Change": quote["pChange"],
                    })
                else:
                    failed.append(idx_name)
            except Exception as e:
                logger.warning(f"get_sectoral_indices | {idx_name} | {type(e).__name__}: {e}")
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
