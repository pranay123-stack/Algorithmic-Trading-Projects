"""
Market Utilities Module

Provides common market-related utility functions to eliminate code duplication
across modules, including slippage calculations, position sizing, and price utilities.
"""

from typing import Literal


class MarketUtils:
    """Utility class for market-related calculations."""

    @staticmethod
    def calculate_slippage(price: float, side: Literal['buy', 'sell'], slippage_pct: float = 0.0005) -> float:
        """
        Calculate slippage-adjusted price.

        Args:
            price: Original price
            side: Order side ('buy' or 'sell')
            slippage_pct: Slippage percentage (default 0.05%)

        Returns:
            Price adjusted for slippage
        """
        if side == 'buy':
            return price * (1 + slippage_pct)
        else:  # sell
            return price * (1 - slippage_pct)

    @staticmethod
    def calculate_position_size(
        capital: float,
        risk_per_trade: float,
        entry_price: float,
        stop_loss_price: float,
        leverage: int = 1
    ) -> float:
        """
        Calculate position size based on risk parameters.

        Args:
            capital: Total available capital
            risk_per_trade: Risk percentage per trade (e.g., 0.01 for 1%)
            entry_price: Planned entry price
            stop_loss_price: Stop loss price
            leverage: Leverage multiplier

        Returns:
            Position size in base currency units
        """
        risk_amount = capital * risk_per_trade
        stop_distance = abs(entry_price - stop_loss_price)

        if stop_distance == 0:
            return 0.0

        position_size = (risk_amount / stop_distance) * leverage
        return position_size

    @staticmethod
    def calculate_stop_distance_pct(entry_price: float, stop_loss_price: float) -> float:
        """
        Calculate stop loss distance as percentage of entry price.

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price

        Returns:
            Stop distance as percentage (e.g., 0.02 for 2%)
        """
        if entry_price == 0:
            return 0.0

        return abs(entry_price - stop_loss_price) / entry_price

    @staticmethod
    def is_price_within_tolerance(
        price: float,
        reference_price: float,
        tolerance_pct: float = 0.01
    ) -> bool:
        """
        Check if price is within tolerance range of reference price.

        Args:
            price: Price to check
            reference_price: Reference price
            tolerance_pct: Allowed tolerance percentage (default 1%)

        Returns:
            True if price is within tolerance
        """
        if reference_price == 0:
            return False

        deviation = abs(price - reference_price) / reference_price
        return deviation <= tolerance_pct

    @staticmethod
    def calculate_commission(
        quantity: float,
        price: float,
        commission_rate: float = 0.0004
    ) -> float:
        """
        Calculate trading commission.

        Args:
            quantity: Trade quantity
            price: Trade price
            commission_rate: Commission rate (default 0.04%)

        Returns:
            Commission amount in quote currency
        """
        notional_value = quantity * price
        return notional_value * commission_rate

    @staticmethod
    def calculate_pnl(
        side: Literal['long', 'short'],
        entry_price: float,
        exit_price: float,
        quantity: float
    ) -> float:
        """
        Calculate profit/loss for a position.

        Args:
            side: Position side ('long' or 'short')
            entry_price: Entry price
            exit_price: Exit price
            quantity: Position quantity

        Returns:
            P&L in quote currency (positive for profit, negative for loss)
        """
        if side == 'long':
            pnl = (exit_price - entry_price) * quantity
        else:  # short
            pnl = (entry_price - exit_price) * quantity

        return pnl

    @staticmethod
    def calculate_reward_risk_ratio(
        entry_price: float,
        take_profit_price: float,
        stop_loss_price: float
    ) -> float:
        """
        Calculate reward-to-risk ratio.

        Args:
            entry_price: Entry price
            take_profit_price: Take profit price
            stop_loss_price: Stop loss price

        Returns:
            Reward/risk ratio (e.g., 2.0 for 2:1 ratio)
        """
        reward = abs(take_profit_price - entry_price)
        risk = abs(entry_price - stop_loss_price)

        if risk == 0:
            return 0.0

        return reward / risk
