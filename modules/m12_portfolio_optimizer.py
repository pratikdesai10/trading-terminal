"""Module 12: Portfolio Optimizer (Bloomberg: PORT).

Mean-variance optimization, efficient frontier, Monte Carlo simulation,
and risk analytics for Nifty 50 portfolios. Pure numpy/scipy implementation.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.optimize import minimize

from config import COLORS, NIFTY_50_SYMBOLS, SECTOR_COLORS, NIFTY_50, plotly_layout
from utils.logger import logger
from analytics.risk_metrics import (
    compute_var,
    compute_es,
    compute_sharpe,
    compute_max_drawdown,
    compute_sortino,
    compute_portfolio_returns,
    INDIA_RISK_FREE,
)

# ── Constants ──
TRADING_DAYS = 252
MONTE_CARLO_SIMS = 10_000
LOOKBACK_MAP = {"6M": 180, "1Y": 365, "2Y": 730, "3Y": 1095}
OPTIMIZATION_TARGETS = [
    "Max Sharpe Ratio",
    "Min Volatility",
    "Risk Parity",
    "Max Return for Given Risk",
]


def render():
    """Render the Portfolio Optimizer module."""
    st.markdown(
        f'<span style="color:{COLORS["amber"]};font-size:15px;font-weight:bold;'
        f'letter-spacing:1px">PORTFOLIO OPTIMIZER</span>',
        unsafe_allow_html=True,
    )

    # ── Controls ──
    col_stocks, col_lookback, col_target = st.columns([3, 1, 2])

    with col_stocks:
        symbols = st.multiselect(
            "SELECT STOCKS (min 2, max 15)",
            NIFTY_50_SYMBOLS,
            default=["RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC"],
            max_selections=15,
            key="m12_symbols",
        )

    with col_lookback:
        lookback = st.selectbox(
            "LOOKBACK",
            list(LOOKBACK_MAP.keys()),
            index=1,
            key="m12_lookback",
        )

    with col_target:
        target = st.selectbox(
            "OPTIMIZATION TARGET",
            OPTIMIZATION_TARGETS,
            index=0,
            key="m12_target",
        )

    # Risk budget slider for "Max Return for Given Risk"
    target_vol = None
    if target == "Max Return for Given Risk":
        target_vol = st.slider(
            "TARGET ANNUAL VOLATILITY (%)",
            min_value=5.0,
            max_value=50.0,
            value=20.0,
            step=1.0,
            key="m12_target_vol",
        )

    if len(symbols) < 2:
        st.info("Select at least 2 stocks to optimize.")
        return

    # ── Fetch data ──
    with st.spinner("Fetching historical data..."):
        returns_df, failed = _fetch_returns(symbols, LOOKBACK_MAP[lookback])

    if failed:
        st.warning(f"Could not fetch data for: {', '.join(failed)}")

    valid_symbols = [s for s in symbols if s not in failed]
    if len(valid_symbols) < 2:
        st.error("Need at least 2 stocks with valid data.")
        return

    returns_df = returns_df[valid_symbols].dropna()
    if len(returns_df) < 30:
        st.error("Insufficient overlapping data. Try fewer stocks or shorter lookback.")
        return

    n_assets = len(valid_symbols)
    mean_returns = returns_df.mean().values
    cov_matrix = returns_df.cov().values
    returns_matrix = returns_df.values

    logger.info(
        f"m12_portfolio_optimizer | {n_assets} assets | {len(returns_df)} days | "
        f"lookback={lookback} | target={target}"
    )

    # ── Run optimization ──
    with st.spinner("Running optimization..."):
        opt_weights = _optimize(
            mean_returns, cov_matrix, n_assets, target, target_vol
        )
        mc_results = _monte_carlo(mean_returns, cov_matrix, n_assets)
        frontier = _efficient_frontier(mean_returns, cov_matrix, n_assets)

    if opt_weights is None:
        st.error("Optimization failed. Try different stocks or lookback period.")
        return

    # ── Compute optimized portfolio metrics ──
    port_ret, port_vol = _portfolio_performance(opt_weights, mean_returns, cov_matrix)
    port_daily_returns = compute_portfolio_returns(returns_matrix, opt_weights)
    port_sharpe = compute_sharpe(port_daily_returns)
    port_sortino = compute_sortino(port_daily_returns)
    port_var_95 = compute_var(port_daily_returns, 0.95)
    port_var_99 = compute_var(port_daily_returns, 0.99)
    port_es_95 = compute_es(port_daily_returns, 0.95)
    port_es_99 = compute_es(port_daily_returns, 0.99)
    port_max_dd = compute_max_drawdown(port_daily_returns)

    # ── Display ──
    _render_summary_strip(port_ret, port_vol, port_sharpe, port_sortino, target)

    col_chart, col_weights = st.columns([3, 2])

    with col_chart:
        _render_efficient_frontier(
            mc_results, frontier, port_ret, port_vol, target
        )

    with col_weights:
        _render_weights_table(valid_symbols, opt_weights)

    st.markdown("")  # spacer

    col_risk, col_alloc = st.columns([1, 1])

    with col_risk:
        _render_risk_metrics(
            port_var_95, port_var_99, port_es_95, port_es_99, port_max_dd
        )

    with col_alloc:
        _render_sector_allocation(valid_symbols, opt_weights)

    st.markdown("")
    _render_correlation_heatmap(returns_df)


# ═════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═════════════════════════════════════════════════════════════════════════════


def _fetch_returns(symbols, days):
    """Fetch daily close prices and compute returns. Returns (returns_df, failed_list)."""
    from data.nse_historical import get_stock_history

    end = date.today()
    start = end - timedelta(days=days)
    prices = {}
    failed = []

    for sym in symbols:
        df = get_stock_history(sym, start, end)
        if df is not None and not df.empty and len(df) > 5:
            series = df.set_index("Date")["Close"]
            series = series[~series.index.duplicated(keep="last")]
            prices[sym] = series
        else:
            failed.append(sym)

    if len(prices) < 2:
        return pd.DataFrame(), failed

    price_df = pd.DataFrame(prices).sort_index().ffill().dropna()
    returns_df = price_df.pct_change().dropna()
    return returns_df, failed


# ═════════════════════════════════════════════════════════════════════════════
# OPTIMIZATION ENGINE (scipy.optimize)
# ═════════════════════════════════════════════════════════════════════════════


def _portfolio_performance(weights, mean_returns, cov_matrix):
    """Compute annualized return and volatility for given weights."""
    ann_ret = np.sum(mean_returns * weights) * TRADING_DAYS
    ann_vol = np.sqrt(weights @ cov_matrix @ weights) * np.sqrt(TRADING_DAYS)
    return float(ann_ret), float(ann_vol)


def _optimize(mean_returns, cov_matrix, n_assets, target, target_vol=None):
    """Run constrained optimization. Returns optimal weight array or None."""
    bounds = tuple((0.0, 1.0) for _ in range(n_assets))
    weight_sum_constraint = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    init = np.ones(n_assets) / n_assets

    try:
        if target == "Max Sharpe Ratio":
            return _optimize_max_sharpe(
                mean_returns, cov_matrix, n_assets, bounds, weight_sum_constraint, init
            )
        elif target == "Min Volatility":
            return _optimize_min_vol(
                cov_matrix, n_assets, bounds, weight_sum_constraint, init
            )
        elif target == "Risk Parity":
            return _optimize_risk_parity(cov_matrix, n_assets)
        elif target == "Max Return for Given Risk":
            return _optimize_max_return_for_risk(
                mean_returns, cov_matrix, n_assets, bounds,
                weight_sum_constraint, init, target_vol
            )
    except Exception as e:
        logger.error(f"_optimize | target={target} | {type(e).__name__}: {e}")
        return None


def _optimize_max_sharpe(mean_returns, cov_matrix, n_assets, bounds, eq_con, init):
    """Maximize Sharpe ratio (minimize negative Sharpe)."""
    daily_rf = (1 + INDIA_RISK_FREE) ** (1 / TRADING_DAYS) - 1

    def neg_sharpe(w):
        ret = np.sum(mean_returns * w) * TRADING_DAYS
        vol = np.sqrt(w @ cov_matrix @ w) * np.sqrt(TRADING_DAYS)
        if vol < 1e-10:
            return 1e6
        return -(ret - INDIA_RISK_FREE) / vol

    result = minimize(
        neg_sharpe, init, method="SLSQP", bounds=bounds, constraints=[eq_con],
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    if result.success:
        logger.info(f"max_sharpe | converged | sharpe={-result.fun:.4f}")
        return result.x
    logger.warning(f"max_sharpe | did not converge: {result.message}")
    return result.x  # return best attempt


def _optimize_min_vol(cov_matrix, n_assets, bounds, eq_con, init):
    """Minimize portfolio volatility."""

    def portfolio_vol(w):
        return np.sqrt(w @ cov_matrix @ w) * np.sqrt(TRADING_DAYS)

    result = minimize(
        portfolio_vol, init, method="SLSQP", bounds=bounds, constraints=[eq_con],
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    if result.success:
        logger.info(f"min_vol | converged | vol={result.fun:.4f}")
    else:
        logger.warning(f"min_vol | did not converge: {result.message}")
    return result.x


def _optimize_risk_parity(cov_matrix, n_assets):
    """Equal risk contribution (risk parity) portfolio.

    Each asset contributes equally to total portfolio variance.
    """
    init = np.ones(n_assets) / n_assets
    bounds = tuple((1e-6, 1.0) for _ in range(n_assets))
    weight_sum_constraint = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

    def risk_contribution_error(w):
        port_var = w @ cov_matrix @ w
        if port_var < 1e-16:
            return 1e6
        # Marginal risk contribution
        marginal = cov_matrix @ w
        # Risk contribution of each asset
        rc = w * marginal
        rc_pct = rc / port_var
        # Target: equal contribution = 1/n
        target_rc = 1.0 / n_assets
        return np.sum((rc_pct - target_rc) ** 2)

    result = minimize(
        risk_contribution_error, init, method="SLSQP",
        bounds=bounds, constraints=[weight_sum_constraint],
        options={"maxiter": 1000, "ftol": 1e-14},
    )
    if result.success:
        logger.info("risk_parity | converged")
    else:
        logger.warning(f"risk_parity | did not converge: {result.message}")
    return result.x


def _optimize_max_return_for_risk(
    mean_returns, cov_matrix, n_assets, bounds, eq_con, init, target_vol
):
    """Maximize return subject to a volatility ceiling."""
    vol_target = target_vol / 100.0  # convert from percentage

    vol_constraint = {
        "type": "ineq",
        "fun": lambda w: vol_target - np.sqrt(w @ cov_matrix @ w) * np.sqrt(TRADING_DAYS),
    }

    def neg_return(w):
        return -(np.sum(mean_returns * w) * TRADING_DAYS)

    result = minimize(
        neg_return, init, method="SLSQP",
        bounds=bounds, constraints=[eq_con, vol_constraint],
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    if result.success:
        logger.info(f"max_return_for_risk | converged | ret={-result.fun:.4f}")
    else:
        logger.warning(f"max_return_for_risk | did not converge: {result.message}")
    return result.x


# ═════════════════════════════════════════════════════════════════════════════
# MONTE CARLO SIMULATION
# ═════════════════════════════════════════════════════════════════════════════


def _monte_carlo(mean_returns, cov_matrix, n_assets):
    """Generate random portfolios for Monte Carlo overlay.

    Returns dict with arrays: returns, volatilities, sharpes.
    """
    np.random.seed(42)
    results_ret = np.zeros(MONTE_CARLO_SIMS)
    results_vol = np.zeros(MONTE_CARLO_SIMS)
    results_sharpe = np.zeros(MONTE_CARLO_SIMS)

    for i in range(MONTE_CARLO_SIMS):
        w = np.random.random(n_assets)
        w /= w.sum()
        ret, vol = _portfolio_performance(w, mean_returns, cov_matrix)
        results_ret[i] = ret
        results_vol[i] = vol
        results_sharpe[i] = (ret - INDIA_RISK_FREE) / vol if vol > 1e-10 else 0

    logger.info(
        f"monte_carlo | {MONTE_CARLO_SIMS} sims | "
        f"ret=[{results_ret.min():.4f}, {results_ret.max():.4f}] | "
        f"vol=[{results_vol.min():.4f}, {results_vol.max():.4f}]"
    )
    return {
        "returns": results_ret,
        "volatilities": results_vol,
        "sharpes": results_sharpe,
    }


# ═════════════════════════════════════════════════════════════════════════════
# EFFICIENT FRONTIER
# ═════════════════════════════════════════════════════════════════════════════


def _efficient_frontier(mean_returns, cov_matrix, n_assets, n_points=60):
    """Compute the efficient frontier by sweeping target returns.

    Returns dict with arrays: returns, volatilities.
    """
    bounds = tuple((0.0, 1.0) for _ in range(n_assets))
    init = np.ones(n_assets) / n_assets

    # Range of achievable returns
    min_ret = np.min(mean_returns) * TRADING_DAYS
    max_ret = np.max(mean_returns) * TRADING_DAYS
    target_returns = np.linspace(min_ret, max_ret, n_points)

    frontier_ret = []
    frontier_vol = []

    for t_ret in target_returns:
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {
                "type": "eq",
                "fun": lambda w, tr=t_ret: np.sum(mean_returns * w) * TRADING_DAYS - tr,
            },
        ]

        def min_vol(w):
            return np.sqrt(w @ cov_matrix @ w) * np.sqrt(TRADING_DAYS)

        result = minimize(
            min_vol, init, method="SLSQP", bounds=bounds, constraints=constraints,
            options={"maxiter": 500, "ftol": 1e-10},
        )
        if result.success:
            frontier_ret.append(t_ret)
            frontier_vol.append(result.fun)

    return {
        "returns": np.array(frontier_ret),
        "volatilities": np.array(frontier_vol),
    }


# ═════════════════════════════════════════════════════════════════════════════
# RENDERING
# ═════════════════════════════════════════════════════════════════════════════


def _render_summary_strip(port_ret, port_vol, port_sharpe, port_sortino, target):
    """Top summary bar with key portfolio metrics."""
    ret_color = COLORS["green"] if port_ret >= 0 else COLORS["red"]

    cells = [
        ("TARGET", target, COLORS["amber"]),
        ("ANN. RETURN", f"{port_ret * 100:+.2f}%", ret_color),
        ("ANN. VOLATILITY", f"{port_vol * 100:.2f}%", COLORS["text"]),
        ("SHARPE", f"{port_sharpe:.3f}", COLORS["blue"]),
        ("SORTINO", f"{port_sortino:.3f}", COLORS["blue"]),
    ]

    html_cells = ""
    for label, value, color in cells:
        html_cells += (
            f'<div style="text-align:center;padding:6px 12px;border-right:1px solid {COLORS["border"]}">'
            f'<div style="color:{COLORS["muted"]};font-size:9px;text-transform:uppercase;letter-spacing:1px">{label}</div>'
            f'<div style="color:{color};font-size:14px;font-weight:bold;font-family:monospace">{value}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div style="display:flex;justify-content:space-around;background:{COLORS["panel"]};'
        f'border:1px solid {COLORS["border"]};border-radius:2px;margin:8px 0 12px 0;padding:4px 0">'
        f'{html_cells}</div>',
        unsafe_allow_html=True,
    )


def _render_efficient_frontier(mc_results, frontier, opt_ret, opt_vol, target):
    """Plot efficient frontier with Monte Carlo overlay and optimal point."""
    st.markdown(
        f'<span style="color:{COLORS["amber"]};font-size:12px;font-weight:bold">'
        f'EFFICIENT FRONTIER & MONTE CARLO ({MONTE_CARLO_SIMS:,} SIMULATIONS)</span>',
        unsafe_allow_html=True,
    )

    fig = go.Figure()

    # Monte Carlo scatter
    fig.add_trace(go.Scatter(
        x=mc_results["volatilities"] * 100,
        y=mc_results["returns"] * 100,
        mode="markers",
        marker=dict(
            size=2.5,
            color=mc_results["sharpes"],
            colorscale=[
                [0.0, "#FF3333"],
                [0.5, "#FFCC00"],
                [1.0, "#00CC66"],
            ],
            showscale=True,
            colorbar=dict(
                title=dict(text="Sharpe", font=dict(size=10, color=COLORS["text"])),
                tickfont=dict(size=9, color=COLORS["text"]),
                len=0.6,
                thickness=12,
            ),
            opacity=0.4,
        ),
        name="Random Portfolios",
        hovertemplate="Vol: %{x:.2f}%<br>Ret: %{y:.2f}%<extra></extra>",
    ))

    # Efficient frontier line
    if len(frontier["returns"]) > 1:
        fig.add_trace(go.Scatter(
            x=frontier["volatilities"] * 100,
            y=frontier["returns"] * 100,
            mode="lines",
            line=dict(color=COLORS["amber"], width=2.5),
            name="Efficient Frontier",
            hovertemplate="Vol: %{x:.2f}%<br>Ret: %{y:.2f}%<extra></extra>",
        ))

    # Optimal portfolio marker
    fig.add_trace(go.Scatter(
        x=[opt_vol * 100],
        y=[opt_ret * 100],
        mode="markers+text",
        marker=dict(size=14, color=COLORS["amber"], symbol="star", line=dict(width=1, color="#FFFFFF")),
        text=[target.split()[0:2]],
        textposition="top center",
        textfont=dict(size=10, color=COLORS["amber"]),
        name=f"Optimal ({target})",
        hovertemplate=f"<b>{target}</b><br>Vol: %{{x:.2f}}%<br>Ret: %{{y:.2f}}%<extra></extra>",
    ))

    fig.update_layout(**plotly_layout(
        height=420,
        xaxis_title="Annual Volatility (%)",
        yaxis_title="Annual Return (%)",
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=10, color=COLORS["text"]),
        ),
    ))

    st.plotly_chart(fig, use_container_width=True)


def _render_weights_table(symbols, weights):
    """Bloomberg-style weights table with sector info."""
    st.markdown(
        f'<span style="color:{COLORS["amber"]};font-size:12px;font-weight:bold">'
        f'RECOMMENDED ALLOCATION</span>',
        unsafe_allow_html=True,
    )

    # Sort by weight descending
    sorted_idx = np.argsort(weights)[::-1]

    headers = ["#", "STOCK", "SECTOR", "WEIGHT"]
    header_html = ""
    aligns = ["center", "left", "left", "right"]
    for i, h in enumerate(headers):
        header_html += (
            f'<th style="padding:5px 8px;text-align:{aligns[i]};color:{COLORS["amber"]};'
            f'border-bottom:2px solid {COLORS["amber"]};font-size:10px;'
            f'letter-spacing:1px;white-space:nowrap">{h}</th>'
        )

    rows_html = ""
    for rank, idx in enumerate(sorted_idx):
        w = weights[idx]
        if w < 0.001:  # skip negligible weights
            continue
        sym = symbols[idx]
        sector = NIFTY_50.get(sym, "—")
        sector_color = SECTOR_COLORS.get(sector, COLORS["text"])

        # Weight bar (visual indicator)
        bar_width = min(w * 100, 100)
        bar_color = COLORS["green"] if w >= 0.10 else COLORS["blue"] if w >= 0.05 else COLORS["muted"]

        rows_html += (
            f'<tr style="border-bottom:1px solid {COLORS["panel"]}">'
            f'<td style="padding:4px 8px;text-align:center;color:{COLORS["muted"]};font-size:11px">{rank + 1}</td>'
            f'<td style="padding:4px 8px;color:{COLORS["blue"]};font-size:12px;font-weight:bold">{sym}</td>'
            f'<td style="padding:4px 8px;color:{sector_color};font-size:11px">{sector}</td>'
            f'<td style="padding:4px 8px;text-align:right;font-family:monospace;font-size:12px">'
            f'<div style="display:flex;align-items:center;justify-content:flex-end;gap:6px">'
            f'<div style="width:60px;height:8px;background:{COLORS["panel"]};border-radius:2px;overflow:hidden">'
            f'<div style="width:{bar_width}%;height:100%;background:{bar_color}"></div></div>'
            f'<span style="color:{COLORS["text"]};min-width:48px">{w * 100:.1f}%</span>'
            f'</div></td>'
            f'</tr>'
        )

    st.markdown(
        f'<div style="max-height:370px;overflow-y:auto">'
        f'<table style="width:100%;border-collapse:collapse;border:1px solid {COLORS["border"]}">'
        f'<thead><tr>{header_html}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def _render_risk_metrics(var_95, var_99, es_95, es_99, max_dd):
    """Display VaR, Expected Shortfall, and drawdown metrics."""
    st.markdown(
        f'<span style="color:{COLORS["amber"]};font-size:12px;font-weight:bold">'
        f'RISK METRICS</span>',
        unsafe_allow_html=True,
    )

    metrics = [
        ("VaR (95%)", f"{var_95 * 100:.2f}%", "1-day loss not exceeded 95% of the time"),
        ("VaR (99%)", f"{var_99 * 100:.2f}%", "1-day loss not exceeded 99% of the time"),
        ("CVaR / ES (95%)", f"{es_95 * 100:.2f}%", "Expected loss beyond 95% VaR"),
        ("CVaR / ES (99%)", f"{es_99 * 100:.2f}%", "Expected loss beyond 99% VaR"),
        ("Max Drawdown", f"{max_dd * 100:.2f}%", "Largest peak-to-trough decline"),
    ]

    rows_html = ""
    for label, value, desc in metrics:
        rows_html += (
            f'<tr style="border-bottom:1px solid {COLORS["panel"]}">'
            f'<td style="padding:5px 8px;color:{COLORS["text"]};font-size:12px;font-weight:bold">{label}</td>'
            f'<td style="padding:5px 8px;text-align:right;color:{COLORS["red"]};font-family:monospace;font-size:13px;font-weight:bold">{value}</td>'
            f'</tr>'
            f'<tr>'
            f'<td colspan="2" style="padding:0 8px 6px 8px;color:{COLORS["muted"]};font-size:9px">{desc}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;border:1px solid {COLORS["border"]};'
        f'background:{COLORS["panel"]}">'
        f'<tbody>{rows_html}</tbody></table>',
        unsafe_allow_html=True,
    )


def _render_sector_allocation(symbols, weights):
    """Pie chart of sector allocation based on optimized weights."""
    st.markdown(
        f'<span style="color:{COLORS["amber"]};font-size:12px;font-weight:bold">'
        f'SECTOR ALLOCATION</span>',
        unsafe_allow_html=True,
    )

    sector_weights = {}
    for sym, w in zip(symbols, weights):
        if w < 0.001:
            continue
        sector = NIFTY_50.get(sym, "Other")
        sector_weights[sector] = sector_weights.get(sector, 0) + w

    if not sector_weights:
        st.info("No allocation to display.")
        return

    sectors = list(sector_weights.keys())
    allocs = list(sector_weights.values())
    colors = [SECTOR_COLORS.get(s, COLORS["muted"]) for s in sectors]

    fig = go.Figure(go.Pie(
        labels=sectors,
        values=allocs,
        marker=dict(colors=colors, line=dict(color=COLORS["bg"], width=2)),
        textinfo="label+percent",
        textfont=dict(size=10, color=COLORS["text"]),
        hovertemplate="<b>%{label}</b><br>Weight: %{percent}<extra></extra>",
        hole=0.45,
    ))

    fig.update_layout(**plotly_layout(
        height=320,
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
    ))

    st.plotly_chart(fig, use_container_width=True)


def _render_correlation_heatmap(returns_df):
    """Correlation matrix heatmap of selected stocks."""
    st.markdown(
        f'<span style="color:{COLORS["amber"]};font-size:12px;font-weight:bold">'
        f'RETURN CORRELATION MATRIX</span>',
        unsafe_allow_html=True,
    )

    corr = returns_df.corr()

    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.index,
        text=[[f"{v:.2f}" for v in row] for row in corr.values],
        texttemplate="%{text}",
        textfont=dict(size=10, color=COLORS["text"]),
        colorscale=[
            [0.0, "#3333CC"],
            [0.5, "#1A1A1A"],
            [1.0, "#CC3333"],
        ],
        zmid=0.0,
        zmin=-1,
        zmax=1,
        showscale=True,
        colorbar=dict(
            tickfont=dict(color=COLORS["text"], size=9),
            len=0.6,
            thickness=12,
        ),
    ))

    fig.update_layout(**plotly_layout(
        height=max(300, len(corr) * 28),
        xaxis=dict(side="bottom", tickfont=dict(size=9), tickangle=45),
        yaxis=dict(autorange="reversed", tickfont=dict(size=9)),
        margin=dict(l=70, r=20, t=10, b=70),
    ))

    st.plotly_chart(fig, use_container_width=True)
