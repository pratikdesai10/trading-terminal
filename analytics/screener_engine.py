"""Stock screener engine — filter Nifty 50 stocks by fundamentals."""

import pandas as pd
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


def run_screener(stocks_data, filters):
    """Apply filters to stock data and return matching results.

    Args:
        stocks_data: list of dicts with stock fundamentals
        filters: dict of filter criteria (key → (min, max) or value)

    Returns:
        Filtered and sorted DataFrame
    """
    if not stocks_data:
        return pd.DataFrame()

    df = pd.DataFrame(stocks_data)
    initial_count = len(df)
    logger.info(f"screener | starting with {initial_count} stocks, {len(filters)} filters")

    # Apply range filters
    for key, (lo, hi) in filters.items():
        if key not in df.columns:
            continue
        col = pd.to_numeric(df[key], errors="coerce")
        if lo is not None:
            df = df[col >= lo]
        if hi is not None:
            df = df[col <= hi]

    logger.info(f"screener | {len(df)}/{initial_count} stocks passed filters")
    return df.reset_index(drop=True)


def fetch_screener_data(symbols, sectors):
    """Fetch fundamental data for a list of symbols via yfinance (parallel).

    Returns list of dicts with key metrics.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_single(symbol):
        ticker = _yf.Ticker(f"{symbol}.NS", session=_SESSION)
        info = ticker.info or {}
        if not info.get("currentPrice") and not info.get("regularMarketPrice"):
            return None
        price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        return {
            "Symbol": symbol,
            "Sector": sectors.get(symbol, ""),
            "Price": price,
            "Mkt Cap (Cr)": round(info.get("marketCap", 0) / 1e7, 0),
            "P/E": round(info.get("trailingPE") or 0, 1),
            "P/B": round(info.get("priceToBook") or 0, 1),
            "ROE (%)": round((info.get("returnOnEquity") or 0) * 100, 1),
            "D/E": round(info.get("debtToEquity") or 0, 1),
            "Div Yield (%)": round((info.get("dividendYield") or 0) * 100, 2),
            "Rev Growth (%)": round((info.get("revenueGrowth") or 0) * 100, 1),
            "52W High": info.get("fiftyTwoWeekHigh", 0),
            "52W Low": info.get("fiftyTwoWeekLow", 0),
            "Beta": round(info.get("beta") or 0, 2),
            "EPS": round(info.get("trailingEps") or 0, 1),
        }

    records = []
    failed = []

    with ThreadPoolExecutor(max_workers=15) as executor:
        future_map = {executor.submit(_fetch_single, s): s for s in symbols}
        for future in as_completed(future_map):
            sym = future_map[future]
            try:
                result = future.result(timeout=15)
                if result:
                    records.append(result)
                else:
                    failed.append(sym)
            except Exception as e:
                logger.warning(f"screener_fetch | {sym} | {type(e).__name__}: {e}")
                failed.append(sym)

    if failed:
        logger.warning(f"screener_fetch | failed: {failed}")
    logger.info(f"screener_fetch | {len(records)}/{len(symbols)} loaded")
    return records
