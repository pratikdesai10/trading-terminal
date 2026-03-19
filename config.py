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
