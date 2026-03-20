"""Module 07: Option Chain & OI Analysis (Bloomberg: OMON)."""

import plotly.graph_objects as go
import streamlit as st

from config import COLORS, NIFTY_50_SYMBOLS, plotly_layout
from utils.logger import logger


# F&O symbols (indices + top stocks)
FNO_SYMBOLS = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"] + NIFTY_50_SYMBOLS


def render():
    """Render the Option Chain module."""
    st.markdown("### OPTION CHAIN & OI ANALYSIS")

    col_sym, col_exp = st.columns([1, 1])
    with col_sym:
        symbol = st.selectbox("SYMBOL", FNO_SYMBOLS, index=0)

    # Fetch option chain
    from data.nse_fno import get_option_chain, compute_pcr, compute_max_pain

    with st.spinner(f"Loading option chain for {symbol}..."):
        chain = get_option_chain(symbol)

    if not chain or not chain["records"]:
        st.warning(f"Option chain not available for {symbol}")
        return

    with col_exp:
        expiry_dates = chain["expiry_dates"]
        selected_expiry = st.selectbox("EXPIRY", expiry_dates,
                                        index=0 if expiry_dates else 0)

    # Re-fetch if expiry changed
    if selected_expiry != chain.get("selected_expiry"):
        with st.spinner("Refreshing..."):
            chain = get_option_chain(symbol, expiry=selected_expiry)
        if not chain or not chain["records"]:
            st.warning("No data for selected expiry")
            return

    records = chain["records"]
    underlying = chain["underlying_value"]

    # ── PCR & Max Pain row ──
    pcr = compute_pcr(records)
    max_pain = compute_max_pain(records)

    st.divider()
    c1, c2, c3, c4, c5 = st.columns(5)
    _metric(c1, "UNDERLYING", f"₹{underlying:,.2f}" if underlying else "—")
    _metric(c2, "PCR (OI)", f"{pcr['pcr_oi']:.3f}")
    _metric(c3, "PCR (VOL)", f"{pcr['pcr_vol']:.3f}")
    _metric(c4, "MAX PAIN", f"₹{max_pain:,.0f}" if max_pain else "—")
    _metric(c5, "EXPIRY", selected_expiry[:12] if selected_expiry else "—")

    st.divider()

    # ── Option Chain Table ──
    _render_chain_table(records, underlying)

    st.divider()

    # ── OI Charts ──
    _render_oi_chart(records, underlying, max_pain)


def _metric(col, label, value):
    """Render a compact metric."""
    col.markdown(
        f'<div style="text-align:center">'
        f'<div style="color:{COLORS["muted"]};font-size:10px">{label}</div>'
        f'<div style="color:{COLORS["amber"]};font-size:16px;font-weight:bold">{value}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_chain_table(records, underlying):
    """Render option chain as an HTML table with OI heatmap coloring."""
    if not records:
        return

    # Find max OI for gradient scaling
    max_ce_oi = max((r["CE_OI"] for r in records), default=1) or 1
    max_pe_oi = max((r["PE_OI"] for r in records), default=1) or 1

    # Header
    header = (
        '<tr>'
        f'<th style="color:{COLORS["green"]};padding:3px 6px;font-size:10px;text-align:right;border-bottom:1px solid {COLORS["border"]}">OI</th>'
        f'<th style="color:{COLORS["green"]};padding:3px 6px;font-size:10px;text-align:right;border-bottom:1px solid {COLORS["border"]}">Chg OI</th>'
        f'<th style="color:{COLORS["green"]};padding:3px 6px;font-size:10px;text-align:right;border-bottom:1px solid {COLORS["border"]}">Vol</th>'
        f'<th style="color:{COLORS["green"]};padding:3px 6px;font-size:10px;text-align:right;border-bottom:1px solid {COLORS["border"]}">IV</th>'
        f'<th style="color:{COLORS["green"]};padding:3px 6px;font-size:10px;text-align:right;border-bottom:1px solid {COLORS["border"]}">LTP</th>'
        f'<th style="color:{COLORS["amber"]};padding:3px 6px;font-size:11px;text-align:center;border-bottom:1px solid {COLORS["border"]};font-weight:bold">STRIKE</th>'
        f'<th style="color:{COLORS["red"]};padding:3px 6px;font-size:10px;text-align:right;border-bottom:1px solid {COLORS["border"]}">LTP</th>'
        f'<th style="color:{COLORS["red"]};padding:3px 6px;font-size:10px;text-align:right;border-bottom:1px solid {COLORS["border"]}">IV</th>'
        f'<th style="color:{COLORS["red"]};padding:3px 6px;font-size:10px;text-align:right;border-bottom:1px solid {COLORS["border"]}">Vol</th>'
        f'<th style="color:{COLORS["red"]};padding:3px 6px;font-size:10px;text-align:right;border-bottom:1px solid {COLORS["border"]}">Chg OI</th>'
        f'<th style="color:{COLORS["red"]};padding:3px 6px;font-size:10px;text-align:right;border-bottom:1px solid {COLORS["border"]}">OI</th>'
        '</tr>'
    )

    # Filter to strikes near the money (±20 strikes)
    sorted_records = sorted(records, key=lambda r: r["strikePrice"])
    if underlying:
        atm_idx = min(range(len(sorted_records)),
                      key=lambda i: abs(sorted_records[i]["strikePrice"] - underlying))
        start = max(0, atm_idx - 20)
        end = min(len(sorted_records), atm_idx + 21)
        sorted_records = sorted_records[start:end]

    rows = ""
    for r in sorted_records:
        strike = r["strikePrice"]
        is_atm = underlying and abs(strike - underlying) < (underlying * 0.005)

        # OI intensity for background color
        ce_intensity = min(r["CE_OI"] / max_ce_oi, 1.0) * 0.3
        pe_intensity = min(r["PE_OI"] / max_pe_oi, 1.0) * 0.3
        ce_bg = f"rgba(0,204,102,{ce_intensity:.2f})"
        pe_bg = f"rgba(255,51,51,{pe_intensity:.2f})"

        strike_bg = f"background:{COLORS['amber']};color:#000" if is_atm else f"color:{COLORS['amber']}"
        border = f"border-bottom:1px solid #1A1A1A"
        cell = "padding:2px 6px;font-size:11px;text-align:right"

        chg_oi_ce_color = COLORS["green"] if r["CE_chgOI"] > 0 else COLORS["red"]
        chg_oi_pe_color = COLORS["green"] if r["PE_chgOI"] > 0 else COLORS["red"]

        rows += (
            f'<tr>'
            f'<td style="{cell};{border};background:{ce_bg}">{r["CE_OI"]:,}</td>'
            f'<td style="{cell};{border};color:{chg_oi_ce_color}">{r["CE_chgOI"]:+,}</td>'
            f'<td style="{cell};{border}">{r["CE_volume"]:,}</td>'
            f'<td style="{cell};{border}">{r["CE_IV"]:.1f}</td>'
            f'<td style="{cell};{border};color:{COLORS["text"]}">{r["CE_LTP"]:.2f}</td>'
            f'<td style="padding:2px 6px;font-size:11px;text-align:center;{border};{strike_bg};font-weight:bold">{strike:,.0f}</td>'
            f'<td style="{cell};{border};color:{COLORS["text"]}">{r["PE_LTP"]:.2f}</td>'
            f'<td style="{cell};{border}">{r["PE_IV"]:.1f}</td>'
            f'<td style="{cell};{border}">{r["PE_volume"]:,}</td>'
            f'<td style="{cell};{border};color:{chg_oi_pe_color}">{r["PE_chgOI"]:+,}</td>'
            f'<td style="{cell};{border};background:{pe_bg}">{r["PE_OI"]:,}</td>'
            f'</tr>'
        )

    html = (
        f'<div style="text-align:center;margin-bottom:4px">'
        f'<span style="color:{COLORS["green"]};font-size:11px;font-weight:bold">◀ CALLS</span>'
        f'<span style="color:{COLORS["muted"]};font-size:11px;margin:0 20px">|</span>'
        f'<span style="color:{COLORS["red"]};font-size:11px;font-weight:bold">PUTS ▶</span>'
        f'</div>'
        f'<div style="overflow-x:auto;max-height:500px;overflow-y:auto">'
        f'<table style="width:100%;border-collapse:collapse;font-family:monospace">'
        f'<thead style="position:sticky;top:0;background:{COLORS["bg"]}">{header}</thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _render_oi_chart(records, underlying, max_pain):
    """Render OI bar chart — Calls vs Puts by strike."""
    if not records:
        return

    sorted_records = sorted(records, key=lambda r: r["strikePrice"])
    # Filter near ATM
    if underlying:
        atm_idx = min(range(len(sorted_records)),
                      key=lambda i: abs(sorted_records[i]["strikePrice"] - underlying))
        start = max(0, atm_idx - 15)
        end = min(len(sorted_records), atm_idx + 16)
        sorted_records = sorted_records[start:end]

    strikes = [r["strikePrice"] for r in sorted_records]
    ce_oi = [r["CE_OI"] for r in sorted_records]
    pe_oi = [r["PE_OI"] for r in sorted_records]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=strikes, y=ce_oi, name="Call OI",
        marker_color=COLORS["green"], opacity=0.7,
    ))
    fig.add_trace(go.Bar(
        x=strikes, y=pe_oi, name="Put OI",
        marker_color=COLORS["red"], opacity=0.7,
    ))

    # Mark underlying and max pain
    if underlying:
        fig.add_vline(x=underlying, line_dash="dash", line_color=COLORS["amber"],
                      annotation_text=f"Spot: {underlying:,.0f}")
    if max_pain:
        fig.add_vline(x=max_pain, line_dash="dot", line_color=COLORS["blue"],
                      annotation_text=f"MaxPain: {max_pain:,.0f}")

    fig.update_layout(**plotly_layout(
        height=350,
        barmode="group",
        xaxis_title="Strike Price",
        yaxis_title="Open Interest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    ))

    st.markdown("##### OI BY STRIKE")
    st.plotly_chart(fig, use_container_width=True)
