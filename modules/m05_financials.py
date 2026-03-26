"""Module 05: Financial Statements & Ratios (Bloomberg: FA)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import NIFTY_500_SYMBOLS, COLORS, plotly_layout


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
        symbol = st.selectbox("SYMBOL", NIFTY_500_SYMBOLS, index=0, key="m05_symbol")
    with col_period:
        period = st.radio("PERIOD", ["Annual", "Quarterly"], horizontal=True, key="m05_period")

    period_key = "annual" if period == "Annual" else "quarterly"

    tab_income, tab_balance, tab_cashflow, tab_ratios, tab_peers, tab_trends = st.tabs([
        "INCOME STATEMENT", "BALANCE SHEET", "CASH FLOW", "KEY RATIOS", "PEER COMPARISON", "TREND SPARKLINES",
    ])

    with tab_income:
        _render_statement(symbol, "income", period_key)

    with tab_balance:
        _render_statement(symbol, "balance", period_key)

    with tab_cashflow:
        _render_statement(symbol, "cashflow", period_key)

    with tab_ratios:
        _render_ratios(symbol)

    with tab_peers:
        _render_peer_comparison(symbol)

    with tab_trends:
        _render_trend_sparklines(symbol)


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


def _render_peer_comparison(symbol):
    """Side-by-side comparison of key ratios against peer companies."""
    from data.fundamentals import get_company_info

    peers = st.multiselect(
        "SELECT PEERS (up to 4)",
        [s for s in NIFTY_500_SYMBOLS if s != symbol],
        default=[],
        max_selections=4,
        key="m05_peers",
    )

    all_symbols = [symbol] + peers
    if not peers:
        st.info("Select peer companies above to compare.")
        return

    # Fetch info for all symbols
    infos = {}
    with st.spinner("Fetching peer data..."):
        for sym in all_symbols:
            try:
                info = get_company_info(sym)
                if info:
                    infos[sym] = info
            except Exception:
                pass

    if len(infos) < 2:
        st.warning("Not enough data to compare. Try different peers.")
        return

    # Metrics to compare — (label, key, format, higher_is_better)
    metrics = [
        ("P/E Ratio", "trailingPE", "ratio", False),
        ("P/B Ratio", "priceToBook", "ratio", False),
        ("ROE", "returnOnEquity", "pct", True),
        ("ROA", "returnOnAssets", "pct", True),
        ("Debt / Equity", "debtToEquity", "ratio", False),
        ("Operating Margin", "operatingMargins", "pct", True),
        ("Net Margin", "profitMargins", "pct", True),
        ("Dividend Yield", "dividendYield", "pct", True),
        ("Market Cap", "marketCap", "crore", True),
        ("EPS (TTM)", "trailingEps", "ratio", True),
    ]

    ordered_syms = [s for s in all_symbols if s in infos]

    def _fmt(val, fmt_type):
        if val is None:
            return "—"
        try:
            val = float(val)
        except (ValueError, TypeError):
            return "—"
        if fmt_type == "pct":
            return f"{val * 100:.2f}%" if abs(val) < 10 else f"{val:.2f}%"
        if fmt_type == "crore":
            cr = val / 1e7
            return f"₹{cr:,.0f} Cr"
        return f"{val:.2f}"

    # Build HTML table
    header_cells = '<th style="padding:6px 8px;text-align:left;color:#FF9900;border-bottom:1px solid #FF9900;font-size:10px;min-width:140px">METRIC</th>'
    for sym in ordered_syms:
        bg = "background:#1A1A00;" if sym == symbol else ""
        header_cells += (
            f'<th style="padding:6px 8px;text-align:right;color:#FF9900;border-bottom:1px solid #FF9900;'
            f'font-size:10px;white-space:nowrap;{bg}">{sym}</th>'
        )

    rows_html = ""
    for label, key, fmt_type, higher_is_better in metrics:
        raw_vals = {}
        for sym in ordered_syms:
            raw_vals[sym] = infos[sym].get(key)

        # Determine best value
        numeric_vals = {}
        for sym, v in raw_vals.items():
            if v is not None:
                try:
                    numeric_vals[sym] = float(v)
                except (ValueError, TypeError):
                    pass

        best_sym = None
        if numeric_vals:
            if higher_is_better:
                best_sym = max(numeric_vals, key=numeric_vals.get)
            else:
                best_sym = min(numeric_vals, key=numeric_vals.get)

        cells = f'<td style="padding:4px 8px;color:#E0E0E0;border-bottom:1px solid #1A1A1A;font-size:12px">{label}</td>'
        for sym in ordered_syms:
            formatted = _fmt(raw_vals[sym], fmt_type)
            color = COLORS["green"] if sym == best_sym else COLORS["text"]
            font_weight = "bold" if sym == best_sym else "normal"
            cells += (
                f'<td style="padding:4px 8px;text-align:right;color:{color};font-weight:{font_weight};'
                f'font-family:monospace;border-bottom:1px solid #1A1A1A;font-size:12px;white-space:nowrap">'
                f'{formatted}</td>'
            )
        rows_html += f"<tr>{cells}</tr>"

    st.markdown(
        f'<div style="overflow-x:auto">'
        f'<table style="width:100%;border-collapse:collapse;border:1px solid #333">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def _render_trend_sparklines(symbol):
    """Show 5-year trend sparklines for key income statement metrics."""
    from data.fundamentals import get_income_statement

    with st.spinner("Loading trend data..."):
        try:
            data = get_income_statement(symbol)
        except Exception:
            st.warning(f"Could not fetch income statement for {symbol}")
            return

    if data is None:
        st.warning(f"No income statement data available for {symbol}")
        return

    df = data["annual"]
    if df is None or df.empty:
        st.warning("No annual data available")
        return

    # Sort columns chronologically (oldest first)
    df = df[sorted(df.columns)]

    def _extract_series(row_name):
        """Extract a time series from the dataframe, returning (dates, values)."""
        if row_name not in df.index:
            return None, None
        row = df.loc[row_name]
        dates = []
        values = []
        for col in row.index:
            val = row[col]
            if pd.notna(val):
                try:
                    dates.append(pd.Timestamp(col).strftime("%b %y"))
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass
        if len(values) < 2:
            return None, None
        return dates, values

    def _make_sparkline(dates, values, title, fmt_fn=None):
        """Create a tiny sparkline figure."""
        if dates is None or values is None:
            return None

        trend_up = values[-1] >= values[0]
        line_color = COLORS["green"] if trend_up else COLORS["red"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            mode="lines",
            line=dict(color=line_color, width=2),
            fill="tozeroy",
            fillcolor=f"rgba({'0,204,102' if trend_up else '255,51,51'},0.1)",
            hovertemplate="%{x}: %{y:,.0f}<extra></extra>",
        ))

        # Annotate start and end values
        start_label = fmt_fn(values[0]) if fmt_fn else f"{values[0]:,.0f}"
        end_label = fmt_fn(values[-1]) if fmt_fn else f"{values[-1]:,.0f}"

        fig.add_annotation(x=dates[0], y=values[0], text=start_label,
                           showarrow=False, yshift=12, font=dict(size=9, color=COLORS["muted"]))
        fig.add_annotation(x=dates[-1], y=values[-1], text=end_label,
                           showarrow=False, yshift=12, font=dict(size=9, color=line_color))

        fig.update_layout(**plotly_layout(
            title=dict(text=title, font=dict(size=11, color=COLORS["amber"])),
            height=80,
            margin=dict(l=5, r=5, t=25, b=5),
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            showlegend=False,
        ))
        return fig

    def _fmt_crore(val):
        cr = val / 1e7
        if abs(cr) >= 100:
            return f"₹{cr:,.0f}Cr"
        return f"₹{cr:,.1f}Cr"

    def _fmt_pct(val):
        return f"{val:.1f}%"

    # Extract series
    rev_dates, rev_values = _extract_series("Total Revenue")
    ni_dates, ni_values = _extract_series("Net Income")
    oi_dates, oi_values = _extract_series("Operating Income")

    # Compute operating margin trend
    om_dates, om_values = None, None
    if rev_dates and oi_dates and rev_values and oi_values and len(rev_values) == len(oi_values):
        om_dates = rev_dates
        om_values = [(oi / rev * 100) if rev != 0 else 0 for oi, rev in zip(oi_values, rev_values)]

    sparklines = [
        (rev_dates, rev_values, "TOTAL REVENUE", _fmt_crore),
        (ni_dates, ni_values, "NET INCOME", _fmt_crore),
        (oi_dates, oi_values, "OPERATING INCOME", _fmt_crore),
        (om_dates, om_values, "OPERATING MARGIN %", _fmt_pct),
    ]

    # 2x2 grid
    for row_start in range(0, len(sparklines), 2):
        cols = st.columns(2)
        for col, (dates, values, title, fmt_fn) in zip(cols, sparklines[row_start:row_start + 2]):
            fig = _make_sparkline(dates, values, title, fmt_fn)
            if fig:
                col.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                col.markdown(
                    f'<div style="background:#1A1A1A;padding:10px;border:1px solid #333;height:80px;'
                    f'display:flex;align-items:center;justify-content:center">'
                    f'<span style="color:#888;font-size:11px">{title}: No data</span></div>',
                    unsafe_allow_html=True,
                )
