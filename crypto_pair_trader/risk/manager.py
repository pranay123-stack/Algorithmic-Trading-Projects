"""Position sizing and portfolio risk management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from config import Config
from database.store import DatabaseStore
from utils.log import get_logger
from utils.types import Signal

log = get_logger(__name__)


class RiskManager:
    """Enforces dollar-neutral sizing, exposure limits, and daily loss caps."""

    def __init__(self, cfg: Config, db: DatabaseStore) -> None:
        self.cfg = cfg
        self.r = cfg.risk
        self.db = db
        self._daily_pnl: float = 0.0
        self._daily_date: str = ""

    # ── Sizing ─────────────────────────────────────────────

    def compute_sizes(
        self,
        signal: Signal,
        price_a: float,
        price_b: float,
    ) -> Optional[Dict[str, float]]:
        """
        Returns {"qty_a": ..., "qty_b": ...} or None if risk limits block.
        Dollar-neutral: notional_a ≈ notional_b.
        """
        if not self._check_daily_loss():
            log.warning("Daily loss limit reached — blocking trade")
            return None

        if not self._check_exposure():
            log.warning("Portfolio exposure limit reached — blocking trade")
            return None

        # Target notional per leg
        max_notional = min(
            self.r.max_position_usd,
            self.r.capital * self.r.max_pair_exposure_pct,
        )

        qty_a = max_notional / price_a
        # Dollar-neutral: notional_b = notional_a
        notional_a = qty_a * price_a
        qty_b = notional_a / price_b

        # Verify dollar-neutral within tolerance
        notional_b = qty_b * price_b
        imbalance = abs(notional_a - notional_b) / max(notional_a, notional_b)
        if imbalance > self.r.dollar_neutral_tolerance:
            log.warning("Dollar-neutral imbalance %.2f%% — adjusting", imbalance * 100)
            qty_b = notional_a / price_b
            notional_b = qty_b * price_b

        log.info(
            "SIZE %s/%s  qty_a=%.6f ($%.0f)  qty_b=%.6f ($%.0f)",
            signal.pair_leg_a, signal.pair_leg_b,
            qty_a, notional_a, qty_b, notional_b,
        )
        return {"qty_a": qty_a, "qty_b": qty_b}

    def record_pnl(self, pnl: float) -> None:
        self._daily_pnl += pnl
        log.info("Daily PnL: $%.2f", self._daily_pnl)

    def reset_daily(self) -> None:
        self._daily_pnl = 0.0
        self._daily_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    # ── Checks ─────────────────────────────────────────────

    def _check_daily_loss(self) -> bool:
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        if today != self._daily_date:
            self.reset_daily()
            # Load from DB
            self._daily_pnl = self.db.get_daily_pnl(today)

        if self._daily_pnl <= -self.r.max_daily_loss_usd:
            return False
        if self.r.capital > 0 and self._daily_pnl <= -self.r.capital * self.r.max_daily_loss_pct:
            return False
        return True

    def _check_exposure(self) -> bool:
        open_trades = self.db.get_open_trades()
        if len(open_trades) >= self.r.max_open_pairs:
            return False
        # Approximate total exposure
        total_exposure = sum(
            abs(t.get("qty_a", 0) * t.get("entry_price_a", 0))
            + abs(t.get("qty_b", 0) * t.get("entry_price_b", 0))
            for t in open_trades
        )
        if self.r.capital > 0 and total_exposure / self.r.capital > self.r.max_portfolio_exposure_pct:
            return False
        return True

    def should_square_off(self, now: datetime) -> bool:
        parts = self.r.session_end_utc.split(":")
        end_h, end_m = int(parts[0]), int(parts[1])
        session_end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
        return now >= session_end
