"""Configuration constants for the Indian Bloomberg Terminal."""

# ── Color Palette (Bloomberg-style) ──
COLORS = {
    "bg": "#0A0A0A",
    "panel": "#1A1A1A",
    "border": "#333333",
    "text": "#E0E0E0",
    "amber": "#FF9900",
    "green": "#00CC66",
    "red": "#FF3333",
    "blue": "#3399FF",
    "muted": "#888888",
}

# ── Plotly dark chart template ──
PLOTLY_LAYOUT = dict(
    paper_bgcolor=COLORS["bg"],
    plot_bgcolor=COLORS["bg"],
    font=dict(family="Fira Code, Consolas, Courier New, monospace", color=COLORS["text"], size=12),
    xaxis=dict(gridcolor="#1A1A1A", zerolinecolor="#333333"),
    yaxis=dict(gridcolor="#1A1A1A", zerolinecolor="#333333"),
    margin=dict(l=40, r=20, t=40, b=30),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
)


def plotly_layout(**overrides):
    """Return PLOTLY_LAYOUT deep-merged with overrides (overrides win on conflict)."""
    import copy
    base = copy.deepcopy(dict(PLOTLY_LAYOUT))
    for key, val in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            base[key] = {**base[key], **val}
        else:
            base[key] = val
    return base

# ── Market hours (IST) ──
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MIN = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MIN = 30

# ── Nifty 50 Stocks & Sector Mapping ──
NIFTY_50 = {
    "ADANIENT": "Conglomerate",
    "ADANIPORTS": "Infrastructure",
    "APOLLOHOSP": "Healthcare",
    "ASIANPAINT": "Consumer",
    "AXISBANK": "Financial",
    "BAJAJ-AUTO": "Auto",
    "BAJFINANCE": "Financial",
    "BAJAJFINSV": "Financial",
    "BEL": "Defence",
    "BPCL": "Energy",
    "BHARTIARTL": "Telecom",
    "BRITANNIA": "FMCG",
    "CIPLA": "Pharma",
    "COALINDIA": "Mining",
    "DRREDDY": "Pharma",
    "EICHERMOT": "Auto",
    "ETERNAL": "Consumer",
    "GRASIM": "Materials",
    "HCLTECH": "IT",
    "HDFCBANK": "Financial",
    "HDFCLIFE": "Financial",
    "HEROMOTOCO": "Auto",
    "HINDALCO": "Metals",
    "HINDUNILVR": "FMCG",
    "ICICIBANK": "Financial",
    "INDUSINDBK": "Financial",
    "INFY": "IT",
    "ITC": "FMCG",
    "JSWSTEEL": "Metals",
    "KOTAKBANK": "Financial",
    "LT": "Infrastructure",
    "M&M": "Auto",
    "MARUTI": "Auto",
    "NESTLEIND": "FMCG",
    "NTPC": "Power",
    "ONGC": "Energy",
    "POWERGRID": "Power",
    "RELIANCE": "Energy",
    "SBILIFE": "Financial",
    "SBIN": "Financial",
    "SHRIRAMFIN": "Financial",
    "SUNPHARMA": "Pharma",
    "TATACONSUM": "FMCG",
    "TATAMOTORS": "Auto",
    "TATASTEEL": "Metals",
    "TCS": "IT",
    "TECHM": "IT",
    "TITAN": "Consumer",
    "TRENT": "Consumer",
    "ULTRACEMCO": "Materials",
    "WIPRO": "IT",
}

NIFTY_50_SYMBOLS = list(NIFTY_50.keys())

# ── Nifty Next 50 (additional stocks beyond Nifty 50) ──
NIFTY_NEXT_50 = [
    "ABB", "ADANIENSOL", "ADANIGREEN", "ADANIPOWER", "ATGL",
    "AMBUJACEM", "DMART", "BAJAJHLDNG", "BANKBARODA", "BERGEPAINT",
    "BOSCHLTD", "CANBK", "CHOLAFIN", "COLPAL", "DLF",
    "DABUR", "DIVISLAB", "GAIL", "GODREJCP", "HAVELLS",
    "HAL", "ICICIPRULI", "INDIGO", "IOC", "IRCTC",
    "IRFC", "JINDALSTEL", "JIOFIN", "LICI", "LODHA",
    "MARICO", "MOTHERSON", "NHPC", "NAUKRI", "PIIND",
    "PFC", "PIDILITIND", "PNB", "RECLTD", "SBICARD",
    "SIEMENS", "SRF", "TATAPOWER", "TORNTPHARM", "TVSMOTOR",
    "UNIONBANK", "UNITDSPR", "VBL", "VEDL", "ZOMATO",
]

NIFTY_100_SYMBOLS = NIFTY_50_SYMBOLS + NIFTY_NEXT_50

# ── Nifty 200 additional symbols ──
NIFTY_200_EXTRA = [
    "ACC", "ALKEM", "APLAPOLLO", "ASHOKLEY", "ASTRAL",
    "ATUL", "AUBANK", "AUROPHARMA", "BALKRISIND", "BANDHANBNK",
    "BHARATFORG", "BHEL", "BIOCON", "CANFINHOME", "CGPOWER",
    "CHAMBLFERT", "CONCOR", "COROMANDEL", "CROMPTON", "CUB",
    "CUMMINSIND", "DEEPAKNTR", "DELTACORP", "DIXON", "ESCORTS",
    "EXIDEIND", "FEDERALBNK", "FORTIS", "GLENMARK", "GMRINFRA",
    "GNFC", "GSPL", "GUJGASLTD", "HDFCAMC", "HINDPETRO",
    "HONAUT", "IDFCFIRSTB", "IEX", "IIFL", "INDUSTOWER",
    "IPCA", "JKCEMENT", "JSWENERGY", "JUBLFOOD", "KPITTECH",
    "L&TFH", "LAURUSLABS", "LICHSGFIN", "LTTS", "LUPIN",
    "M&MFIN", "MANAPPURAM", "MFSL", "MGL", "MINDTREE",
    "MPHASIS", "MUTHOOTFIN", "NAM-INDIA", "NATIONALUM", "NAVINFLUOR",
    "NMDC", "OBEROIRLTY", "OFSS", "PAGEIND", "PERSISTENT",
    "PETRONET", "POLYCAB", "PRESTIGE", "PVRINOX", "RAJESHEXPO",
    "RAMCOCEM", "RBLBANK", "SAIL", "SBILIFE", "SHREECEM",
    "SONACOMS", "STAR", "SUNDARMFIN", "SUNPHARMA", "SUNTV",
    "SYNGENE", "TATACHEM", "TATACOMM", "TATAELXSI", "TECHM",
    "THERMAX", "TITAN", "TORNTPOWER", "TRENT", "TRIDENT",
    "UBL", "ULTRACEMCO", "UPL", "VOLTAS", "WIPRO",
    "ZEEL", "ZYDUSLIFE",
]

# Deduplicate: remove symbols already in NIFTY_100
_nifty_100_set = set(NIFTY_100_SYMBOLS)
NIFTY_200_SYMBOLS = NIFTY_100_SYMBOLS + [s for s in NIFTY_200_EXTRA if s not in _nifty_100_set]

# ── Sector colors for charts ──
SECTOR_COLORS = {
    "Financial": "#3399FF",
    "IT": "#00CC66",
    "Energy": "#FF9900",
    "FMCG": "#CC66FF",
    "Auto": "#FF6633",
    "Pharma": "#33CCCC",
    "Metals": "#999999",
    "Telecom": "#FFCC00",
    "Infrastructure": "#FF99CC",
    "Consumer": "#66FF66",
    "Power": "#FF6666",
    "Healthcare": "#33CCCC",
    "Materials": "#CC9966",
    "Mining": "#996633",
    "Defence": "#669999",
    "Conglomerate": "#CC6699",
}

# ── Key Indices ──
KEY_INDICES = [
    "NIFTY 50",
    "NIFTY BANK",
    "NIFTY IT",
    "NIFTY NEXT 50",
    "NIFTY MIDCAP 50",
    "NIFTY FINANCIAL SERVICES",
    "NIFTY AUTO",
    "NIFTY PHARMA",
    "NIFTY FMCG",
    "NIFTY METAL",
    "NIFTY REALTY",
    "NIFTY ENERGY",
    "NIFTY MEDIA",
    "NIFTY PSU BANK",
    "NIFTY PRIVATE BANK",
    "INDIA VIX",
]

# ── Sectoral Indices ──
SECTORAL_INDICES = [
    "NIFTY BANK",
    "NIFTY IT",
    "NIFTY FINANCIAL SERVICES",
    "NIFTY AUTO",
    "NIFTY PHARMA",
    "NIFTY FMCG",
    "NIFTY METAL",
    "NIFTY REALTY",
    "NIFTY ENERGY",
    "NIFTY MEDIA",
    "NIFTY PSU BANK",
    "NIFTY PRIVATE BANK",
    "NIFTY HEALTHCARE INDEX",
    "NIFTY CONSUMER DURABLES",
    "NIFTY OIL & GAS",
]

# ── Default watchlist ──
DEFAULT_WATCHLIST = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "BHARTIARTL", "SBIN", "LT", "ITC", "KOTAKBANK",
]

# ── Cache TTLs (seconds) ──
CACHE_TTL_LIVE = 60
CACHE_TTL_HISTORICAL = 3600
CACHE_TTL_FUNDAMENTALS = 86400
