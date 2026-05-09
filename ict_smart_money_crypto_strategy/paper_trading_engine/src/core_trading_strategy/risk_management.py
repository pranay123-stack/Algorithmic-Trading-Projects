"""
Risk Management Module
Handles position sizing, risk calculations, and risk limits
"""

import logging

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Manages trading risk

    Features:
    - Position sizing based on risk
    - Daily loss limits
    - Maximum drawdown limits
    - Position size caps
    """

    def __init__(
        self,
        initial_capital: float,
        risk_per_trade_pct: float = 0.02,
        max_daily_loss_pct: float = 0.05,
        max_drawdown_pct: float = 0.25,
        max_position_size_pct: float = 0.20,
        leverage: float = 5.0
    ):
        """
        Initialize risk manager

        Args:
            initial_capital: Starting capital
            risk_per_trade_pct: Risk per trade (0.02 = 2%)
            max_daily_loss_pct: Max daily loss (0.05 = 5%)
            max_drawdown_pct: Max drawdown (0.25 = 25%)
            max_position_size_pct: Max position size (0.20 = 20%)
            leverage: Trading leverage
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_position_size_pct = max_position_size_pct
        self.leverage = leverage

        # Track daily metrics
        self.daily_pnl = 0.0
        self.max_drawdown_reached = 0.0

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str
    ) -> float:
        """
        Calculate position size based on risk

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: 'LONG' or 'SHORT'

        Returns:
            Position size in USD
        """
        # Calculate risk amount
        risk_amount = self.current_capital * self.risk_per_trade_pct

        # Calculate stop distance
        if direction == 'LONG':
            stop_distance = entry_price - stop_loss
        else:  # SHORT
            stop_distance = stop_loss - entry_price

        if stop_distance <= 0:
            logger.warning("Invalid stop distance, returning 0 position size")
            return 0.0

        # Calculate position value needed to risk the desired amount
        position_value = (risk_amount / stop_distance) * entry_price

        # Apply leverage
        position_size = position_value * self.leverage

        # Cap at maximum position size
        max_position = self.current_capital * self.max_position_size_pct * self.leverage
        position_size = min(position_size, max_position)

        logger.info(f"Position Size: ${position_size:.2f} (Risk: ${risk_amount:.2f}, {self.risk_per_trade_pct*100:.1f}%)")

        return position_size

    def check_risk_limits(self) -> dict:
        """
        Check if any risk limits are breached

        Returns:
            dict with status and breach information
        """
        # Check daily loss limit
        daily_loss_pct = (self.daily_pnl / self.initial_capital) * 100
        daily_limit_breached = daily_loss_pct < -self.max_daily_loss_pct * 100

        # Check max drawdown
        current_dd_pct = ((self.peak_capital - self.current_capital) / self.peak_capital) * 100
        dd_limit_breached = current_dd_pct > self.max_drawdown_pct * 100

        # Update max drawdown reached
        if current_dd_pct > self.max_drawdown_reached:
            self.max_drawdown_reached = current_dd_pct

        return {
            'all_clear': not (daily_limit_breached or dd_limit_breached),
            'daily_loss_pct': daily_loss_pct,
            'daily_limit_breached': daily_limit_breached,
            'current_dd_pct': current_dd_pct,
            'dd_limit_breached': dd_limit_breached,
            'max_dd_reached': self.max_drawdown_reached
        }

    def update_capital(self, pnl: float):
        """
        Update capital after trade

        Args:
            pnl: Profit/loss from trade
        """
        self.current_capital += pnl
        self.daily_pnl += pnl

        # Update peak capital
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital

        logger.info(f"Capital updated: ${self.current_capital:.2f} (PnL: ${pnl:.2f})")

    def reset_daily_metrics(self):
        """Reset daily tracking metrics (call at start of each day)"""
        self.daily_pnl = 0.0
        logger.info("Daily metrics reset")

    def get_stats(self) -> dict:
        """Get current risk statistics"""
        return {
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'total_return_pct': ((self.current_capital - self.initial_capital) / self.initial_capital) * 100,
            'current_dd_pct': ((self.peak_capital - self.current_capital) / self.peak_capital) * 100,
            'max_dd_reached': self.max_drawdown_reached,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_pct': (self.daily_pnl / self.initial_capital) * 100
        }
