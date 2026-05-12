"""Intraday mean-reversion pair trading strategy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from config import Config
from pair_selection.spread import SpreadEngine, SpreadState
from utils.log import get_logger
from utils.types import Side, Signal

log = get_logger(__name__)


class Action(str, Enum):
    ENTER_LONG_SPREAD = "enter_long_spread"   # buy A, sell B
    ENTER_SHORT_SPREAD = "enter_short_spread"  # sell A, buy B
    EXIT = "exit"
    STOP_LOSS = "stop_loss"
    TIME_EXIT = "time_exit"
    SPREAD_WIDEN_EXIT = "spread_widen_exit"
    SESSION_CLOSE = "session_close"
    HOLD = "hold"


@dataclass
class PositionState:
    pair_key: str
    leg_a: str
    leg_b: str
    side: str  # "long_spread" or "short_spread"
    entry_zscore: float
    entry_time: datetime
    entry_spread: float
    entry_spread_std: float


class MeanReversionStrategy:
    """
    Core strategy logic.

    - Enter when |zscore| > entry threshold (spread diverges from mean)
    - Exit when zscore reverts near zero
    - Stop when |zscore| blows through stop threshold
    - Time-based exit after max holding period
    - Spread-widening protection
    - Volatility filter
    - Trend regime filter (ADX-based)
    """

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.s = cfg.strategy
        self.r = cfg.risk
        self._positions: Dict[str, PositionState] = {}

    # ── Main decision function ─────────────────────────────

    def evaluate(
        self,
        state: SpreadState,
        now: datetime,
        prices_a_series: Optional[pd.Series] = None,
        prices_b_series: Optional[pd.Series] = None,
    ) -> Action:
        key = f"{state.leg_a}|{state.leg_b}"
        z = state.zscore

        # Check if we have an open position
        pos = self._positions.get(key)

        if pos is not None:
            return self._evaluate_exit(pos, state, now)
        else:
            return self._evaluate_entry(
                key, state, now, prices_a_series, prices_b_series
            )

    def generate_signal(
        self, state: SpreadState, action: Action, now: datetime
    ) -> Optional[Signal]:
        """Convert an action into a Signal object."""
        if action == Action.HOLD:
            return None

        z = state.zscore

        if action == Action.ENTER_LONG_SPREAD:
            # Spread is low (z < -entry) → buy A, sell B
            return Signal(
                timestamp=now,
                pair_leg_a=state.leg_a,
                pair_leg_b=state.leg_b,
                zscore=z,
                spread=float(state.spread_series.iloc[-1]),
                hedge_ratio=state.hedge_ratio,
                side_a=Side.LONG,
                side_b=Side.SHORT,
                strength=abs(z),
            )
        elif action == Action.ENTER_SHORT_SPREAD:
            # Spread is high (z > entry) → sell A, buy B
            return Signal(
                timestamp=now,
                pair_leg_a=state.leg_a,
                pair_leg_b=state.leg_b,
                zscore=z,
                spread=float(state.spread_series.iloc[-1]),
                hedge_ratio=state.hedge_ratio,
                side_a=Side.SHORT,
                side_b=Side.LONG,
                strength=abs(z),
            )
        else:
            # Exit signals
            pos = self._positions.get(f"{state.leg_a}|{state.leg_b}")
            if pos is None:
                return None
            # Reverse the entry sides
            if pos.side == "long_spread":
                return Signal(
                    timestamp=now,
                    pair_leg_a=state.leg_a,
                    pair_leg_b=state.leg_b,
                    zscore=z,
                    spread=float(state.spread_series.iloc[-1]),
                    hedge_ratio=state.hedge_ratio,
                    side_a=Side.SHORT,  # close long A
                    side_b=Side.LONG,   # close short B
                    strength=abs(z),
                    meta={"exit_reason": action.value},
                )
            else:
                return Signal(
                    timestamp=now,
                    pair_leg_a=state.leg_a,
                    pair_leg_b=state.leg_b,
                    zscore=z,
                    spread=float(state.spread_series.iloc[-1]),
                    hedge_ratio=state.hedge_ratio,
                    side_a=Side.LONG,
                    side_b=Side.SHORT,
                    strength=abs(z),
                    meta={"exit_reason": action.value},
                )

    def register_entry(
        self, state: SpreadState, action: Action, now: datetime
    ) -> None:
        key = f"{state.leg_a}|{state.leg_b}"
        side = "long_spread" if action == Action.ENTER_LONG_SPREAD else "short_spread"
        self._positions[key] = PositionState(
            pair_key=key,
            leg_a=state.leg_a,
            leg_b=state.leg_b,
            side=side,
            entry_zscore=state.zscore,
            entry_time=now,
            entry_spread=float(state.spread_series.iloc[-1]),
            entry_spread_std=state.spread_std,
        )
        log.info("ENTRY %s %s z=%.2f", side, key, state.zscore)

    def register_exit(self, leg_a: str, leg_b: str, reason: str) -> None:
        key = f"{leg_a}|{leg_b}"
        pos = self._positions.pop(key, None)
        if pos:
            log.info("EXIT %s reason=%s", key, reason)

    def has_position(self, leg_a: str, leg_b: str) -> bool:
        return f"{leg_a}|{leg_b}" in self._positions

    def get_position(self, leg_a: str, leg_b: str) -> Optional[PositionState]:
        return self._positions.get(f"{leg_a}|{leg_b}")

    def open_position_count(self) -> int:
        return len(self._positions)

    # ── Entry logic ────────────────────────────────────────

    def _evaluate_entry(
        self,
        key: str,
        state: SpreadState,
        now: datetime,
        prices_a: Optional[pd.Series],
        prices_b: Optional[pd.Series],
    ) -> Action:
        z = state.zscore

        # Session close guard
        if self._near_session_end(now):
            return Action.HOLD

        # Max open pairs guard
        if len(self._positions) >= self.r.max_open_pairs:
            return Action.HOLD

        # Volatility filter
        if not self._passes_vol_filter(state):
            return Action.HOLD

        # Trend filter (ADX-based on spread)
        if not self._passes_trend_filter(state):
            return Action.HOLD

        if z < -self.s.zscore_entry:
            return Action.ENTER_LONG_SPREAD
        elif z > self.s.zscore_entry:
            return Action.ENTER_SHORT_SPREAD

        return Action.HOLD

    # ── Exit logic ─────────────────────────────────────────

    def _evaluate_exit(
        self, pos: PositionState, state: SpreadState, now: datetime
    ) -> Action:
        z = state.zscore

        # 1. Session end
        if self._near_session_end(now):
            return Action.SESSION_CLOSE

        # 2. Time-based exit
        held = (now - pos.entry_time).total_seconds() / 60
        if held >= self.s.max_holding_minutes:
            return Action.TIME_EXIT

        # 3. Stop loss
        if pos.side == "long_spread" and z < -self.s.zscore_stop:
            return Action.STOP_LOSS
        if pos.side == "short_spread" and z > self.s.zscore_stop:
            return Action.STOP_LOSS

        # 4. Spread widening protection
        if state.spread_std > pos.entry_spread_std * self.s.spread_widening_mult:
            return Action.SPREAD_WIDEN_EXIT

        # 5. Mean reversion exit
        if pos.side == "long_spread" and z >= -self.s.zscore_exit:
            return Action.EXIT
        if pos.side == "short_spread" and z <= self.s.zscore_exit:
            return Action.EXIT

        return Action.HOLD

    # ── Filters ────────────────────────────────────────────

    def _passes_vol_filter(self, state: SpreadState) -> bool:
        """Reject entry if short-term vol is too high relative to long-term."""
        s = state.spread_series
        if len(s) < self.s.vol_filter_window * 2:
            return True
        short_vol = s.iloc[-self.s.vol_filter_window:].std()
        long_vol = s.std()
        if long_vol < 1e-12:
            return True
        ratio = short_vol / long_vol
        return ratio <= self.s.vol_filter_max_ratio

    def _passes_trend_filter(self, state: SpreadState) -> bool:
        """Simple ADX-like directional filter on the spread."""
        s = state.spread_series
        w = self.s.trend_filter_window
        if len(s) < w:
            return True
        # Use slope of linear regression as trend strength proxy
        y = s.iloc[-w:].values
        x = np.arange(len(y))
        if np.std(y) < 1e-12:
            return True
        slope = np.polyfit(x, y, 1)[0]
        normalised_slope = abs(slope) / np.std(y) * np.sqrt(w)
        # If trend too strong, skip (mean reversion unlikely)
        return normalised_slope < self.s.trend_filter_adx_thresh

    def _near_session_end(self, now: datetime) -> bool:
        parts = self.r.session_end_utc.split(":")
        end_h, end_m = int(parts[0]), int(parts[1])
        session_end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
        return now >= session_end
