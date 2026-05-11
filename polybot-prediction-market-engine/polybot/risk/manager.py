"""Pre-trade and ongoing risk management.

Gates every order through position limits, exposure caps, and loss
limits before execution.
"""

from __future__ import annotations

from polybot.config.settings import RiskConfig
from polybot.telemetry import get_logger
from polybot.types import Position, Signal

logger = get_logger(__name__)


class RiskManager:
    """Enforces trading risk limits."""

    def __init__(self, config: RiskConfig) -> None:
        self._cfg = config
        self._daily_pnl = 0.0
        self._halted = False

    def check_order(
        self,
        signal: Signal,
        positions: list[Position],
        balance: float,
    ) -> tuple[bool, str]:
        """Pre-trade risk check.

        Returns ``(passed, reason)``.  If *passed* is ``False``,
        *reason* explains why the order was rejected.
        """
        if self._halted:
            return False, "trading_halted_daily_loss_limit"

        # 1. Position count
        if len(positions) >= self._cfg.max_positions:
            return False, "max_positions_reached"

        # 2. Single position size
        if signal.size_usdc > self._cfg.max_position_size_usdc:
            return False, "exceeds_max_position_size"

        # 3. Total exposure
        total_exposure = sum(p.size * p.current_price for p in positions)
        if total_exposure + signal.size_usdc > self._cfg.max_total_exposure_usdc:
            return False, "exceeds_max_total_exposure"

        # 4. Per-market loss
        market_loss = sum(
            abs(p.unrealized_pnl)
            for p in positions
            if p.market_id == signal.market_id and p.unrealized_pnl < 0
        )
        if market_loss >= self._cfg.max_loss_per_market_usdc:
            return False, "max_loss_per_market_reached"

        # 5. Daily loss
        if abs(self._daily_pnl) >= self._cfg.daily_loss_limit_usdc:
            self._halted = True
            return False, "daily_loss_limit_breached"

        # 6. Balance
        cost = signal.target_price * signal.size_usdc
        if cost > balance:
            return False, "insufficient_balance"

        return True, "approved"

    def update_daily_pnl(self, pnl_delta: float) -> None:
        """Accumulate daily PnL."""
        self._daily_pnl += pnl_delta
        if self._daily_pnl <= -self._cfg.daily_loss_limit_usdc:
            self._halted = True
            logger.warning("daily_loss_limit_hit", daily_pnl=self._daily_pnl)

    def reset_daily(self) -> None:
        """Reset daily counters (call at midnight UTC)."""
        self._daily_pnl = 0.0
        self._halted = False

    @property
    def is_halted(self) -> bool:
        return self._halted

    @property
    def daily_pnl(self) -> float:
        return self._daily_pnl

    @property
    def stats(self) -> dict[str, object]:
        return {
            "daily_pnl": self._daily_pnl,
            "halted": self._halted,
        }
