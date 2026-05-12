"""Portfolio analytics and performance metrics."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


def trade_log_df(trades: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert list of trade dicts (from DB) into a clean DataFrame."""
    if not trades:
        return pd.DataFrame()

    df = pd.DataFrame(trades)
    for col in ["timestamp_open", "timestamp_close"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df


def compute_metrics(trades_df: pd.DataFrame, initial_capital: float = 50000) -> Dict[str, Any]:
    """Compute comprehensive performance metrics from a trades DataFrame."""
    if trades_df.empty:
        return _empty_metrics()

    closed = trades_df[trades_df["timestamp_close"].notna()].copy()
    if closed.empty:
        return _empty_metrics()

    pnls = closed["pnl"].values
    total_pnl = float(pnls.sum())
    n_trades = len(closed)
    winners = pnls[pnls > 0]
    losers = pnls[pnls <= 0]

    # Win rate
    win_rate = len(winners) / n_trades if n_trades > 0 else 0.0

    # Profit factor
    gross_profit = float(winners.sum()) if len(winners) > 0 else 0.0
    gross_loss = float(abs(losers.sum())) if len(losers) > 0 else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    # Equity curve
    closed_sorted = closed.sort_values("timestamp_close")
    equity = initial_capital + closed_sorted["pnl"].cumsum()

    # Max drawdown
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_dd = float(drawdown.min())

    # Sharpe (daily)
    if len(closed_sorted) > 1:
        closed_sorted = closed_sorted.set_index("timestamp_close")
        daily_pnl = closed_sorted["pnl"].resample("D").sum().dropna()
        daily_returns = daily_pnl / initial_capital
        if daily_returns.std() > 0:
            sharpe = float(daily_returns.mean() / daily_returns.std() * np.sqrt(365))
        else:
            sharpe = 0.0
    else:
        sharpe = 0.0

    # Average trade
    avg_win = float(winners.mean()) if len(winners) > 0 else 0.0
    avg_loss = float(losers.mean()) if len(losers) > 0 else 0.0

    # Duration
    if "timestamp_open" in closed.columns and "timestamp_close" in closed.columns:
        durations = (closed["timestamp_close"] - closed["timestamp_open"]).dt.total_seconds() / 60
        avg_duration = float(durations.mean())
    else:
        avg_duration = 0.0

    # Expectancy
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss) if n_trades > 0 else 0.0

    return {
        "total_trades": n_trades,
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "win_rate": round(win_rate, 4),
        "total_pnl": round(total_pnl, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(profit_factor, 3),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "avg_duration_minutes": round(avg_duration, 1),
        "expectancy": round(expectancy, 2),
        "final_equity": round(float(equity.iloc[-1]) if not equity.empty else initial_capital, 2),
    }


def _empty_metrics() -> Dict[str, Any]:
    return {
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate": 0.0,
        "total_pnl": 0.0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "profit_factor": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown_pct": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "avg_duration_minutes": 0.0,
        "expectancy": 0.0,
        "final_equity": 0.0,
    }
