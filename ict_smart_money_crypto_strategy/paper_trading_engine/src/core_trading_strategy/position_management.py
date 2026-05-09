"""
Position Management Module
Handles position tracking, monitoring, and P&L calculations
"""

import logging
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class Position:
    """Position object"""

    def __init__(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        size: float,
        stop_loss: float,
        take_profit: float,
        entry_time: datetime,
        leverage: float = 1.0
    ):
        self.symbol = symbol
        self.side = side  # 'LONG' or 'SHORT'
        self.entry_price = entry_price
        self.size = size  # Position size in USD
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.entry_time = entry_time
        self.leverage = leverage
        self.exit_price = None
        self.exit_time = None
        self.pnl = 0.0
        self.pnl_pct = 0.0
        self.exit_reason = None  # 'TP', 'SL', 'MANUAL', 'TIMEOUT'
        self.is_open = True

    def calculate_pnl(self, current_price: float) -> float:
        """
        Calculate current P&L

        Args:
            current_price: Current market price

        Returns:
            P&L in USD
        """
        if self.side == 'LONG':
            price_change_pct = (current_price - self.entry_price) / self.entry_price
        else:  # SHORT
            price_change_pct = (self.entry_price - current_price) / self.entry_price

        # Apply leverage
        pnl_pct = price_change_pct * self.leverage
        pnl = self.size * pnl_pct

        return pnl

    def calculate_pnl_pct(self, current_price: float) -> float:
        """
        Calculate P&L percentage

        Args:
            current_price: Current market price

        Returns:
            P&L as percentage
        """
        if self.side == 'LONG':
            price_change_pct = (current_price - self.entry_price) / self.entry_price
        else:  # SHORT
            price_change_pct = (self.entry_price - current_price) / self.entry_price

        return price_change_pct * self.leverage * 100

    def close_position(
        self,
        exit_price: float,
        exit_reason: str,
        exit_time: datetime = None
    ):
        """
        Close the position

        Args:
            exit_price: Exit price
            exit_reason: Reason for exit ('TP', 'SL', 'MANUAL', 'TIMEOUT')
            exit_time: Exit timestamp
        """
        self.exit_price = exit_price
        self.exit_reason = exit_reason
        self.exit_time = exit_time or datetime.now()
        self.pnl = self.calculate_pnl(exit_price)
        self.pnl_pct = self.calculate_pnl_pct(exit_price)
        self.is_open = False

        logger.info(
            f"Position closed: {self.side} {self.symbol} @ {exit_price:.2f} "
            f"(P&L: ${self.pnl:.2f}, {self.pnl_pct:.2f}%) - Reason: {exit_reason}"
        )

    def to_dict(self) -> dict:
        """Convert position to dictionary"""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'size': self.size,
            'leverage': self.leverage,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'exit_reason': self.exit_reason,
            'is_open': self.is_open
        }


class PositionManager:
    """
    Manages trading positions

    Features:
    - Position tracking (open and closed)
    - Real-time P&L calculations
    - Position history
    - Performance statistics
    """

    def __init__(self, max_positions: int = 1):
        """
        Initialize position manager

        Args:
            max_positions: Maximum concurrent positions
        """
        self.max_positions = max_positions
        self.current_position: Optional[Position] = None
        self.position_history = []

    def open_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        size: float,
        stop_loss: float,
        take_profit: float,
        leverage: float = 1.0,
        entry_time: datetime = None
    ) -> Position:
        """
        Open a new position

        Args:
            symbol: Trading symbol
            side: 'LONG' or 'SHORT'
            entry_price: Entry price
            size: Position size in USD
            stop_loss: Stop loss price
            take_profit: Take profit price
            leverage: Trading leverage
            entry_time: Entry timestamp

        Returns:
            Position object
        """
        # Check if we can open a new position
        if self.current_position is not None:
            raise RuntimeError(f"Cannot open position - already have open position: {self.current_position.side} {self.current_position.symbol}")

        # Create position
        position = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            size=size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=entry_time or datetime.now(),
            leverage=leverage
        )

        self.current_position = position

        logger.info(
            f"Position opened: {side} {symbol} @ {entry_price:.2f} "
            f"(Size: ${size:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f})"
        )

        return position

    def close_position(
        self,
        exit_price: float,
        exit_reason: str,
        exit_time: datetime = None
    ) -> Optional[Position]:
        """
        Close the current position

        Args:
            exit_price: Exit price
            exit_reason: Reason for exit
            exit_time: Exit timestamp

        Returns:
            Closed position or None
        """
        if self.current_position is None:
            logger.warning("No open position to close")
            return None

        # Close position
        self.current_position.close_position(exit_price, exit_reason, exit_time)

        # Move to history
        self.position_history.append(self.current_position)
        closed_position = self.current_position
        self.current_position = None

        return closed_position

    def get_current_position(self) -> Optional[Position]:
        """Get current open position"""
        return self.current_position

    def has_open_position(self) -> bool:
        """Check if there's an open position"""
        return self.current_position is not None

    def get_current_pnl(self, current_price: float) -> float:
        """
        Get current P&L for open position

        Args:
            current_price: Current market price

        Returns:
            P&L in USD or 0 if no position
        """
        if self.current_position is None:
            return 0.0

        return self.current_position.calculate_pnl(current_price)

    def get_position_history(self) -> list:
        """Get all closed positions"""
        return [p.to_dict() for p in self.position_history]

    def get_total_pnl(self) -> float:
        """Calculate total P&L from all closed positions"""
        return sum(p.pnl for p in self.position_history)

    def get_win_rate(self) -> float:
        """Calculate win rate"""
        if not self.position_history:
            return 0.0

        winning_trades = len([p for p in self.position_history if p.pnl > 0])
        return (winning_trades / len(self.position_history)) * 100

    def get_profit_factor(self) -> float:
        """Calculate profit factor"""
        gross_profit = sum(p.pnl for p in self.position_history if p.pnl > 0)
        gross_loss = abs(sum(p.pnl for p in self.position_history if p.pnl < 0))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    def get_avg_win(self) -> float:
        """Calculate average winning trade"""
        winning_trades = [p.pnl for p in self.position_history if p.pnl > 0]
        return sum(winning_trades) / len(winning_trades) if winning_trades else 0.0

    def get_avg_loss(self) -> float:
        """Calculate average losing trade"""
        losing_trades = [p.pnl for p in self.position_history if p.pnl < 0]
        return sum(losing_trades) / len(losing_trades) if losing_trades else 0.0

    def get_stats(self) -> dict:
        """Get position statistics"""
        return {
            'total_trades': len(self.position_history),
            'open_position': self.current_position.to_dict() if self.current_position else None,
            'total_pnl': self.get_total_pnl(),
            'win_rate': self.get_win_rate(),
            'profit_factor': self.get_profit_factor(),
            'avg_win': self.get_avg_win(),
            'avg_loss': self.get_avg_loss(),
            'winning_trades': len([p for p in self.position_history if p.pnl > 0]),
            'losing_trades': len([p for p in self.position_history if p.pnl < 0])
        }
