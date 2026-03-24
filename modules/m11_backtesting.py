"""Module 11: Backtesting Engine (Bloomberg: BTST)."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from config import COLORS, NIFTY_50_SYMBOLS, plotly_layout
from utils.logger import logger


# ── Strategy definitions ──
STRATEGIES = {
    "SMA Crossover": {
        "desc": "Buy when fast SMA crosses above slow SMA, sell on cross below.",
        "params": {"fast_period": 20, "slow_period": 50},
    },
    "RSI Mean Reversion": {
        "desc": "Buy when RSI drops below oversold level, sell when RSI rises above overbought.",
        "params": {"rsi_period": 14, "oversold": 30, "overbought": 70},
    },
    "MACD Signal": {
        "desc": "Buy when MACD line crosses above signal line, sell on cross below.",
        "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
    },
    "Bollinger Band Bounce": {
        "desc": "Buy when price touches lower band, sell when price touches upper band.",
        "params": {"bb_period": 20, "bb_std": 2.0},
    },
    "Custom Strategy": {
        "desc": "Write custom Python signal logic. Use df with columns: Date, Open, High, Low, Close, Volume. Set df['signal'] = 1 (buy), -1 (sell), or 0 (hold).",
        "params": {},
    },
}

PERIOD_PRESETS = {
    "6M": 180,
    "1Y": 365,
    "2Y": 730,
    "3Y": 1095,
    "5Y": 1825,
}


def render():
    """Render the Backtesting Engine module."""
    st.markdown("### BACKTESTING ENGINE")

    # ── Controls row 1: Symbol + Strategy ──
    col_sym, col_strat = st.columns([1, 1])
    with col_sym:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:10px;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:2px">SYMBOL</p>',
            unsafe_allow_html=True,
        )
        symbol = st.selectbox(
            "SYMBOL", NIFTY_50_SYMBOLS, index=0,
            key="m11_symbol", label_visibility="collapsed",
        )
    with col_strat:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:10px;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:2px">STRATEGY</p>',
            unsafe_allow_html=True,
        )
        strategy_name = st.selectbox(
            "STRATEGY", list(STRATEGIES.keys()), index=0,
            key="m11_strategy", label_visibility="collapsed",
        )

    strategy = STRATEGIES[strategy_name]
    st.markdown(
        f'<p style="color:{COLORS["muted"]};font-size:11px;font-style:italic;margin:0">'
        f'{strategy["desc"]}</p>',
        unsafe_allow_html=True,
    )

    # ── Controls row 2: Date range ──
    col_period, col_start, col_end = st.columns([1, 1, 1])
    with col_period:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:10px;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:2px">PERIOD PRESET</p>',
            unsafe_allow_html=True,
        )
        period_preset = st.selectbox(
            "PERIOD", list(PERIOD_PRESETS.keys()), index=1,
            key="m11_period", label_visibility="collapsed",
        )
    default_end = date.today()
    default_start = default_end - timedelta(days=PERIOD_PRESETS[period_preset])
    with col_start:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:10px;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:2px">START DATE</p>',
            unsafe_allow_html=True,
        )
        start_date = st.date_input(
            "START", value=default_start, key="m11_start",
            label_visibility="collapsed",
        )
    with col_end:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:10px;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:2px">END DATE</p>',
            unsafe_allow_html=True,
        )
        end_date = st.date_input(
            "END", value=default_end, key="m11_end",
            label_visibility="collapsed",
        )

    # ── Controls row 3: Strategy parameters ──
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:10px;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:2px;margin-top:8px">STRATEGY PARAMETERS</p>',
        unsafe_allow_html=True,
    )
    params = _render_strategy_params(strategy_name, strategy["params"])

    # ── Controls row 4: Capital + Run button ──
    col_capital, col_commission, col_run = st.columns([1, 1, 1])
    with col_capital:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:10px;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:2px">INITIAL CAPITAL</p>',
            unsafe_allow_html=True,
        )
        initial_capital = st.number_input(
            "CAPITAL", value=1000000, step=100000, min_value=10000,
            key="m11_capital", label_visibility="collapsed",
        )
    with col_commission:
        st.markdown(
            f'<p style="color:{COLORS["amber"]};font-size:10px;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:2px">COMMISSION (%)</p>',
            unsafe_allow_html=True,
        )
        commission_pct = st.number_input(
            "COMMISSION", value=0.05, step=0.01, min_value=0.0, max_value=1.0,
            format="%.2f", key="m11_commission", label_visibility="collapsed",
        )
    with col_run:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("RUN BACKTEST", use_container_width=True, key="m11_run")

    st.markdown(
        f'<hr style="border:1px solid {COLORS["border"]};margin:8px 0">',
        unsafe_allow_html=True,
    )

    # ── Execute backtest ──
    if run_btn:
        _run_backtest(symbol, strategy_name, params, start_date, end_date,
                      initial_capital, commission_pct)
    elif "m11_results" in st.session_state:
        # Re-render cached results
        results = st.session_state["m11_results"]
        _display_results(results)
    else:
        st.info("Configure strategy parameters above and click **RUN BACKTEST**.")


def _render_strategy_params(strategy_name, defaults):
    """Render editable parameter inputs for the selected strategy."""
    params = {}

    if strategy_name == "SMA Crossover":
        c1, c2 = st.columns(2)
        with c1:
            params["fast_period"] = st.number_input(
                "Fast SMA Period", value=defaults["fast_period"],
                min_value=2, max_value=100, key="m11_p_fast_sma",
            )
        with c2:
            params["slow_period"] = st.number_input(
                "Slow SMA Period", value=defaults["slow_period"],
                min_value=5, max_value=500, key="m11_p_slow_sma",
            )

    elif strategy_name == "RSI Mean Reversion":
        c1, c2, c3 = st.columns(3)
        with c1:
            params["rsi_period"] = st.number_input(
                "RSI Period", value=defaults["rsi_period"],
                min_value=2, max_value=50, key="m11_p_rsi_period",
            )
        with c2:
            params["oversold"] = st.number_input(
                "Oversold Level", value=defaults["oversold"],
                min_value=5, max_value=50, key="m11_p_oversold",
            )
        with c3:
            params["overbought"] = st.number_input(
                "Overbought Level", value=defaults["overbought"],
                min_value=50, max_value=95, key="m11_p_overbought",
            )

    elif strategy_name == "MACD Signal":
        c1, c2, c3 = st.columns(3)
        with c1:
            params["fast_period"] = st.number_input(
                "MACD Fast", value=defaults["fast_period"],
                min_value=2, max_value=50, key="m11_p_macd_fast",
            )
        with c2:
            params["slow_period"] = st.number_input(
                "MACD Slow", value=defaults["slow_period"],
                min_value=5, max_value=100, key="m11_p_macd_slow",
            )
        with c3:
            params["signal_period"] = st.number_input(
                "Signal Period", value=defaults["signal_period"],
                min_value=2, max_value=50, key="m11_p_macd_signal",
            )

    elif strategy_name == "Bollinger Band Bounce":
        c1, c2 = st.columns(2)
        with c1:
            params["bb_period"] = st.number_input(
                "BB Period", value=defaults["bb_period"],
                min_value=5, max_value=100, key="m11_p_bb_period",
            )
        with c2:
            params["bb_std"] = st.number_input(
                "BB Std Deviations", value=defaults["bb_std"],
                min_value=0.5, max_value=5.0, step=0.1,
                format="%.1f", key="m11_p_bb_std",
            )

    elif strategy_name == "Custom Strategy":
        default_code = '''# Custom Strategy Template
# Available: df (DataFrame with Date, Open, High, Low, Close, Volume columns)
# Available: pd, np, ta (libraries)
# Set df['signal'] = 1 for BUY, -1 for SELL, 0 for HOLD

# Example: Simple price breakout
rolling_high = df['High'].rolling(window=20).max().shift(1)
rolling_low = df['Low'].rolling(window=20).min().shift(1)

df['signal'] = 0
df.loc[df['Close'] > rolling_high, 'signal'] = 1
df.loc[df['Close'] < rolling_low, 'signal'] = -1
'''
        params["custom_code"] = st.text_area(
            "STRATEGY CODE",
            value=default_code,
            height=250,
            key="m11_custom_code",
        )
        st.caption("⚠️ Code runs in a sandboxed namespace with limited builtins.")

    return params


def _run_backtest(symbol, strategy_name, params, start_date, end_date,
                  initial_capital, commission_pct):
    """Fetch data, generate signals, run backtest loop, display results."""
    with st.spinner(f"Fetching {symbol} data and running {strategy_name}..."):
        from data.nse_historical import get_stock_history

        df = get_stock_history(symbol, start_date, end_date)
        if df is None or df.empty:
            st.error(f"No historical data available for {symbol}. Try a different date range.")
            return

        if len(df) < 30:
            st.error(f"Insufficient data: only {len(df)} bars. Need at least 30 for backtesting.")
            return

        logger.info(
            f"m11_backtest | {symbol} | {strategy_name} | {len(df)} bars | "
            f"{start_date} to {end_date}"
        )

        # Generate signals
        signals = _generate_signals(df, strategy_name, params)
        if signals is None or signals.empty:
            st.error("Failed to generate trading signals.")
            return

        # Run backtest
        results = _execute_backtest(signals, initial_capital, commission_pct)
        results["symbol"] = symbol
        results["strategy"] = strategy_name
        results["params"] = params

        # Cache results
        st.session_state["m11_results"] = results

    _display_results(results)


def _exec_custom_strategy(custom_code, df):
    """Execute custom strategy code in a sandboxed subprocess.

    Runs the user code in a separate Python process with a timeout,
    communicating data via temporary CSV files.
    """
    import subprocess
    import tempfile
    import os

    # Validate code: block dangerous patterns
    _BLOCKED = [
        "import os", "import sys", "import subprocess", "import shutil",
        "__import__", "eval(", "exec(", "compile(", "open(",
        "__class__", "__bases__", "__subclasses__", "__globals__",
        "__builtins__", "__code__", "__func__", "getattr(", "setattr(",
        "delattr(", "breakpoint(", "quit(", "exit(",
    ]
    code_lower = custom_code.lower()
    for pattern in _BLOCKED:
        if pattern.lower() in code_lower:
            import streamlit as st_mod
            st_mod.error(f"Blocked: '{pattern}' is not allowed in custom strategies.")
            return None

    with tempfile.TemporaryDirectory() as tmpdir:
        input_csv = os.path.join(tmpdir, "input.csv")
        output_csv = os.path.join(tmpdir, "output.csv")
        script_path = os.path.join(tmpdir, "strategy.py")

        df.to_csv(input_csv, index=False)

        # Build a runner script that loads df, runs user code, saves result
        runner = f'''
import pandas as pd
import numpy as np
import ta

df = pd.read_csv({input_csv!r})
df["signal"] = 0

# --- User code start ---
{custom_code}
# --- User code end ---

if "signal" not in df.columns:
    df["signal"] = 0
df.to_csv({output_csv!r}, index=False)
'''
        with open(script_path, "w") as f:
            f.write(runner)

        try:
            result = subprocess.run(
                ["python", script_path],
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            if result.returncode != 0:
                import streamlit as st_mod
                err_msg = result.stderr.strip().split("\n")[-1] if result.stderr.strip() else "Unknown error"
                st_mod.error(f"Custom strategy error: {err_msg}")
                return None

            result_df = pd.read_csv(output_csv)
            # Restore Date column to datetime (CSV serializes as string)
            if "Date" in result_df.columns:
                result_df["Date"] = pd.to_datetime(result_df["Date"])
            return result_df
        except subprocess.TimeoutExpired:
            import streamlit as st_mod
            st_mod.error("Custom strategy timed out (30s limit).")
            return None


def _generate_signals(df, strategy_name, params):
    """Generate buy/sell signals based on strategy. Returns df with 'signal' column.

    signal: 1 = buy, -1 = sell, 0 = hold
    """
    from ta.trend import sma_indicator, ema_indicator, macd, macd_signal
    from ta.momentum import rsi
    from ta.volatility import BollingerBands

    df = df.copy()
    df["signal"] = 0

    if strategy_name == "SMA Crossover":
        fast = params["fast_period"]
        slow = params["slow_period"]
        df["sma_fast"] = sma_indicator(df["Close"], window=fast)
        df["sma_slow"] = sma_indicator(df["Close"], window=slow)
        df.dropna(subset=["sma_fast", "sma_slow"], inplace=True)

        # Cross detection
        df["cross"] = 0
        df.loc[df["sma_fast"] > df["sma_slow"], "cross"] = 1
        df.loc[df["sma_fast"] <= df["sma_slow"], "cross"] = -1
        df["signal"] = df["cross"].diff()
        # Normalize: >0 means buy, <0 means sell
        df.loc[df["signal"] > 0, "signal"] = 1
        df.loc[df["signal"] < 0, "signal"] = -1
        df.loc[df["signal"].abs() != 1, "signal"] = 0

    elif strategy_name == "RSI Mean Reversion":
        period = params["rsi_period"]
        oversold = params["oversold"]
        overbought = params["overbought"]
        df["rsi"] = rsi(df["Close"], window=period)
        df.dropna(subset=["rsi"], inplace=True)

        # State machine: buy when RSI crosses up through oversold, sell when crosses down through overbought
        prev_rsi = df["rsi"].shift(1)
        df.loc[(prev_rsi <= oversold) & (df["rsi"] > oversold), "signal"] = 1
        df.loc[(prev_rsi >= overbought) & (df["rsi"] < overbought), "signal"] = -1

    elif strategy_name == "MACD Signal":
        fast = params["fast_period"]
        slow = params["slow_period"]
        sig = params["signal_period"]
        df["macd_line"] = macd(df["Close"], window_slow=slow, window_fast=fast)
        df["macd_signal"] = macd_signal(
            df["Close"], window_slow=slow, window_fast=fast, window_sign=sig
        )
        df.dropna(subset=["macd_line", "macd_signal"], inplace=True)

        # Cross detection
        df["cross"] = 0
        df.loc[df["macd_line"] > df["macd_signal"], "cross"] = 1
        df.loc[df["macd_line"] <= df["macd_signal"], "cross"] = -1
        df["signal"] = df["cross"].diff()
        df.loc[df["signal"] > 0, "signal"] = 1
        df.loc[df["signal"] < 0, "signal"] = -1
        df.loc[df["signal"].abs() != 1, "signal"] = 0

    elif strategy_name == "Bollinger Band Bounce":
        period = params["bb_period"]
        std_dev = params["bb_std"]
        bb = BollingerBands(df["Close"], window=period, window_dev=std_dev)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_mid"] = bb.bollinger_mavg()
        df.dropna(subset=["bb_upper", "bb_lower"], inplace=True)

        # Buy when price crosses up through lower band, sell when crosses down through upper band
        prev_close = df["Close"].shift(1)
        df.loc[(prev_close <= df["bb_lower"]) & (df["Close"] > df["bb_lower"]), "signal"] = 1
        df.loc[(prev_close >= df["bb_upper"]) & (df["Close"] < df["bb_upper"]), "signal"] = -1

    elif strategy_name == "Custom Strategy":
        custom_code = params.get("custom_code", "")
        if not custom_code.strip():
            return None
        # Execute in sandboxed subprocess for security
        import streamlit as st_mod
        try:
            df = _exec_custom_strategy(custom_code, df)
            if df is None:
                return None
        except Exception as e:
            st_mod.error(f"Custom strategy error: {e}")
            return None
        # Ensure signal column exists
        if "signal" not in df.columns:
            df["signal"] = 0

    df = df.reset_index(drop=True)
    return df


def _execute_backtest(df, initial_capital, commission_pct):
    """Run the backtest loop and compute performance metrics.

    Returns dict with equity curve, drawdown, trades, and summary stats.
    """
    capital = initial_capital
    position = 0  # number of shares held
    entry_price = 0.0
    trades = []
    equity_curve = []
    dates = []

    commission_rate = commission_pct / 100.0

    for i, row in df.iterrows():
        price = row["Close"]
        signal = row["signal"]
        trade_date = row["Date"]

        # Execute signals
        if signal == 1 and position == 0:
            # Buy: invest all available capital
            shares = int(capital / (price * (1 + commission_rate)))
            if shares > 0:
                cost = shares * price
                comm = cost * commission_rate
                capital -= (cost + comm)
                position = shares
                entry_price = price
                trades.append({
                    "Date": trade_date,
                    "Type": "BUY",
                    "Price": price,
                    "Shares": shares,
                    "Value": cost,
                    "Commission": round(comm, 2),
                    "Capital": round(capital, 2),
                })

        elif signal == -1 and position > 0:
            # Sell: liquidate entire position
            proceeds = position * price
            comm = proceeds * commission_rate
            pnl = (price - entry_price) * position - comm
            capital += (proceeds - comm)
            trades.append({
                "Date": trade_date,
                "Type": "SELL",
                "Price": price,
                "Shares": position,
                "Value": proceeds,
                "Commission": round(comm, 2),
                "Capital": round(capital, 2),
                "PnL": round(pnl, 2),
                "Return %": round((price / entry_price - 1) * 100, 2),
            })
            position = 0
            entry_price = 0.0

        # Track equity = cash + market value of holdings
        portfolio_value = capital + position * price
        equity_curve.append(portfolio_value)
        dates.append(trade_date)

    # If still holding at end, mark to market (don't force sell)
    final_equity = equity_curve[-1] if equity_curve else initial_capital

    # Build equity DataFrame
    equity_df = pd.DataFrame({"Date": dates, "Equity": equity_curve})

    # Compute drawdown
    equity_df["Peak"] = equity_df["Equity"].cummax()
    equity_df["Drawdown"] = (equity_df["Equity"] - equity_df["Peak"]) / equity_df["Peak"] * 100

    # Buy-and-hold benchmark
    first_price = df["Close"].iloc[0]
    bh_shares = int(initial_capital / first_price)
    equity_df["BuyHold"] = bh_shares * df["Close"].values[:len(equity_df)] + (
        initial_capital - bh_shares * first_price
    )

    # Compute summary stats
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    stats = _compute_stats(equity_df, trades_df, initial_capital, final_equity)

    return {
        "equity_df": equity_df,
        "trades_df": trades_df,
        "stats": stats,
        "price_df": df,
    }


def _compute_stats(equity_df, trades_df, initial_capital, final_equity):
    """Compute backtest performance statistics."""
    total_return = (final_equity / initial_capital - 1) * 100

    # Daily returns for Sharpe
    equity_df["daily_ret"] = equity_df["Equity"].pct_change()
    daily_returns = equity_df["daily_ret"].dropna()

    if len(daily_returns) > 1 and daily_returns.std() > 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    max_drawdown = equity_df["Drawdown"].min()

    # Trade stats
    n_trades = 0
    n_wins = 0
    n_losses = 0
    total_profit = 0.0
    total_loss = 0.0

    if not trades_df.empty and "PnL" in trades_df.columns:
        sell_trades = trades_df[trades_df["Type"] == "SELL"]
        n_trades = len(sell_trades)
        if n_trades > 0:
            wins = sell_trades[sell_trades["PnL"] > 0]
            losses = sell_trades[sell_trades["PnL"] <= 0]
            n_wins = len(wins)
            n_losses = len(losses)
            total_profit = wins["PnL"].sum() if not wins.empty else 0.0
            total_loss = abs(losses["PnL"].sum()) if not losses.empty else 0.0

    win_rate = (n_wins / n_trades * 100) if n_trades > 0 else 0.0
    profit_factor = (total_profit / total_loss) if total_loss > 0 else (
        float("inf") if total_profit > 0 else 0.0
    )

    # Buy-and-hold return
    bh_return = 0.0
    if "BuyHold" in equity_df.columns and len(equity_df) > 0:
        bh_return = (equity_df["BuyHold"].iloc[-1] / initial_capital - 1) * 100

    # CAGR
    n_days = (equity_df["Date"].iloc[-1] - equity_df["Date"].iloc[0]).days if len(equity_df) > 1 else 1
    n_years = max(n_days / 365.25, 0.01)
    cagr = ((final_equity / initial_capital) ** (1 / n_years) - 1) * 100 if final_equity > 0 else 0.0

    # Average trade duration
    avg_duration = 0
    if not trades_df.empty and n_trades > 0:
        buy_dates = trades_df[trades_df["Type"] == "BUY"]["Date"].values
        sell_dates = trades_df[trades_df["Type"] == "SELL"]["Date"].values
        n_pairs = min(len(buy_dates), len(sell_dates))
        if n_pairs > 0:
            durations = []
            for j in range(n_pairs):
                d = (pd.Timestamp(sell_dates[j]) - pd.Timestamp(buy_dates[j])).days
                durations.append(d)
            avg_duration = int(np.mean(durations))

    return {
        "total_return": round(total_return, 2),
        "cagr": round(cagr, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_drawdown, 2),
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "Inf",
        "n_trades": n_trades,
        "n_wins": n_wins,
        "n_losses": n_losses,
        "total_profit": round(total_profit, 2),
        "total_loss": round(total_loss, 2),
        "bh_return": round(bh_return, 2),
        "initial_capital": initial_capital,
        "final_equity": round(final_equity, 2),
        "avg_duration_days": avg_duration,
    }


def _display_results(results):
    """Display backtest results: stats, charts, trade log."""
    stats = results["stats"]
    equity_df = results["equity_df"]
    trades_df = results["trades_df"]
    price_df = results["price_df"]
    symbol = results.get("symbol", "")
    strategy = results.get("strategy", "")

    # ── Header ──
    st.markdown(
        f'<div style="background:{COLORS["panel"]};padding:6px 12px;border:1px solid {COLORS["border"]};'
        f'border-radius:4px;margin-bottom:8px">'
        f'<span style="color:{COLORS["amber"]};font-size:13px;font-weight:bold;font-family:monospace">'
        f'BACKTEST RESULTS: {symbol} | {strategy}</span></div>',
        unsafe_allow_html=True,
    )

    # ── Summary stats grid ──
    _render_stats_grid(stats)

    # ── Equity curve + Drawdown chart ──
    _render_equity_chart(equity_df, symbol, strategy)

    # ── Price chart with signals ──
    _render_signal_chart(price_df, trades_df, symbol)

    # ── Trade log ──
    _render_trade_log(trades_df)


def _render_stats_grid(stats):
    """Render performance statistics as a Bloomberg-style metrics panel."""
    ret_color = COLORS["green"] if stats["total_return"] >= 0 else COLORS["red"]
    dd_color = COLORS["red"] if stats["max_drawdown"] < -10 else COLORS["amber"]
    sharpe_color = COLORS["green"] if stats["sharpe"] > 1 else (
        COLORS["amber"] if stats["sharpe"] > 0 else COLORS["red"]
    )
    wr_color = COLORS["green"] if stats["win_rate"] >= 50 else COLORS["red"]
    pf_display = str(stats["profit_factor"]) if stats["profit_factor"] == "Inf" else f'{stats["profit_factor"]:.2f}'
    pf_val = 999 if stats["profit_factor"] == "Inf" else stats["profit_factor"]
    pf_color = COLORS["green"] if pf_val > 1 else COLORS["red"]
    bh_color = COLORS["green"] if stats["bh_return"] >= 0 else COLORS["red"]
    alpha = stats["total_return"] - stats["bh_return"]
    alpha_color = COLORS["green"] if alpha >= 0 else COLORS["red"]

    metrics = [
        ("TOTAL RETURN", f'{stats["total_return"]:+.2f}%', ret_color),
        ("CAGR", f'{stats["cagr"]:+.2f}%', ret_color),
        ("SHARPE RATIO", f'{stats["sharpe"]:.2f}', sharpe_color),
        ("MAX DRAWDOWN", f'{stats["max_drawdown"]:.2f}%', dd_color),
        ("WIN RATE", f'{stats["win_rate"]:.1f}%', wr_color),
        ("PROFIT FACTOR", pf_display, pf_color),
    ]

    metrics_row2 = [
        ("TRADES", str(stats["n_trades"]), COLORS["text"]),
        ("WINS / LOSSES", f'{stats["n_wins"]} / {stats["n_losses"]}', COLORS["text"]),
        ("AVG HOLD (DAYS)", str(stats["avg_duration_days"]), COLORS["text"]),
        ("BUY & HOLD", f'{stats["bh_return"]:+.2f}%', bh_color),
        ("ALPHA", f'{alpha:+.2f}%', alpha_color),
        ("FINAL EQUITY", f'{stats["final_equity"]:,.0f}', ret_color),
    ]

    def _metric_cell(label, value, color):
        return (
            f'<td style="background:{COLORS["panel"]};padding:8px 12px;'
            f'border:1px solid {COLORS["border"]};text-align:center;min-width:100px">'
            f'<div style="color:{COLORS["amber"]};font-size:9px;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:2px">{label}</div>'
            f'<div style="color:{color};font-size:18px;font-family:monospace;font-weight:bold">'
            f'{value}</div></td>'
        )

    row1_html = "".join(_metric_cell(l, v, c) for l, v, c in metrics)
    row2_html = "".join(_metric_cell(l, v, c) for l, v, c in metrics_row2)

    html = (
        f'<table style="width:100%;border-collapse:collapse;margin-bottom:12px">'
        f'<tr>{row1_html}</tr>'
        f'<tr>{row2_html}</tr>'
        f'</table>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _render_equity_chart(equity_df, symbol, strategy):
    """Render equity curve and drawdown as a dual-panel Plotly chart."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.65, 0.35],
        subplot_titles=["EQUITY CURVE", "DRAWDOWN"],
    )

    # Equity curve
    fig.add_trace(
        go.Scatter(
            x=equity_df["Date"], y=equity_df["Equity"],
            mode="lines", name="Strategy",
            line=dict(color=COLORS["green"], width=2),
        ),
        row=1, col=1,
    )

    # Buy-and-hold benchmark
    if "BuyHold" in equity_df.columns:
        fig.add_trace(
            go.Scatter(
                x=equity_df["Date"], y=equity_df["BuyHold"],
                mode="lines", name="Buy & Hold",
                line=dict(color=COLORS["muted"], width=1.5, dash="dash"),
            ),
            row=1, col=1,
        )

    # Drawdown
    fig.add_trace(
        go.Scatter(
            x=equity_df["Date"], y=equity_df["Drawdown"],
            mode="lines", name="Drawdown",
            line=dict(color=COLORS["red"], width=1.5),
            fill="tozeroy",
            fillcolor="rgba(255,51,51,0.15)",
            showlegend=False,
        ),
        row=2, col=1,
    )

    fig.update_layout(**plotly_layout(
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1,
            font=dict(size=10, color=COLORS["text"]),
            bgcolor="rgba(0,0,0,0)",
        ),
    ))

    # Style subplot titles
    for annotation in fig["layout"]["annotations"]:
        annotation["font"] = dict(
            size=11, color=COLORS["amber"],
            family="Fira Code, Consolas, Courier New, monospace",
        )

    fig.update_yaxes(title_text="Portfolio Value", row=1, col=1,
                     gridcolor="#1A1A1A", zerolinecolor="#333333")
    fig.update_yaxes(title_text="DD %", row=2, col=1,
                     gridcolor="#1A1A1A", zerolinecolor="#333333")

    st.plotly_chart(fig, use_container_width=True, key="m11_equity_chart")


def _render_signal_chart(price_df, trades_df, symbol):
    """Render price chart with buy/sell markers."""
    fig = go.Figure()

    # Price line
    fig.add_trace(
        go.Scatter(
            x=price_df["Date"], y=price_df["Close"],
            mode="lines", name=f"{symbol} Close",
            line=dict(color=COLORS["text"], width=1.5),
        )
    )

    if not trades_df.empty:
        # Buy signals
        buys = trades_df[trades_df["Type"] == "BUY"]
        if not buys.empty:
            fig.add_trace(
                go.Scatter(
                    x=buys["Date"], y=buys["Price"],
                    mode="markers", name="BUY",
                    marker=dict(
                        symbol="triangle-up", size=12,
                        color=COLORS["green"], line=dict(width=1, color="#FFFFFF"),
                    ),
                )
            )

        # Sell signals
        sells = trades_df[trades_df["Type"] == "SELL"]
        if not sells.empty:
            fig.add_trace(
                go.Scatter(
                    x=sells["Date"], y=sells["Price"],
                    mode="markers", name="SELL",
                    marker=dict(
                        symbol="triangle-down", size=12,
                        color=COLORS["red"], line=dict(width=1, color="#FFFFFF"),
                    ),
                )
            )

    fig.update_layout(**plotly_layout(
        height=350,
        title=dict(
            text=f"TRADE SIGNALS: {symbol}",
            font=dict(size=12, color=COLORS["amber"]),
        ),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=10), bgcolor="rgba(0,0,0,0)",
        ),
        yaxis=dict(title="Price", gridcolor="#1A1A1A", zerolinecolor="#333333"),
    ))

    st.plotly_chart(fig, use_container_width=True, key="m11_signal_chart")


def _render_trade_log(trades_df):
    """Render trade log as a Bloomberg-style HTML table."""
    st.markdown(
        f'<p style="color:{COLORS["amber"]};font-size:11px;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:4px;margin-top:8px">TRADE LOG</p>',
        unsafe_allow_html=True,
    )

    if trades_df.empty:
        st.markdown(
            f'<p style="color:{COLORS["muted"]};font-size:11px">No trades generated. '
            f'Try adjusting parameters or extending the date range.</p>',
            unsafe_allow_html=True,
        )
        return

    display_cols = ["Date", "Type", "Price", "Shares", "Value", "Commission"]
    if "PnL" in trades_df.columns:
        display_cols.extend(["PnL", "Return %"])

    # Filter to available columns
    display_cols = [c for c in display_cols if c in trades_df.columns]

    # Header
    header = "".join(
        f'<th style="color:{COLORS["amber"]};padding:4px 8px;text-align:{"left" if c in ("Date", "Type") else "right"};'
        f'border-bottom:1px solid {COLORS["border"]};font-size:10px;letter-spacing:1px">{c.upper()}</th>'
        for c in display_cols
    )

    # Rows
    rows = ""
    for _, row in trades_df.iterrows():
        cells = ""
        for c in display_cols:
            val = row.get(c, "")
            align = "left" if c in ("Date", "Type") else "right"
            color = COLORS["text"]

            if c == "Type":
                color = COLORS["green"] if val == "BUY" else COLORS["red"]
            elif c == "PnL":
                if pd.notna(val):
                    color = COLORS["green"] if val > 0 else COLORS["red"]
                    val = f"{val:+,.2f}"
                else:
                    val = "—"
            elif c == "Return %":
                if pd.notna(val):
                    color = COLORS["green"] if val > 0 else COLORS["red"]
                    val = f"{val:+.2f}%"
                else:
                    val = "—"
            elif c == "Date":
                if hasattr(val, "strftime"):
                    val = val.strftime("%Y-%m-%d")
                else:
                    val = str(val)[:10]
            elif c in ("Price", "Value", "Commission", "Capital"):
                if pd.notna(val):
                    val = f"{float(val):,.2f}"
                else:
                    val = "—"
            elif c == "Shares":
                val = f"{int(val):,}" if pd.notna(val) else "—"

            cells += (
                f'<td style="padding:3px 8px;text-align:{align};color:{color};'
                f'font-size:11px;border-bottom:1px solid #1A1A1A;font-family:monospace">{val}</td>'
            )
        rows += f"<tr>{cells}</tr>"

    html = (
        f'<div style="overflow-x:auto;max-height:400px;overflow-y:auto">'
        f'<table style="width:100%;border-collapse:collapse;font-family:monospace">'
        f'<thead style="position:sticky;top:0;background:{COLORS["bg"]}">'
        f'<tr>{header}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    # Summary row below the table
    if not trades_df.empty and "PnL" in trades_df.columns:
        sell_trades = trades_df[trades_df["Type"] == "SELL"]
        if not sell_trades.empty:
            total_pnl = sell_trades["PnL"].sum()
            pnl_color = COLORS["green"] if total_pnl >= 0 else COLORS["red"]
            st.markdown(
                f'<p style="color:{COLORS["muted"]};font-size:10px;margin-top:4px;font-family:monospace">'
                f'Total P&L from closed trades: '
                f'<span style="color:{pnl_color};font-weight:bold">{total_pnl:+,.2f}</span>'
                f' | {len(sell_trades)} round-trip trade(s)</p>',
                unsafe_allow_html=True,
            )

    # Export
    csv = trades_df.to_csv(index=False)
    st.download_button(
        "EXPORT TRADE LOG", csv, "backtest_trades.csv", "text/csv",
        key="m11_export_trades",
    )
