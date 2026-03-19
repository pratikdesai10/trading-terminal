"""Module 05: Financial Statements & Ratios (Bloomberg: FA)."""

import pandas as pd
import streamlit as st

from config import NIFTY_50_SYMBOLS, COLORS


# Key rows to display from each financial statement
INCOME_ROWS = [
    "Total Revenue", "Cost Of Revenue", "Gross Profit",
    "Operating Expense", "Operating Income", "EBITDA", "EBIT",
    "Interest Expense", "Tax Provision",
    "Net Income", "Net Income From Continuing Operation Net Minority Interest",
    "Basic EPS", "Diluted EPS",
]

BALANCE_ROWS = [
    "Total Assets", "Current Assets", "Cash And Cash Equivalents",
    "Cash Cash Equivalents And Short Term Investments",
    "Total Non Current Assets", "Net PPE",
    "Total Liabilities Net Minority Interest", "Current Liabilities",
    "Total Non Current Liabilities Net Minority Interest", "Total Debt",
    "Stockholders Equity", "Common Stock Equity", "Retained Earnings",
    "Working Capital",
]

CASHFLOW_ROWS = [
    "Operating Cash Flow", "Capital Expenditure", "Free Cash Flow",
    "Investing Cash Flow", "Financing Cash Flow",
    "Cash Dividends Paid", "Repayment Of Debt", "Issuance Of Debt",
    "Changes In Cash", "End Cash Position",
]


def render():
    """Render the Financials module."""
    st.markdown("### FINANCIAL ANALYSIS")

    col_sym, col_period = st.columns([2, 1])
    with col_sym:
        symbol = st.selectbox("SYMBOL", NIFTY_50_SYMBOLS, index=0, key="m05_symbol")
    with col_period:
        period = st.radio("PERIOD", ["Annual", "Quarterly"], horizontal=True, key="m05_period")

    period_key = "annual" if period == "Annual" else "quarterly"

    tab_income, tab_balance, tab_cashflow, tab_ratios = st.tabs([
        "INCOME STATEMENT", "BALANCE SHEET", "CASH FLOW", "KEY RATIOS",
    ])

    with tab_income:
        _render_statement(symbol, "income", period_key)

    with tab_balance:
        _render_statement(symbol, "balance", period_key)

    with tab_cashflow:
        _render_statement(symbol, "cashflow", period_key)

    with tab_ratios:
        _render_ratios(symbol)


def _render_statement(symbol, stmt_type, period_key):
    """Fetch and display a financial statement as an HTML table."""
    from data.fundamentals import get_income_statement, get_balance_sheet, get_cashflow

    fetch_map = {
        "income": (get_income_statement, INCOME_ROWS),
        "balance": (get_balance_sheet, BALANCE_ROWS),
        "cashflow": (get_cashflow, CASHFLOW_ROWS),
    }

    fetch_fn, row_filter = fetch_map[stmt_type]

    with st.spinner("Loading..."):
        data = fetch_fn(symbol)

    if data is None:
        st.warning(f"No {stmt_type} data available for {symbol}")
        return

    df = data[period_key]
    if df is None or df.empty:
        st.warning(f"No {period_key} data available")
        return

    # Filter to key rows (keep only rows that exist)
    available_rows = [r for r in row_filter if r in df.index]
    if not available_rows:
        # Show all rows if none of the expected ones match
        available_rows = list(df.index)
    df_display = df.loc[available_rows]

    # Format column headers as dates
    col_headers = []
    for col in df_display.columns:
        try:
            col_headers.append(pd.Timestamp(col).strftime("%b %Y"))
        except Exception:
            col_headers.append(str(col))

    # Build HTML table
    header_cells = '<th style="padding:6px 8px;text-align:left;color:#FF9900;border-bottom:1px solid #FF9900;font-size:10px;text-transform:uppercase;min-width:180px">Item</th>'
    for h in col_headers:
        header_cells += f'<th style="padding:6px 8px;text-align:right;color:#FF9900;border-bottom:1px solid #FF9900;font-size:10px;text-transform:uppercase;white-space:nowrap">{h}</th>'

    rows_html = ""
    for row_name in available_rows:
        row_data = df_display.loc[row_name]
        cells = f'<td style="padding:4px 8px;color:#E0E0E0;border-bottom:1px solid #1A1A1A;font-size:12px">{row_name}</td>'
        for val in row_data:
            formatted = _format_value(val)
            color = COLORS["text"]
            try:
                if pd.notna(val) and float(val) < 0:
                    color = COLORS["red"]
            except (ValueError, TypeError):
                pass
            cells += (
                f'<td style="padding:4px 8px;text-align:right;color:{color};'
                f'font-family:monospace;border-bottom:1px solid #1A1A1A;font-size:12px;white-space:nowrap">'
                f'{formatted}</td>'
            )
        rows_html += f'<tr>{cells}</tr>'

    st.markdown(
        f'<div style="overflow-x:auto">'
        f'<table style="width:100%;border-collapse:collapse;border:1px solid #333">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def _format_value(val):
    """Format a financial value — convert to ₹ Crores."""
    if pd.isna(val):
        return "—"
    try:
        val = float(val)
    except (ValueError, TypeError):
        return str(val)

    # EPS values are small (< 10000), don't convert to Crores
    if abs(val) < 10000:
        return f"{val:,.2f}"

    # Convert to Crores (1 Cr = 1,00,00,000 = 1e7)
    cr = val / 1e7
    if abs(cr) >= 100:
        return f"₹{cr:,.0f} Cr"
    elif abs(cr) >= 1:
        return f"₹{cr:,.2f} Cr"
    else:
        lakh = val / 1e5
        return f"₹{lakh:,.2f} L"


def _render_ratios(symbol):
    """Display key financial ratios."""
    from data.fundamentals import get_company_info

    with st.spinner("Loading ratios..."):
        info = get_company_info(symbol)

    if info is None:
        st.warning(f"No ratio data available for {symbol}")
        return

    st.markdown("##### KEY RATIOS")

    def _fmt_pct(val):
        if val is None:
            return "—"
        if abs(val) < 10:
            return f"{val * 100:.2f}%"
        return f"{val:.2f}%"

    def _fmt_ratio(val):
        if val is None:
            return "—"
        return f"{val:.2f}"

    ratios = [
        ("RETURN ON EQUITY", _fmt_pct(info.get("returnOnEquity"))),
        ("RETURN ON ASSETS", _fmt_pct(info.get("returnOnAssets"))),
        ("OPERATING MARGIN", _fmt_pct(info.get("operatingMargins"))),
        ("NET MARGIN", _fmt_pct(info.get("profitMargins"))),
        ("DEBT / EQUITY", _fmt_ratio(info.get("debtToEquity"))),
        ("REVENUE GROWTH", _fmt_pct(info.get("revenueGrowth"))),
        ("EARNINGS GROWTH", _fmt_pct(info.get("earningsGrowth"))),
        ("EV / EBITDA", _fmt_ratio(info.get("enterpriseToEbitda"))),
    ]

    for row_start in range(0, len(ratios), 4):
        cols = st.columns(4)
        for col, (label, value) in zip(cols, ratios[row_start:row_start + 4]):
            col.markdown(
                f'<div style="background:#1A1A1A;padding:10px;border:1px solid #333;border-radius:4px">'
                f'<div style="color:#FF9900;font-size:10px;text-transform:uppercase;letter-spacing:1px">{label}</div>'
                f'<div style="color:#E0E0E0;font-size:18px;font-family:monospace;margin-top:4px">{value}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
