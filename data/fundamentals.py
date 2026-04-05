"""yfinance wrapper for Indian stock fundamentals."""

import time

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


def _is_rate_limit(exc):
    """Detect yfinance rate-limit errors by class name or message."""
    name = type(exc).__name__
    if name == "YFRateLimitError":
        return True
    msg = str(exc).lower()
    return "too many requests" in msg or "rate limit" in msg or "429" in msg


def _yf_call_with_backoff(fn, *, label, max_attempts=3, base_delay=1.5):
    """Run a yfinance call with exponential backoff on rate-limit errors.

    Yahoo aggressively rate-limits cloud egress IPs, so a short retry chain
    recovers from transient 429s without waiting on the 24h Streamlit cache.
    """
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt < max_attempts and _is_rate_limit(e):
                delay = base_delay * (2 ** (attempt - 1))
                logger.info(f"yf_backoff | {label} | rate-limited, retrying in {delay:.1f}s (attempt {attempt}/{max_attempts})")
                time.sleep(delay)
                continue
            raise
    raise last_exc  # pragma: no cover — loop above always raises


@st.cache_data(ttl=86400, show_spinner=False)
def get_company_info(symbol):
    """Fetch company info via yfinance.

    Returns a dict of company details. Raises RuntimeError on failure so the
    Streamlit cache does not memoize a None result (which would hide the
    symbol for the full 24-hour TTL after a single rate-limit hit).
    All numeric values are raw (not converted to Crores).
    """
    logger.info(f"get_company_info | symbol={symbol}")
    try:
        ticker = _yf.Ticker(f"{symbol}.NS", session=_SESSION)
        info = _yf_call_with_backoff(lambda: ticker.info, label=f"company_info({symbol})")
    except Exception as e:
        logger.error(f"get_company_info | symbol={symbol} | FAILED: {type(e).__name__}: {e}")
        raise RuntimeError(f"get_company_info failed for {symbol}: {e}") from e
    if not info or not isinstance(info, dict) or len(info) < 5:
        keys = len(info) if info else 0
        logger.warning(f"get_company_info | symbol={symbol} | empty or minimal response, keys={keys}")
        raise RuntimeError(f"get_company_info empty response for {symbol} (keys={keys})")
    logger.info(f"get_company_info | symbol={symbol} | OK | name={info.get('longName', 'N/A')} | keys={len(info)}")
    return info


@st.cache_data(ttl=86400, show_spinner=False)
def get_income_statement(symbol):
    """Fetch income statement (annual + quarterly).

    Returns {"annual": DataFrame, "quarterly": DataFrame}. Raises RuntimeError
    on failure so the Streamlit cache does not memoize a None result.
    """
    logger.info(f"get_income_statement | symbol={symbol}")
    try:
        ticker = _yf.Ticker(f"{symbol}.NS", session=_SESSION)
        annual = _yf_call_with_backoff(lambda: ticker.financials, label=f"income_annual({symbol})")
        quarterly = _yf_call_with_backoff(lambda: ticker.quarterly_financials, label=f"income_quarterly({symbol})")
    except Exception as e:
        logger.error(f"get_income_statement | symbol={symbol} | FAILED: {type(e).__name__}: {e}")
        raise RuntimeError(f"get_income_statement failed for {symbol}: {e}") from e
    if annual is None or annual.empty:
        logger.warning(f"get_income_statement | symbol={symbol} | no annual data")
        raise RuntimeError(f"get_income_statement no annual data for {symbol}")
    q_shape = quarterly.shape if quarterly is not None and not quarterly.empty else "empty"
    logger.info(f"get_income_statement | symbol={symbol} | OK | annual={annual.shape} quarterly={q_shape}")
    return {
        "annual": annual,
        "quarterly": quarterly if quarterly is not None and not quarterly.empty else annual,
    }


@st.cache_data(ttl=86400, show_spinner=False)
def get_balance_sheet(symbol):
    """Fetch balance sheet (annual + quarterly).

    Returns {"annual": DataFrame, "quarterly": DataFrame}. Raises RuntimeError
    on failure so the Streamlit cache does not memoize a None result.
    """
    logger.info(f"get_balance_sheet | symbol={symbol}")
    try:
        ticker = _yf.Ticker(f"{symbol}.NS", session=_SESSION)
        annual = _yf_call_with_backoff(lambda: ticker.balance_sheet, label=f"balance_annual({symbol})")
        quarterly = _yf_call_with_backoff(lambda: ticker.quarterly_balance_sheet, label=f"balance_quarterly({symbol})")
    except Exception as e:
        logger.error(f"get_balance_sheet | symbol={symbol} | FAILED: {type(e).__name__}: {e}")
        raise RuntimeError(f"get_balance_sheet failed for {symbol}: {e}") from e
    if annual is None or annual.empty:
        logger.warning(f"get_balance_sheet | symbol={symbol} | no annual data")
        raise RuntimeError(f"get_balance_sheet no annual data for {symbol}")
    logger.info(f"get_balance_sheet | symbol={symbol} | OK | annual={annual.shape}")
    return {
        "annual": annual,
        "quarterly": quarterly if quarterly is not None and not quarterly.empty else annual,
    }


@st.cache_data(ttl=86400, show_spinner=False)
def get_cashflow(symbol):
    """Fetch cash flow statement (annual + quarterly).

    Returns {"annual": DataFrame, "quarterly": DataFrame}. Raises RuntimeError
    on failure so the Streamlit cache does not memoize a None result.
    """
    logger.info(f"get_cashflow | symbol={symbol}")
    try:
        ticker = _yf.Ticker(f"{symbol}.NS", session=_SESSION)
        annual = _yf_call_with_backoff(lambda: ticker.cashflow, label=f"cashflow_annual({symbol})")
        quarterly = _yf_call_with_backoff(lambda: ticker.quarterly_cashflow, label=f"cashflow_quarterly({symbol})")
    except Exception as e:
        logger.error(f"get_cashflow | symbol={symbol} | FAILED: {type(e).__name__}: {e}")
        raise RuntimeError(f"get_cashflow failed for {symbol}: {e}") from e
    if annual is None or annual.empty:
        logger.warning(f"get_cashflow | symbol={symbol} | no annual data")
        raise RuntimeError(f"get_cashflow no annual data for {symbol}")
    logger.info(f"get_cashflow | symbol={symbol} | OK | annual={annual.shape}")
    return {
        "annual": annual,
        "quarterly": quarterly if quarterly is not None and not quarterly.empty else annual,
    }
