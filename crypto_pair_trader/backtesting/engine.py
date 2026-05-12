"""Intraday backtesting engine with full trade simulation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config import Config
from pair_selection.selector import PairSelector
from pair_selection.spread import SpreadEngine
from strategies.mean_reversion import Action, MeanReversionStrategy
from utils.log import get_logger
from utils.types import PairScore, Side, TradeRecord

log = get_logger(__name__)


@dataclass
class BacktestTrade:
    trade_id: str
    leg_a: str
    leg_b: str
    side_a: Side
    side_b: Side
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price_a: float = 0.0
    entry_price_b: float = 0.0
    exit_price_a: float = 0.0
    exit_price_b: float = 0.0
    qty_a: float = 0.0
    qty_b: float = 0.0
    pnl: float = 0.0
    commission: float = 0.0
    exit_reason: str = ""
    hedge_ratio: float = 1.0
    zscore_entry: float = 0.0
    zscore_exit: float = 0.0


@dataclass
class BacktestResult:
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    params: Dict = field(default_factory=dict)

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def winning_trades(self) -> int:
        return sum(1 for t in self.trades if t.pnl > 0)

    @property
    def losing_trades(self) -> int:
        return sum(1 for t in self.trades if t.pnl <= 0)

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.trades)

    @property
    def gross_profit(self) -> float:
        return sum(t.pnl for t in self.trades if t.pnl > 0)

    @property
    def gross_loss(self) -> float:
        return abs(sum(t.pnl for t in self.trades if t.pnl <= 0))

    @property
    def profit_factor(self) -> float:
        if self.gross_loss == 0:
            return float("inf") if self.gross_profit > 0 else 0.0
        return self.gross_profit / self.gross_loss

    @property
    def max_drawdown(self) -> float:
        if self.equity_curve.empty:
            return 0.0
        running_max = self.equity_curve.cummax()
        dd = (self.equity_curve - running_max) / running_max
        return float(dd.min())

    @property
    def sharpe_ratio(self) -> float:
        if self.equity_curve.empty or len(self.equity_curve) < 2:
            return 0.0
        returns = self.equity_curve.pct_change().dropna()
        if returns.std() == 0:
            return 0.0
        # Annualise assuming 5m bars, ~288 bars/day, ~365 days
        periods_per_year = 288 * 365
        return float(returns.mean() / returns.std() * np.sqrt(periods_per_year))

    @property
    def avg_trade_duration_minutes(self) -> float:
        durations = []
        for t in self.trades:
            if t.exit_time and t.entry_time:
                durations.append((t.exit_time - t.entry_time).total_seconds() / 60)
        return np.mean(durations) if durations else 0.0

    def summary(self) -> Dict:
        return {
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 4),
            "total_pnl": round(self.total_pnl, 2),
            "profit_factor": round(self.profit_factor, 3),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "max_drawdown": round(self.max_drawdown, 4),
            "gross_profit": round(self.gross_profit, 2),
            "gross_loss": round(self.gross_loss, 2),
            "avg_trade_duration_min": round(self.avg_trade_duration_minutes, 1),
            "final_equity": round(float(self.equity_curve.iloc[-1]), 2) if not self.equity_curve.empty else 0.0,
        }


class BacktestEngine:
    """
    Event-driven backtest engine.

    Replays candle data bar-by-bar, using the same strategy logic as live.
    """

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.bt = cfg.backtest
        self.strategy = MeanReversionStrategy(cfg)
        self.spread_engine = SpreadEngine(cfg)
        self.pair_selector = PairSelector(cfg)

    def run(
        self,
        pair: PairScore,
        data_a: pd.DataFrame,
        data_b: pd.DataFrame,
    ) -> BacktestResult:
        """
        Run backtest on a single pair.

        Parameters
        ----------
        pair : PairScore from pair selection
        data_a, data_b : DataFrames with datetime index, 'close', 'volume' columns
        """
        log.info("BACKTEST START %s / %s", pair.leg_a, pair.leg_b)

        # Align data
        merged = pd.merge(
            data_a[["close", "volume"]].rename(columns={"close": "close_a", "volume": "vol_a"}),
            data_b[["close", "volume"]].rename(columns={"close": "close_b", "volume": "vol_b"}),
            left_index=True, right_index=True, how="inner",
        )

        if len(merged) < self.cfg.strategy.lookback * 2:
            log.warning("Insufficient data for backtest")
            return BacktestResult()

        # Initialise spread engine with warmup period
        warmup = self.cfg.strategy.lookback
        warmup_a = merged["close_a"].iloc[:warmup]
        warmup_b = merged["close_b"].iloc[:warmup]
        self.spread_engine.init_pair(
            pair.leg_a, pair.leg_b, warmup_a, warmup_b, pair.hedge_ratio
        )

        capital = self.bt.initial_capital
        equity_points = []
        trades: List[BacktestTrade] = []
        open_trade: Optional[BacktestTrade] = None

        comm_rate = self.bt.commission_bps / 10000
        slip_rate = self.bt.slippage_bps / 10000

        for i in range(warmup, len(merged)):
            row = merged.iloc[i]
            ts = merged.index[i]
            price_a = row["close_a"]
            price_b = row["close_b"]

            # Update spread
            state = self.spread_engine.update(
                pair.leg_a, pair.leg_b, price_a, price_b,
                timestamp=ts,
            )
            if state is None:
                continue

            now = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts

            # Evaluate strategy
            action = self.strategy.evaluate(state, now)

            if action in (Action.ENTER_LONG_SPREAD, Action.ENTER_SHORT_SPREAD) and open_trade is None:
                # Size: use max_position_usd
                notional = min(
                    self.cfg.risk.max_position_usd,
                    capital * self.cfg.risk.max_pair_exposure_pct,
                )
                qty_a = notional / price_a
                qty_b = notional / price_b

                # Apply slippage
                if action == Action.ENTER_LONG_SPREAD:
                    ep_a = price_a * (1 + slip_rate)
                    ep_b = price_b * (1 - slip_rate)
                    side_a, side_b = Side.LONG, Side.SHORT
                else:
                    ep_a = price_a * (1 - slip_rate)
                    ep_b = price_b * (1 + slip_rate)
                    side_a, side_b = Side.SHORT, Side.LONG

                open_trade = BacktestTrade(
                    trade_id=str(uuid.uuid4())[:8],
                    leg_a=pair.leg_a,
                    leg_b=pair.leg_b,
                    side_a=side_a,
                    side_b=side_b,
                    entry_time=now,
                    entry_price_a=ep_a,
                    entry_price_b=ep_b,
                    qty_a=qty_a,
                    qty_b=qty_b,
                    hedge_ratio=state.hedge_ratio,
                    zscore_entry=state.zscore,
                )
                self.strategy.register_entry(state, action, now)

                # Entry commission
                entry_comm = (qty_a * ep_a + qty_b * ep_b) * comm_rate
                capital -= entry_comm
                open_trade.commission += entry_comm

            elif action not in (Action.HOLD, Action.ENTER_LONG_SPREAD, Action.ENTER_SHORT_SPREAD) and open_trade is not None:
                # Close trade
                if open_trade.side_a == Side.LONG:
                    xp_a = price_a * (1 - slip_rate)
                    xp_b = price_b * (1 + slip_rate)
                else:
                    xp_a = price_a * (1 + slip_rate)
                    xp_b = price_b * (1 - slip_rate)

                # PnL
                if open_trade.side_a == Side.LONG:
                    pnl_a = (xp_a - open_trade.entry_price_a) * open_trade.qty_a
                else:
                    pnl_a = (open_trade.entry_price_a - xp_a) * open_trade.qty_a

                if open_trade.side_b == Side.LONG:
                    pnl_b = (xp_b - open_trade.entry_price_b) * open_trade.qty_b
                else:
                    pnl_b = (open_trade.entry_price_b - xp_b) * open_trade.qty_b

                exit_comm = (open_trade.qty_a * xp_a + open_trade.qty_b * xp_b) * comm_rate
                total_pnl = pnl_a + pnl_b - exit_comm

                open_trade.exit_time = now
                open_trade.exit_price_a = xp_a
                open_trade.exit_price_b = xp_b
                open_trade.pnl = total_pnl
                open_trade.commission += exit_comm
                open_trade.exit_reason = action.value
                open_trade.zscore_exit = state.zscore

                capital += total_pnl
                trades.append(open_trade)
                open_trade = None
                self.strategy.register_exit(pair.leg_a, pair.leg_b, action.value)

            equity_points.append((ts, capital))

        # Force close any open trade at end
        if open_trade is not None:
            last_row = merged.iloc[-1]
            xp_a = last_row["close_a"]
            xp_b = last_row["close_b"]
            if open_trade.side_a == Side.LONG:
                pnl_a = (xp_a - open_trade.entry_price_a) * open_trade.qty_a
            else:
                pnl_a = (open_trade.entry_price_a - xp_a) * open_trade.qty_a
            if open_trade.side_b == Side.LONG:
                pnl_b = (xp_b - open_trade.entry_price_b) * open_trade.qty_b
            else:
                pnl_b = (open_trade.entry_price_b - xp_b) * open_trade.qty_b

            open_trade.exit_time = merged.index[-1].to_pydatetime() if hasattr(merged.index[-1], "to_pydatetime") else merged.index[-1]
            open_trade.exit_price_a = xp_a
            open_trade.exit_price_b = xp_b
            open_trade.pnl = pnl_a + pnl_b
            open_trade.exit_reason = "backtest_end"
            trades.append(open_trade)
            capital += open_trade.pnl

        equity = pd.Series(
            [e[1] for e in equity_points],
            index=[e[0] for e in equity_points],
        )

        result = BacktestResult(trades=trades, equity_curve=equity, params={
            "pair": f"{pair.leg_a}/{pair.leg_b}",
            "timeframe": self.cfg.data.timeframe,
            "zscore_entry": self.cfg.strategy.zscore_entry,
            "zscore_exit": self.cfg.strategy.zscore_exit,
            "lookback": self.cfg.strategy.lookback,
        })

        s = result.summary()
        log.info("BACKTEST DONE  trades=%d  winrate=%.1f%%  PnL=$%.2f  sharpe=%.2f  MDD=%.2f%%",
                 s["total_trades"], s["win_rate"] * 100, s["total_pnl"],
                 s["sharpe_ratio"], s["max_drawdown"] * 100)
        return result
