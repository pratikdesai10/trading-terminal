"""Live NSE data fetching.

Uses a direct curl_cffi browser-impersonating HTTP client as the primary
source (browser impersonation + cookie priming is required because NSE
returns an HTML error page to naive User-Agents, which downstream callers
then hit as ``JSONDecodeError: Expecting value: line 1 column 1``).
Falls back to ``jugaad-data`` and ``nsetools`` when the direct client fails.
"""

import time
from urllib.parse import quote as _urlquote

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


# ─────────────────────────────────────────────────────────────────────
# Direct NSE HTTP client (primary source)
# ─────────────────────────────────────────────────────────────────────

_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nseindia.com/",
    "X-Requested-With": "XMLHttpRequest",
}


@st.cache_resource(ttl=900)
def _get_nse_http_session():
    """Browser-impersonating session with NSE cookies primed. Refreshed every 15 min."""
    try:
        from curl_cffi import requests as _curl_req
        s = _curl_req.Session(impersonate="chrome")
    except Exception:
        import requests as _requests
        s = _requests.Session()
    s.headers.update(_NSE_HEADERS)
    # Prime cookies from the public pages
    try:
        s.get("https://www.nseindia.com/", timeout=15)
        s.get("https://www.nseindia.com/market-data/live-equity-market", timeout=15)
    except Exception as e:
        logger.warning(f"nse_http | cookie priming failed: {type(e).__name__}: {e}")
    return s


def _reprime_nse_session(session):
    """Re-fetch NSE homepage to refresh cookies on 401/403."""
    try:
        session.get("https://www.nseindia.com/", timeout=15)
    except Exception as e:
        logger.warning(f"nse_http | re-prime failed: {type(e).__name__}: {e}")


def _nse_api_get(path, label=""):
    """GET a JSON endpoint on nseindia.com with one 403-retry after re-priming."""
    session = _get_nse_http_session()
    url = f"https://www.nseindia.com{path}"
    try:
        r = session.get(url, timeout=15)
    except Exception as e:
        raise RuntimeError(f"{label}: request error {type(e).__name__}: {e}") from e

    if r.status_code in (401, 403):
        _reprime_nse_session(session)
        try:
            r = session.get(url, timeout=15)
        except Exception as e:
            raise RuntimeError(f"{label}: retry error {type(e).__name__}: {e}") from e

    if r.status_code != 200:
        raise RuntimeError(f"{label}: HTTP {r.status_code}")

    # Sanity check: NSE returns HTML when blocked; fail fast with a clear message
    ct = (r.headers.get("content-type") or "").lower()
    text = r.text
    if "application/json" not in ct and not text.lstrip().startswith(("{", "[")):
        raise RuntimeError(f"{label}: non-JSON response (likely blocked)")
    try:
        return r.json()
    except Exception as e:
        raise RuntimeError(f"{label}: JSON parse error {type(e).__name__}: {e}") from e


def _nse_fetch_equity_quote(symbol):
    """Fetch a stock quote directly from NSE's quote-equity endpoint."""
    path = f"/api/quote-equity?symbol={_urlquote(symbol)}"
    return _nse_api_get(path, label=f"quote-equity({symbol})")


def _nse_fetch_index(index_name):
    """Fetch an index + its constituents from NSE's equity-stockIndices endpoint."""
    path = f"/api/equity-stockIndices?index={_urlquote(index_name)}"
    return _nse_api_get(path, label=f"equity-stockIndices({index_name})")


def _shape_stock_quote(symbol, data):
    """Shape a quote-equity payload (from direct NSE or jugaad) into the result dict."""
    price_info = data.get("priceInfo") or {}
    info = data.get("info") or {}
    last_price = _safe_float(price_info.get("lastPrice", 0))
    prev_close = _safe_float(price_info.get("previousClose", 0))
    # After market hours NSE returns lastPrice=0; fall back to previousClose
    if not last_price and prev_close:
        last_price = prev_close
    intra = price_info.get("intraDayHighLow") or {}
    week = price_info.get("weekHighLow") or {}
    preopen = data.get("preOpenMarket") or {}
    return {
        "symbol": symbol,
        "companyName": info.get("compName", symbol),
        "lastPrice": last_price,
        "change": _safe_float(price_info.get("change", 0)),
        "pChange": _safe_float(price_info.get("pChange", 0)),
        "open": _safe_float(price_info.get("open", 0)),
        "dayHigh": _safe_float(intra.get("max", 0)),
        "dayLow": _safe_float(intra.get("min", 0)),
        "previousClose": prev_close,
        "totalTradedVolume": _safe_int(preopen.get("totalTradedVolume", 0)),
        "yearHigh": _safe_float(week.get("max", 0)),
        "yearLow": _safe_float(week.get("min", 0)),
    }


@st.cache_data(ttl=60, show_spinner=False)
def get_stock_quote(symbol):
    """Get live quote for a single NSE stock.

    Tries the direct NSE HTTP client first (most reliable on cloud egress IPs
    because it uses browser impersonation and cookie priming), then falls back
    to jugaad-data and finally nsetools.
    """
    # ── Primary: direct NSE API ──
    logger.info(f"get_stock_quote | symbol={symbol} | trying nse-direct")
    try:
        data = _nse_fetch_equity_quote(symbol)
        if data and "priceInfo" in data:
            result = _shape_stock_quote(symbol, data)
            logger.info(f"get_stock_quote | symbol={symbol} | OK via nse-direct | ltp={result['lastPrice']}")
            return result
        logger.warning(f"get_stock_quote | symbol={symbol} | nse-direct no priceInfo")
    except Exception as e:
        logger.warning(f"get_stock_quote | symbol={symbol} | nse-direct failed: {type(e).__name__}: {e}")

    # ── Fallback 1: jugaad-data ──
    logger.info(f"get_stock_quote | symbol={symbol} | trying jugaad-data")
    try:
        nse = _get_nse_client()
        data = _retry_call(nse.stock_quote, symbol, label=f"stock_quote({symbol})")
        if data and "priceInfo" in data:
            result = _shape_stock_quote(symbol, data)
            logger.info(f"get_stock_quote | symbol={symbol} | OK via jugaad-data | ltp={result['lastPrice']}")
            return result
        logger.warning(f"get_stock_quote | symbol={symbol} | jugaad-data returned no priceInfo")
    except Exception as e:
        logger.warning(f"get_stock_quote | symbol={symbol} | jugaad-data failed: {type(e).__name__}: {e}")

    # ── Fallback 2: nsetools ──
    logger.info(f"get_stock_quote | symbol={symbol} | trying nsetools fallback")
    try:
        from nsetools import Nse
        nse = Nse()
        q = nse.get_quote(symbol)
        if q:
            last_price = _safe_float(q.get("lastPrice", 0))
            prev_close = _safe_float(q.get("previousClose", 0))
            if not last_price and prev_close:
                last_price = prev_close
            result = {
                "symbol": symbol,
                "companyName": q.get("companyName", symbol),
                "lastPrice": last_price,
                "change": _safe_float(q.get("change", 0)),
                "pChange": _safe_float(q.get("pChange", 0)),
                "open": _safe_float(q.get("open", 0)),
                "dayHigh": _safe_float(q.get("dayHigh", 0)),
                "dayLow": _safe_float(q.get("dayLow", 0)),
                "previousClose": prev_close,
                "totalTradedVolume": _safe_int(q.get("totalTradedVolume", 0)),
                "yearHigh": _safe_float(q.get("high52", 0)),
                "yearLow": _safe_float(q.get("low52", 0)),
            }
            logger.info(f"get_stock_quote | symbol={symbol} | OK via nsetools | ltp={result['lastPrice']}")
            return result
        logger.warning(f"get_stock_quote | symbol={symbol} | nsetools returned None")
    except Exception as e:
        logger.warning(f"get_stock_quote | symbol={symbol} | nsetools failed: {type(e).__name__}: {e}")

    logger.error(f"get_stock_quote | symbol={symbol} | ALL SOURCES FAILED")
    return None


def _shape_index_row(index_name, data):
    """Given a live-index payload, locate the index row and shape the result dict.

    Matching strategy:
    1. Case-insensitive match on `symbol` / `identifier` / `index` / `indexSymbol`.
    2. If no match, fall back to `data[0]` — on NSE's equity-stockIndices
       endpoint the first row is always the index itself, even when its symbol
       field uses a slightly different string than the query parameter.
    """
    rows = data.get("data", []) or []
    target = (index_name or "").strip().lower()
    match = None
    for item in rows:
        for key in ("symbol", "identifier", "index", "indexSymbol"):
            val = item.get(key)
            if isinstance(val, str) and val.strip().lower() == target:
                match = item
                break
        if match is not None:
            break

    if match is None and rows:
        # Fallback: first row is the index summary on equity-stockIndices
        first = rows[0]
        logger.info(
            f"_shape_index_row | {index_name} | no exact match, using data[0] "
            f"keys={list(first.keys())[:12]}"
        )
        match = first

    if match is None:
        logger.warning(f"_shape_index_row | {index_name} | empty data[] payload")
        return None

    adv_data = data.get("advance") or {}
    return {
        "indexName": index_name,
        "last": _safe_float(
            match.get("last", match.get("lastPrice", match.get("last_price", match.get("value", 0))))
        ),
        "change": _safe_float(match.get("change", match.get("variation", 0))),
        "pChange": _safe_float(
            match.get("pChange", match.get("percentChange", match.get("percChange", 0)))
        ),
        "open": _safe_float(match.get("open", 0)),
        "high": _safe_float(match.get("dayHigh", match.get("high", 0))),
        "low": _safe_float(match.get("dayLow", match.get("low", 0))),
        "previousClose": _safe_float(match.get("previousClose", match.get("prevClose", 0))),
        "advances": _safe_int(adv_data.get("advances", 0)),
        "declines": _safe_int(adv_data.get("declines", 0)),
        "unchanged": _safe_int(adv_data.get("unchanged", 0)),
    }


def _fetch_vix_via_all_indices():
    """Fetch INDIA VIX from NSE's /api/allIndices endpoint.

    /api/equity-stockIndices only supports indices with constituents, so VIX
    (which has none) must come from the list-all endpoint. We normalize the
    response into the same {"data": [...]} shape that `_shape_index_row`
    expects so downstream logic is unchanged.
    """
    raw = _nse_api_get("/api/allIndices", label="allIndices(VIX)")
    all_rows = raw.get("data", []) or []
    vix_row = None
    for item in all_rows:
        key_val = (
            item.get("index") or item.get("indexSymbol") or item.get("symbol") or ""
        ).strip().lower()
        if key_val == "india vix":
            vix_row = item
            break
    if vix_row is None:
        raise RuntimeError("allIndices: INDIA VIX row not found")
    return {"data": [vix_row], "advance": {}}


def _fetch_live_index(index_name):
    """Fetch a live index payload, trying direct NSE first then jugaad-data."""
    # VIX has no constituents — equity-stockIndices 400s on it, so route
    # through allIndices instead.
    if (index_name or "").strip().upper() == "INDIA VIX":
        try:
            return _fetch_vix_via_all_indices()
        except Exception as e:
            logger.warning(f"live_index | INDIA VIX | allIndices failed: {type(e).__name__}: {e}")
            # fall through to jugaad-data fallback

    # Primary: direct NSE
    try:
        return _nse_fetch_index(index_name)
    except Exception as e:
        logger.warning(f"live_index | {index_name} | nse-direct failed: {type(e).__name__}: {e}")
    # Fallback: jugaad-data
    nse = _get_nse_client()
    return _retry_call(nse.live_index, index_name, label=f"live_index({index_name})")


@st.cache_data(ttl=60, show_spinner=False)
def get_index_quote(index_name):
    """Get live quote for an NSE index."""
    logger.info(f"get_index_quote | index={index_name}")
    try:
        data = _fetch_live_index(index_name)
    except Exception as e:
        logger.error(f"get_index_quote | index={index_name} | FAILED: {type(e).__name__}: {e}")
        return None

    if not data or "data" not in data:
        logger.warning(f"get_index_quote | index={index_name} | no 'data' key in response")
        return None

    result = _shape_index_row(index_name, data)
    if result is None:
        logger.warning(f"get_index_quote | index={index_name} | symbol not found in {len(data['data'])} items")
        return None

    logger.info(f"get_index_quote | index={index_name} | OK | last={result['last']} | chg={result['pChange']}%")
    return result


@st.cache_data(ttl=60, show_spinner=False)
def get_market_breadth(index_name="NIFTY 500"):
    """Get market breadth (advances, declines, unchanged) for an index.

    Reads the top-level ``advance`` block when NSE provides it; otherwise
    computes breadth manually by counting constituent rows by sign of
    ``pChange``. This protects against NSE schema drift where the summary
    block is missing or zeroed.
    """
    logger.info(f"get_market_breadth | fetching {index_name} breadth")
    data = None
    try:
        data = _fetch_live_index(index_name)
    except Exception as e:
        logger.error(f"get_market_breadth | {index_name} | FAILED: {type(e).__name__}: {e}")

    if data:
        adv = data.get("advance") or {}
        result = {
            "advances": _safe_int(adv.get("advances", 0)),
            "declines": _safe_int(adv.get("declines", 0)),
            "unchanged": _safe_int(adv.get("unchanged", 0)),
        }
        total = result["advances"] + result["declines"] + result["unchanged"]
        if total > 0:
            logger.info(
                f"get_market_breadth | {index_name} | OK via summary | "
                f"adv={result['advances']} dec={result['declines']} unc={result['unchanged']}"
            )
            return result

        # Summary missing or zeroed — compute manually from constituents.
        rows = data.get("data", []) or []
        manual = {"advances": 0, "declines": 0, "unchanged": 0}
        target_lower = (index_name or "").strip().lower()
        for item in rows:
            sym = (item.get("symbol") or "").strip()
            if sym.lower() == target_lower:
                # Skip the index summary row itself
                continue
            pchg = item.get("pChange")
            if pchg is None:
                pchg = item.get("percentChange", 0)
            try:
                pchg_val = float(pchg)
            except (ValueError, TypeError):
                continue
            if pchg_val > 0:
                manual["advances"] += 1
            elif pchg_val < 0:
                manual["declines"] += 1
            else:
                manual["unchanged"] += 1
        if sum(manual.values()) > 0:
            logger.info(
                f"get_market_breadth | {index_name} | OK via manual count | "
                f"adv={manual['advances']} dec={manual['declines']} unc={manual['unchanged']}"
            )
            return manual

    # Fallback: try NIFTY 50 if broader index failed
    if index_name != "NIFTY 50":
        logger.info("get_market_breadth | falling back to NIFTY 50")
        return get_market_breadth("NIFTY 50")

    logger.warning("get_market_breadth | ALL SOURCES FAILED")
    return {"advances": 0, "declines": 0, "unchanged": 0}


@st.cache_data(ttl=60, show_spinner=False)
def get_top_gainers_losers(index_name="NIFTY 50", n=5):
    """Get top N gainers and losers from an index. Returns (gainers_df, losers_df)."""
    logger.info(f"get_top_gainers_losers | index={index_name} | n={n}")
    try:
        data = _fetch_live_index(index_name)
    except Exception as e:
        logger.error(f"get_top_gainers_losers | FAILED: {type(e).__name__}: {e}")
        return pd.DataFrame(), pd.DataFrame()

    if not data or "data" not in data:
        logger.warning("get_top_gainers_losers | no 'data' key in response")
        return pd.DataFrame(), pd.DataFrame()

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

    if not records:
        logger.warning("get_top_gainers_losers | no stock records parsed")
        return pd.DataFrame(), pd.DataFrame()

    df = pd.DataFrame(records)
    df = df.sort_values("% Change", ascending=False)
    gainers = df.head(n).reset_index(drop=True)
    losers = df.tail(n).sort_values("% Change").reset_index(drop=True)
    logger.info(f"get_top_gainers_losers | {len(records)} stocks found")
    return gainers, losers


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
