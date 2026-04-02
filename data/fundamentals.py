"""yfinance wrapper for Indian stock fundamentals."""

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


@st.cache_data(ttl=86400, show_spinner=False)
def get_company_info(symbol):
    """Fetch company info via yfinance.

    Returns dict with company details, or None on failure.
    All numeric values are raw (not converted to Crores).
    """
    logger.info(f"get_company_info | symbol={symbol}")
    try:
        ticker = _yf.Ticker(f"{symbol}.NS", session=_SESSION)
        info = ticker.info
        if not info or not isinstance(info, dict) or len(info) < 5:
            logger.warning(f"get_company_info | symbol={symbol} | empty or minimal response, keys={len(info) if info else 0}")
            return None
        logger.info(f"get_company_info | symbol={symbol} | OK | name={info.get('longName', 'N/A')} | keys={len(info)}")
        return info
    except Exception as e:
        logger.error(f"get_company_info | symbol={symbol} | FAILED: {type(e).__name__}: {e}")
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def get_income_statement(symbol):
    """Fetch income statement (annual + quarterly).

    Returns {"annual": DataFrame, "quarterly": DataFrame} or None.
    """
    logger.info(f"get_income_statement | symbol={symbol}")
    try:
        ticker = _yf.Ticker(f"{symbol}.NS", session=_SESSION)
        annual = ticker.financials
        quarterly = ticker.quarterly_financials
        if annual is None or annual.empty:
            logger.warning(f"get_income_statement | symbol={symbol} | no annual data")
            return None
        q_shape = quarterly.shape if quarterly is not None and not quarterly.empty else "empty"
        logger.info(f"get_income_statement | symbol={symbol} | OK | annual={annual.shape} quarterly={q_shape}")
        return {
            "annual": annual,
            "quarterly": quarterly if quarterly is not None and not quarterly.empty else annual,
        }
    except Exception as e:
        logger.error(f"get_income_statement | symbol={symbol} | FAILED: {type(e).__name__}: {e}")
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def get_balance_sheet(symbol):
    """Fetch balance sheet (annual + quarterly).

    Returns {"annual": DataFrame, "quarterly": DataFrame} or None.
    """
    logger.info(f"get_balance_sheet | symbol={symbol}")
    try:
        ticker = _yf.Ticker(f"{symbol}.NS", session=_SESSION)
        annual = ticker.balance_sheet
        quarterly = ticker.quarterly_balance_sheet
        if annual is None or annual.empty:
            logger.warning(f"get_balance_sheet | symbol={symbol} | no annual data")
            return None
        logger.info(f"get_balance_sheet | symbol={symbol} | OK | annual={annual.shape}")
        return {
            "annual": annual,
            "quarterly": quarterly if quarterly is not None and not quarterly.empty else annual,
        }
    except Exception as e:
        logger.error(f"get_balance_sheet | symbol={symbol} | FAILED: {type(e).__name__}: {e}")
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def get_cashflow(symbol):
    """Fetch cash flow statement (annual + quarterly).

    Returns {"annual": DataFrame, "quarterly": DataFrame} or None.
    """
    logger.info(f"get_cashflow | symbol={symbol}")
    try:
        ticker = _yf.Ticker(f"{symbol}.NS", session=_SESSION)
        annual = ticker.cashflow
        quarterly = ticker.quarterly_cashflow
        if annual is None or annual.empty:
            logger.warning(f"get_cashflow | symbol={symbol} | no annual data")
            return None
        logger.info(f"get_cashflow | symbol={symbol} | OK | annual={annual.shape}")
        return {
            "annual": annual,
            "quarterly": quarterly if quarterly is not None and not quarterly.empty else annual,
        }
    except Exception as e:
        logger.error(f"get_cashflow | symbol={symbol} | FAILED: {type(e).__name__}: {e}")
        return None
