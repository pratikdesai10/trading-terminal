"""Risk metrics computation for portfolio analysis.

Pure numpy/scipy implementations of VaR, ES, Sharpe, and drawdown calculations.
India risk-free rate default: 6.5% (approx. 10Y G-Sec yield).
"""

import numpy as np

from utils.logger import logger


# India risk-free rate (annualized)
INDIA_RISK_FREE = 0.065


def compute_var(returns, confidence=0.95):
    """Compute historical Value at Risk (VaR).

    Args:
        returns: array-like of portfolio returns (daily).
        confidence: confidence level (0.95 or 0.99).

    Returns:
        VaR as a positive float (loss magnitude at the given percentile).
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]
    if len(returns) < 2:
        logger.warning("compute_var | insufficient data")
        return 0.0
    var = -np.percentile(returns, (1 - confidence) * 100)
    logger.info(f"compute_var | confidence={confidence} | VaR={var:.6f}")
    return float(var)


def compute_es(returns, confidence=0.95):
    """Compute Expected Shortfall (CVaR / Conditional VaR).

    Average loss beyond the VaR threshold.

    Args:
        returns: array-like of portfolio returns (daily).
        confidence: confidence level (0.95 or 0.99).

    Returns:
        ES as a positive float.
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]
    if len(returns) < 2:
        logger.warning("compute_es | insufficient data")
        return 0.0
    threshold = np.percentile(returns, (1 - confidence) * 100)
    tail = returns[returns <= threshold]
    if len(tail) == 0:
        return compute_var(returns, confidence)
    es = -tail.mean()
    logger.info(f"compute_es | confidence={confidence} | ES={es:.6f}")
    return float(es)


def compute_sharpe(returns, risk_free_rate=INDIA_RISK_FREE):
    """Compute annualized Sharpe ratio.

    Args:
        returns: array-like of daily portfolio returns.
        risk_free_rate: annualized risk-free rate (default 6.5% for India).

    Returns:
        Annualized Sharpe ratio.
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]
    if len(returns) < 2:
        logger.warning("compute_sharpe | insufficient data")
        return 0.0
    daily_rf = (1 + risk_free_rate) ** (1 / 252) - 1
    excess = returns - daily_rf
    mean_excess = np.mean(excess)
    std_excess = np.std(excess, ddof=1)
    if std_excess == 0:
        return 0.0
    sharpe = (mean_excess / std_excess) * np.sqrt(252)
    logger.info(f"compute_sharpe | rf={risk_free_rate} | sharpe={sharpe:.4f}")
    return float(sharpe)


def compute_max_drawdown(returns):
    """Compute maximum drawdown from a series of returns.

    Args:
        returns: array-like of daily portfolio returns.

    Returns:
        Maximum drawdown as a positive float (e.g., 0.15 = 15% drawdown).
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]
    if len(returns) < 2:
        logger.warning("compute_max_drawdown | insufficient data")
        return 0.0
    # Build cumulative wealth index
    cum = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cum)
    drawdowns = (cum - running_max) / running_max
    max_dd = -np.min(drawdowns)
    logger.info(f"compute_max_drawdown | max_dd={max_dd:.4f}")
    return float(max_dd)


def compute_sortino(returns, risk_free_rate=INDIA_RISK_FREE):
    """Compute annualized Sortino ratio (downside deviation only).

    Args:
        returns: array-like of daily portfolio returns.
        risk_free_rate: annualized risk-free rate.

    Returns:
        Annualized Sortino ratio.
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]
    if len(returns) < 2:
        return 0.0
    daily_rf = (1 + risk_free_rate) ** (1 / 252) - 1
    excess = returns - daily_rf
    downside = excess[excess < 0]
    if len(downside) == 0:
        return 0.0
    downside_std = np.std(downside, ddof=1)
    if downside_std == 0:
        return 0.0
    sortino = (np.mean(excess) / downside_std) * np.sqrt(252)
    return float(sortino)


def compute_portfolio_returns(returns_matrix, weights):
    """Compute portfolio returns given a matrix of asset returns and weights.

    Args:
        returns_matrix: 2D array (n_days x n_assets) of daily returns.
        weights: 1D array of portfolio weights.

    Returns:
        1D array of daily portfolio returns.
    """
    returns_matrix = np.asarray(returns_matrix, dtype=float)
    weights = np.asarray(weights, dtype=float)
    return returns_matrix @ weights
