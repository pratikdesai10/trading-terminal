"""Nifty 500 symbol-to-sector mapping via NSE CSV + static fallback."""

import io

import pandas as pd
import streamlit as st

from utils.logger import logger

# NSE publishes official Nifty 500 constituents with Industry classification
_NSE_CSV_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"

# Map NSE "Industry" values to our terminal sector taxonomy
_INDUSTRY_TO_SECTOR = {
    # Financial
    "Financial Services": "Financial",
    "Banks": "Financial",
    "Insurance": "Financial",
    # IT
    "Information Technology": "IT",
    "IT - Software": "IT",
    "IT - Services": "IT",
    # Pharma / Healthcare
    "Pharmaceuticals": "Pharma",
    "Pharmaceuticals & Biotechnology": "Pharma",
    "Healthcare": "Healthcare",
    "Healthcare Services": "Healthcare",
    "Healthcare Equipment & Supplies": "Healthcare",
    # Auto
    "Automobile": "Auto",
    "Automobiles": "Auto",
    "Auto Components": "Auto",
    "Automobile and Auto Components": "Auto",
    # Energy
    "Oil Gas & Consumable Fuels": "Energy",
    "Oil, Gas & Consumable Fuels": "Energy",
    "Gas": "Energy",
    "Petroleum Products": "Energy",
    # FMCG
    "Fast Moving Consumer Goods": "FMCG",
    "FMCG": "FMCG",
    "Food Products": "FMCG",
    "Personal Products": "FMCG",
    "Household Products": "FMCG",
    "Tobacco Products": "FMCG",
    "Beverages": "FMCG",
    "Food, Beverages & Tobacco": "FMCG",
    # Metals & Mining
    "Metals & Mining": "Metals",
    "Metals": "Metals",
    "Steel": "Metals",
    "Non - Ferrous Metals": "Metals",
    "Ferrous Metals": "Metals",
    "Mining": "Mining",
    # Materials / Chemicals / Cement
    "Chemicals": "Chemicals",
    "Cement & Cement Products": "Materials",
    "Cement": "Materials",
    "Construction Materials": "Materials",
    "Forest Materials": "Materials",
    "Paper & Paper Products": "Materials",
    # Infrastructure / Construction / Capital Goods
    "Construction": "Infrastructure",
    "Capital Goods": "Infrastructure",
    "Industrial Manufacturing": "Infrastructure",
    "Industrial Conglomerates": "Conglomerate",
    "Diversified": "Conglomerate",
    # Power
    "Power": "Power",
    "Utilities": "Power",
    "Electric Utilities": "Power",
    # Telecom
    "Telecommunication": "Telecom",
    "Telecom - Services": "Telecom",
    "Telecommunication Services": "Telecom",
    # Consumer
    "Consumer Durables": "Consumer",
    "Consumer Services": "Consumer",
    "Textiles": "Consumer",
    "Apparel & Accessories": "Consumer",
    "Leisure Products": "Consumer",
    "Retailing": "Consumer",
    "Consumer Discretionary": "Consumer",
    # Realty
    "Realty": "Realty",
    "Real Estate": "Realty",
    "Real Estate Management & Development": "Realty",
    # Media
    "Media": "Media",
    "Media, Entertainment & Publication": "Media",
    "Entertainment": "Media",
    # Defence
    "Aerospace & Defense": "Defence",
    "Defence": "Defence",
    # Transport / Logistics
    "Services": "Infrastructure",
    "Transport Services": "Infrastructure",
    "Transport Infrastructure": "Infrastructure",
    "Commercial Services & Supplies": "Infrastructure",
    # Agri
    "Agricultural Food & other Products": "FMCG",
    "Fertilizers & Agrochemicals": "Chemicals",
    # Miscellaneous
    "Diversified Metals": "Metals",
}

_DEFAULT_SECTOR = "Other"


@st.cache_data(ttl=86400, show_spinner=False)
def get_nifty_500_map():
    """Fetch Nifty 500 symbol-to-sector mapping from NSE CSV.

    Returns dict of {symbol: sector}. Falls back to static data on failure.
    """
    try:
        import requests
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/csv",
        }
        resp = requests.get(_NSE_CSV_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))

        # NSE CSV has columns: Company Name, Industry, Symbol, Series, ISIN Code
        if "Symbol" not in df.columns or "Industry" not in df.columns:
            logger.warning(f"nifty500 | unexpected CSV columns: {list(df.columns)}")
            return _STATIC_NIFTY_500

        mapping = {}
        for _, row in df.iterrows():
            symbol = str(row["Symbol"]).strip()
            industry = str(row["Industry"]).strip()
            sector = _INDUSTRY_TO_SECTOR.get(industry, _DEFAULT_SECTOR)
            mapping[symbol] = sector

        if len(mapping) >= 400:  # sanity check
            logger.info(f"nifty500 | fetched {len(mapping)} stocks from NSE CSV")
            return mapping
        else:
            logger.warning(f"nifty500 | only {len(mapping)} stocks in CSV, using static fallback")
            return _STATIC_NIFTY_500

    except Exception as e:
        logger.warning(f"nifty500 | CSV fetch failed: {type(e).__name__}: {e} | using static fallback")
        return _STATIC_NIFTY_500


def get_nifty_500_symbols():
    """Return sorted list of Nifty 500 symbols."""
    return sorted(get_nifty_500_map().keys())


# ── Static fallback (subset — will be extended by NSE CSV at runtime) ──
# This ensures the app works offline. Contains the known Nifty 200 with sectors.
_STATIC_NIFTY_500 = {
    # Nifty 50 (with sectors from config.NIFTY_50)
    "ADANIENT": "Infrastructure", "ADANIPORTS": "Infrastructure",
    "APOLLOHOSP": "Healthcare", "ASIANPAINT": "Consumer",
    "AXISBANK": "Financial", "BAJAJ-AUTO": "Auto",
    "BAJAJFINSV": "Financial", "BAJFINANCE": "Financial",
    "BHARTIARTL": "Telecom", "BPCL": "Energy",
    "BRITANNIA": "FMCG", "CIPLA": "Pharma",
    "COALINDIA": "Mining", "DRREDDY": "Pharma",
    "EICHERMOT": "Auto", "GRASIM": "Materials",
    "HCLTECH": "IT", "HDFCBANK": "Financial",
    "HDFCLIFE": "Financial", "HEROMOTOCO": "Auto",
    "HINDALCO": "Metals", "HINDUNILVR": "FMCG",
    "ICICIBANK": "Financial", "INDUSINDBK": "Financial",
    "INFY": "IT", "ITC": "FMCG",
    "JSWSTEEL": "Metals", "KOTAKBANK": "Financial",
    "LT": "Infrastructure", "M&M": "Auto",
    "MARUTI": "Auto", "NESTLEIND": "FMCG",
    "NTPC": "Power", "ONGC": "Energy",
    "POWERGRID": "Power", "RELIANCE": "Energy",
    "SBILIFE": "Financial", "SBIN": "Financial",
    "SHRIRAMFIN": "Financial", "SUNPHARMA": "Pharma",
    "TATAMOTORS": "Auto", "TATASTEEL": "Metals",
    "TCS": "IT", "TECHM": "IT",
    "TITAN": "Consumer", "TRENT": "Consumer",
    "ULTRACEMCO": "Materials", "WIPRO": "IT",
    # Nifty Next 50
    "ABB": "Infrastructure", "ADANIENSOL": "Energy",
    "ADANIGREEN": "Energy", "ADANIPOWER": "Power",
    "ATGL": "Energy", "AMBUJACEM": "Materials",
    "DMART": "Consumer", "BAJAJHLDNG": "Financial",
    "BANKBARODA": "Financial", "BERGEPAINT": "Consumer",
    "BOSCHLTD": "Auto", "CANBK": "Financial",
    "CHOLAFIN": "Financial", "COLPAL": "FMCG",
    "DLF": "Realty", "DABUR": "FMCG",
    "DIVISLAB": "Pharma", "GAIL": "Energy",
    "GODREJCP": "FMCG", "HAVELLS": "Consumer",
    "HAL": "Defence", "ICICIPRULI": "Financial",
    "INDIGO": "Infrastructure", "IOC": "Energy",
    "IRCTC": "Consumer", "IRFC": "Financial",
    "JINDALSTEL": "Metals", "JIOFIN": "Financial",
    "LICI": "Financial", "LODHA": "Realty",
    "MARICO": "FMCG", "MOTHERSON": "Auto",
    "NHPC": "Power", "NAUKRI": "IT",
    "PIIND": "Chemicals", "PFC": "Financial",
    "PIDILITIND": "Chemicals", "PNB": "Financial",
    "RECLTD": "Financial", "SBICARD": "Financial",
    "SIEMENS": "Infrastructure", "SRF": "Chemicals",
    "TATAPOWER": "Power", "TORNTPHARM": "Pharma",
    "TVSMOTOR": "Auto", "UNIONBANK": "Financial",
    "UNITDSPR": "FMCG", "VBL": "FMCG",
    "VEDL": "Metals", "ZOMATO": "Consumer",
    # Nifty 200 extra
    "ACC": "Materials", "ALKEM": "Pharma",
    "APLAPOLLO": "Metals", "ASHOKLEY": "Auto",
    "ASTRAL": "Infrastructure", "ATUL": "Chemicals",
    "AUBANK": "Financial", "AUROPHARMA": "Pharma",
    "BALKRISIND": "Auto", "BANDHANBNK": "Financial",
    "BHARATFORG": "Auto", "BHEL": "Infrastructure",
    "BIOCON": "Pharma", "CANFINHOME": "Financial",
    "CGPOWER": "Infrastructure", "CHAMBLFERT": "Chemicals",
    "CONCOR": "Infrastructure", "COROMANDEL": "Chemicals",
    "CROMPTON": "Consumer", "CUB": "Financial",
    "CUMMINSIND": "Infrastructure", "DEEPAKNTR": "Chemicals",
    "DIXON": "Consumer", "ESCORTS": "Auto",
    "EXIDEIND": "Auto", "FEDERALBNK": "Financial",
    "FORTIS": "Healthcare", "GLENMARK": "Pharma",
    "GMRINFRA": "Infrastructure", "GNFC": "Chemicals",
    "GSPL": "Energy", "GUJGASLTD": "Energy",
    "HDFCAMC": "Financial", "HINDPETRO": "Energy",
    "HONAUT": "Chemicals", "IDFCFIRSTB": "Financial",
    "IEX": "Power", "INDUSTOWER": "Telecom",
    "IPCA": "Pharma", "JKCEMENT": "Materials",
    "JSWENERGY": "Power", "JUBLFOOD": "Consumer",
    "KPITTECH": "IT", "LAURUSLABS": "Pharma",
    "LICHSGFIN": "Financial", "LTTS": "IT",
    "LUPIN": "Pharma", "MANAPPURAM": "Financial",
    "MFSL": "Financial", "MGL": "Energy",
    "MPHASIS": "IT", "MUTHOOTFIN": "Financial",
    "NATIONALUM": "Metals", "NAVINFLUOR": "Chemicals",
    "NMDC": "Mining", "OBEROIRLTY": "Realty",
    "OFSS": "IT", "PAGEIND": "Consumer",
    "PERSISTENT": "IT", "PETRONET": "Energy",
    "POLYCAB": "Infrastructure", "PRESTIGE": "Realty",
    "PVRINOX": "Media", "RAMCOCEM": "Materials",
    "RBLBANK": "Financial", "SAIL": "Metals",
    "SHREECEM": "Materials", "STAR": "Media",
    "SUNDARMFIN": "Financial", "SUNTV": "Media",
    "SYNGENE": "Pharma", "TATACHEM": "Chemicals",
    "TATACOMM": "Telecom", "TATAELXSI": "IT",
    "THERMAX": "Infrastructure", "TORNTPOWER": "Power",
    "TRIDENT": "Consumer", "UBL": "FMCG",
    "UPL": "Chemicals", "VOLTAS": "Consumer",
    "ZEEL": "Media", "ZYDUSLIFE": "Pharma",
}
