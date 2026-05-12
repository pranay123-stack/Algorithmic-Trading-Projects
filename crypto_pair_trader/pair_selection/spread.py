"""Spread calculation and z-score tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

from config import Config
from utils.log import get_logger

log = get_logger(__name__)


@dataclass
class SpreadState:
    """Live state of a spread for one pair."""
    leg_a: str
    leg_b: str
    hedge_ratio: float
    spread_series: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    zscore: float = 0.0
    spread_mean: float = 0.0
    spread_std: float = 0.0
    last_price_a: float = 0.0
    last_price_b: float = 0.0
    half_life: float = 0.0


class SpreadEngine:
    """Computes and tracks rolling spreads and z-scores for active pairs."""

    def __init__(self, cfg: Config) -> None:
        self.lookback = cfg.strategy.lookback
        self.hedge_window = cfg.pair_selection.hedge_ratio_window
        self._states: dict[str, SpreadState] = {}

    def pair_key(self, leg_a: str, leg_b: str) -> str:
        return f"{leg_a}|{leg_b}"

    def init_pair(
        self,
        leg_a: str,
        leg_b: str,
        prices_a: pd.Series,
        prices_b: pd.Series,
        hedge_ratio: float,
    ) -> SpreadState:
        key = self.pair_key(leg_a, leg_b)
        spread = prices_a - hedge_ratio * prices_b
        state = SpreadState(
            leg_a=leg_a,
            leg_b=leg_b,
            hedge_ratio=hedge_ratio,
            spread_series=spread,
            last_price_a=float(prices_a.iloc[-1]),
            last_price_b=float(prices_b.iloc[-1]),
        )
        self._update_stats(state)
        self._states[key] = state
        return state

    def update(
        self, leg_a: str, leg_b: str, price_a: float, price_b: float,
        timestamp: Optional[pd.Timestamp] = None,
    ) -> Optional[SpreadState]:
        key = self.pair_key(leg_a, leg_b)
        state = self._states.get(key)
        if state is None:
            return None

        new_spread = price_a - state.hedge_ratio * price_b
        ts = timestamp or pd.Timestamp.utcnow()
        state.spread_series = pd.concat([
            state.spread_series,
            pd.Series([new_spread], index=[ts]),
        ])
        # Trim to 2× lookback to save memory
        if len(state.spread_series) > self.lookback * 2:
            state.spread_series = state.spread_series.iloc[-self.lookback * 2:]

        state.last_price_a = price_a
        state.last_price_b = price_b
        self._update_stats(state)
        return state

    def recalculate_hedge_ratio(
        self, prices_a: pd.Series, prices_b: pd.Series
    ) -> float:
        """Rolling OLS hedge ratio."""
        a = prices_a.values[-self.hedge_window:]
        b = prices_b.values[-self.hedge_window:]
        b_c = add_constant(b)
        model = OLS(a, b_c).fit()
        return float(model.params[1])

    def get_state(self, leg_a: str, leg_b: str) -> Optional[SpreadState]:
        return self._states.get(self.pair_key(leg_a, leg_b))

    def remove_pair(self, leg_a: str, leg_b: str) -> None:
        self._states.pop(self.pair_key(leg_a, leg_b), None)

    def all_states(self) -> dict[str, SpreadState]:
        return dict(self._states)

    # ── Internal ───────────────────────────────────────────

    def _update_stats(self, state: SpreadState) -> None:
        window = state.spread_series.iloc[-self.lookback:]
        if len(window) < 10:
            state.zscore = 0.0
            return
        state.spread_mean = float(window.mean())
        state.spread_std = float(window.std())
        if state.spread_std < 1e-12:
            state.zscore = 0.0
        else:
            current = float(state.spread_series.iloc[-1])
            state.zscore = (current - state.spread_mean) / state.spread_std
