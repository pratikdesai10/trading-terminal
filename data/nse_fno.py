"""F&O data fetching — option chain, OI analysis via jugaad-data and nsepython."""

import pandas as pd
import streamlit as st

from utils.logger import logger


@st.cache_data(ttl=60, show_spinner=False)
def get_option_chain(symbol, expiry=None):
    """Fetch option chain for a symbol.

    Returns dict with keys: records (list of strike dicts), expiry_dates (list),
    underlying_value (float), selected_expiry (str).
    """
    logger.info(f"get_option_chain | symbol={symbol} | expiry={expiry}")

    # Primary: jugaad-data
    result = _fetch_jugaad(symbol)
    if result:
        # Filter by expiry if specified
        if expiry and result["records"]:
            result["records"] = [r for r in result["records"]
                                 if r.get("expiryDate") == expiry]
            result["selected_expiry"] = expiry
        elif result["expiry_dates"]:
            # Default to nearest expiry
            result["selected_expiry"] = result["expiry_dates"][0]
            result["records"] = [r for r in result["records"]
                                 if r.get("expiryDate") == result["expiry_dates"][0]]
        return result

    # Fallback: nsepython
    result = _fetch_nsepython(symbol, expiry)
    if result:
        return result

    logger.error(f"get_option_chain | symbol={symbol} | ALL SOURCES FAILED")
    return None


def _fetch_jugaad(symbol):
    """Fetch option chain via jugaad-data NSELive."""
    try:
        from jugaad_data.nse import NSELive
        nse = NSELive()

        # For indices, use index_option_chain; for stocks, use stock_quote
        if symbol in ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"):
            data = nse.index_option_chain(symbol)
        else:
            data = nse.equities_option_chain(symbol)

        if not data:
            logger.warning(f"_fetch_jugaad | {symbol} | empty response")
            return None

        all_records = data.get("records", {})

        underlying = all_records.get("underlyingValue", 0)
        expiry_dates = all_records.get("expiryDates", [])
        oc_data = all_records.get("data", [])

        if not oc_data:
            logger.warning(f"_fetch_jugaad | {symbol} | no option data in response")
            return None

        records = []
        for item in oc_data:
            strike = item.get("strikePrice", 0)
            ce = item.get("CE", {})
            pe = item.get("PE", {})

            # NSE response uses "expiryDate" (string) on each item
            # but sometimes has "expiryDates" (can be a list) — normalize to string
            item_expiry = item.get("expiryDate", "")
            if not item_expiry:
                raw = item.get("expiryDates", "")
                item_expiry = raw[0] if isinstance(raw, list) and raw else str(raw) if raw else ""

            records.append({
                "strikePrice": strike,
                "expiryDate": item_expiry,
                "CE_OI": ce.get("openInterest", 0),
                "CE_chgOI": ce.get("changeinOpenInterest", 0),
                "CE_volume": ce.get("totalTradedVolume", 0),
                "CE_IV": ce.get("impliedVolatility", 0),
                "CE_LTP": ce.get("lastPrice", 0),
                "CE_change": ce.get("change", 0),
                "PE_OI": pe.get("openInterest", 0),
                "PE_chgOI": pe.get("changeinOpenInterest", 0),
                "PE_volume": pe.get("totalTradedVolume", 0),
                "PE_IV": pe.get("impliedVolatility", 0),
                "PE_LTP": pe.get("lastPrice", 0),
                "PE_change": pe.get("change", 0),
            })

        logger.info(f"_fetch_jugaad | {symbol} | OK | {len(records)} strikes | "
                     f"underlying={underlying} | {len(expiry_dates)} expiries")
        return {
            "records": records,
            "expiry_dates": expiry_dates,
            "underlying_value": underlying,
            "selected_expiry": expiry_dates[0] if expiry_dates else "",
        }
    except Exception as e:
        logger.warning(f"_fetch_jugaad | {symbol} | {type(e).__name__}: {e}")
    return None


def _fetch_nsepython(symbol, expiry=None):
    """Fetch option chain via nsepython as fallback."""
    try:
        from nsepython import option_chain
        data = option_chain(symbol)

        if data is None or data.empty:
            logger.warning(f"_fetch_nsepython | {symbol} | empty DataFrame")
            return None

        # nsepython returns a DataFrame directly
        expiry_dates = sorted(data["Expiry Date"].unique().tolist()) if "Expiry Date" in data.columns else []

        if expiry:
            data = data[data["Expiry Date"] == expiry]
        elif expiry_dates:
            data = data[data["Expiry Date"] == expiry_dates[0]]

        records = []
        for _, row in data.iterrows():
            records.append({
                "strikePrice": row.get("Strike Price", 0),
                "expiryDate": row.get("Expiry Date", ""),
                "CE_OI": row.get("CALLS_OI", 0),
                "CE_chgOI": row.get("CALLS_Chng in OI", 0),
                "CE_volume": row.get("CALLS_Volume", 0),
                "CE_IV": row.get("CALLS_IV", 0),
                "CE_LTP": row.get("CALLS_LTP", 0),
                "CE_change": row.get("CALLS_Net Chng", 0),
                "PE_OI": row.get("PUTS_OI", 0),
                "PE_chgOI": row.get("PUTS_Chng in OI", 0),
                "PE_volume": row.get("PUTS_Volume", 0),
                "PE_IV": row.get("PUTS_IV", 0),
                "PE_LTP": row.get("PUTS_LTP", 0),
                "PE_change": row.get("PUTS_Net Chng", 0),
            })

        underlying = 0
        logger.info(f"_fetch_nsepython | {symbol} | OK | {len(records)} strikes")
        return {
            "records": records,
            "expiry_dates": expiry_dates,
            "underlying_value": underlying,
            "selected_expiry": expiry or (expiry_dates[0] if expiry_dates else ""),
        }
    except Exception as e:
        logger.warning(f"_fetch_nsepython | {symbol} | {type(e).__name__}: {e}")
    return None


def compute_pcr(records):
    """Compute Put-Call Ratio from option chain records."""
    total_ce_oi = sum(r.get("CE_OI", 0) for r in records)
    total_pe_oi = sum(r.get("PE_OI", 0) for r in records)
    total_ce_vol = sum(r.get("CE_volume", 0) for r in records)
    total_pe_vol = sum(r.get("PE_volume", 0) for r in records)

    pcr_oi = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
    pcr_vol = total_pe_vol / total_ce_vol if total_ce_vol > 0 else 0

    return {
        "pcr_oi": round(pcr_oi, 3),
        "pcr_vol": round(pcr_vol, 3),
        "total_ce_oi": total_ce_oi,
        "total_pe_oi": total_pe_oi,
    }


def compute_max_pain(records):
    """Calculate Max Pain strike — the strike where option writers lose the least."""
    strikes = sorted(set(r["strikePrice"] for r in records))
    if not strikes:
        return 0

    # Build OI by strike
    ce_oi = {}
    pe_oi = {}
    for r in records:
        s = r["strikePrice"]
        ce_oi[s] = r.get("CE_OI", 0)
        pe_oi[s] = r.get("PE_OI", 0)

    min_pain = float("inf")
    max_pain_strike = strikes[0]

    for target in strikes:
        total_pain = 0
        for s in strikes:
            # CE holders lose if target > strike (ITM calls)
            if target > s:
                total_pain += (target - s) * ce_oi.get(s, 0)
            # PE holders lose if target < strike (ITM puts)
            if target < s:
                total_pain += (s - target) * pe_oi.get(s, 0)

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = target

    return max_pain_strike
