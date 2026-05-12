"""Pair selection engine — correlation, cointegration, filtering, ranking."""

from __future__ import annotations

import itertools
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant
from statsmodels.tsa.stattools import adfuller, coint

from config import Config
from utils.log import get_logger
from utils.types import PairScore

log = get_logger(__name__)


class PairSelector:
    """Scores and ranks crypto pairs for intraday mean-reversion trading."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.ps = cfg.pair_selection

    # ── Public API ──────────────────────────────────────────

    def score_pairs(
        self, price_dict: Dict[str, pd.DataFrame]
    ) -> List[PairScore]:
        """
        Parameters
        ----------
        price_dict : {symbol: DataFrame with 'close' column, datetime index}

        Returns
        -------
        Sorted list of PairScore (best first).
        """
        symbols = list(price_dict.keys())
        candidates: List[PairScore] = []

        for sym_a, sym_b in itertools.combinations(symbols, 2):
            df_a = price_dict[sym_a]
            df_b = price_dict[sym_b]

            # Align on common timestamps
            merged = pd.merge(
                df_a[["close"]].rename(columns={"close": "a"}),
                df_b[["close"]].rename(columns={"close": "b"}),
                left_index=True, right_index=True, how="inner",
            )
            if len(merged) < self.ps.hedge_ratio_window:
                continue

            # Volume filter
            vol_a = df_a["volume"].mean() * df_a["close"].mean() if "volume" in df_a.columns else 0
            vol_b = df_b["volume"].mean() * df_b["close"].mean() if "volume" in df_b.columns else 0
            if vol_a < self.ps.min_daily_volume_usd or vol_b < self.ps.min_daily_volume_usd:
                continue

            score = self._evaluate_pair(merged, sym_a, sym_b, vol_a, vol_b)
            if score is not None:
                candidates.append(score)

        # Sort by composite score descending
        candidates.sort(key=lambda p: p.composite_score, reverse=True)
        top = candidates[: self.ps.max_pairs]
        for p in top:
            log.info(
                "PAIR %s/%s  corr=%.3f  coint_p=%.4f  hl=%.1f  score=%.3f",
                p.leg_a, p.leg_b, p.correlation,
                p.cointegration_pvalue, p.half_life, p.composite_score,
            )
        return top

    # ── Internals ──────────────────────────────────────────

    def _evaluate_pair(
        self,
        merged: pd.DataFrame,
        sym_a: str,
        sym_b: str,
        vol_a: float,
        vol_b: float,
    ) -> Optional[PairScore]:
        a = merged["a"].values
        b = merged["b"].values

        # 1. Correlation
        corr = np.corrcoef(a, b)[0, 1]
        if corr < self.ps.min_correlation or corr > self.ps.max_correlation:
            return None

        # 2. Cointegration (Engle-Granger)
        try:
            coint_t, coint_p, _ = coint(a, b)
        except Exception:
            return None
        if coint_p > self.ps.cointegration_pvalue:
            return None

        # 3. Hedge ratio via OLS
        hedge_ratio = self._rolling_hedge_ratio(a, b)

        # 4. Spread and ADF
        spread = a - hedge_ratio * b
        try:
            adf_stat, adf_p, *_ = adfuller(spread, maxlag=20, autolag="AIC")
        except Exception:
            return None
        if adf_p > self.ps.adf_pvalue:
            return None

        # 5. Half-life
        half_life = self._half_life(spread)
        if half_life < self.ps.min_half_life or half_life > self.ps.max_half_life:
            return None

        # 6. Composite score
        composite = self._composite_score(corr, coint_p, adf_p, half_life)

        return PairScore(
            leg_a=sym_a,
            leg_b=sym_b,
            correlation=corr,
            cointegration_pvalue=coint_p,
            adf_pvalue=adf_p,
            half_life=half_life,
            hedge_ratio=hedge_ratio,
            avg_daily_volume_a=vol_a,
            avg_daily_volume_b=vol_b,
            composite_score=composite,
        )

    @staticmethod
    def _rolling_hedge_ratio(a: np.ndarray, b: np.ndarray) -> float:
        """OLS hedge ratio: a = beta * b + alpha."""
        b_const = add_constant(b)
        model = OLS(a, b_const).fit()
        return float(model.params[1])

    @staticmethod
    def _half_life(spread: np.ndarray) -> float:
        """Ornstein-Uhlenbeck half-life estimate."""
        spread_lag = spread[:-1]
        spread_diff = np.diff(spread)
        spread_lag = add_constant(spread_lag)
        try:
            model = OLS(spread_diff, spread_lag).fit()
            gamma = model.params[1]
            if gamma >= 0:
                return 999.0
            return float(-np.log(2) / gamma)
        except Exception:
            return 999.0

    @staticmethod
    def _composite_score(
        corr: float, coint_p: float, adf_p: float, half_life: float
    ) -> float:
        """Higher is better. Weights chosen empirically."""
        # Penalise high p-values and long half-lives
        score = (
            0.30 * corr
            + 0.30 * (1.0 - coint_p / 0.05)
            + 0.20 * (1.0 - adf_p / 0.05)
            + 0.20 * max(0, 1.0 - half_life / 200)
        )
        return round(score, 4)
