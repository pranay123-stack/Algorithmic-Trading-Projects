"""
Exit Management Module
Handles exit signal monitoring and execution logic
"""

import logging
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class ExitManager:
    """
    Manages trade exit logic

    Features:
    - Stop loss monitoring (intra-bar execution)
    - Take profit monitoring
    - Timeout exits
    - Exit execution coordination
    - Exit logging
    """

    def __init__(
        self,
        max_holding_bars: int = 80,  # ~20 hours on 15m
        slippage_pct: float = 0.0005
    ):
        """
        Initialize exit manager

        Args:
            max_holding_bars: Maximum bars to hold position
            slippage_pct: Expected slippage (0.0005 = 0.05%)
        """
        self.max_holding_bars = max_holding_bars
        self.slippage_pct = slippage_pct
        self.exit_log = []

    def check_stop_loss(
        self,
        position: dict,
        current_bar: dict
    ) -> tuple[bool, Optional[float], str]:
        """
        Check if stop loss hit (intra-bar execution)

        Args:
            position: Position dictionary
            current_bar: Current bar with OHLC data

        Returns:
            (hit, exit_price, reason) tuple
        """
        if position['side'] == 'LONG':
            # For long: check if low went below stop loss
            if current_bar['low'] <= position['stop_loss']:
                # Use stop loss price (assuming it got hit)
                exit_price = position['stop_loss']
                return True, exit_price, 'SL'

        else:  # SHORT
            # For short: check if high went above stop loss
            if current_bar['high'] >= position['stop_loss']:
                # Use stop loss price (assuming it got hit)
                exit_price = position['stop_loss']
                return True, exit_price, 'SL'

        return False, None, ''

    def check_take_profit(
        self,
        position: dict,
        current_bar: dict
    ) -> tuple[bool, Optional[float], str]:
        """
        Check if take profit hit (intra-bar execution)

        Args:
            position: Position dictionary
            current_bar: Current bar with OHLC data

        Returns:
            (hit, exit_price, reason) tuple
        """
        if position['side'] == 'LONG':
            # For long: check if high reached take profit
            if current_bar['high'] >= position['take_profit']:
                # Use take profit price (assuming it got hit)
                exit_price = position['take_profit']
                return True, exit_price, 'TP'

        else:  # SHORT
            # For short: check if low reached take profit
            if current_bar['low'] <= position['take_profit']:
                # Use take profit price (assuming it got hit)
                exit_price = position['take_profit']
                return True, exit_price, 'TP'

        return False, None, ''

    def check_timeout(
        self,
        position: dict,
        current_bar_index: int,
        entry_bar_index: int
    ) -> tuple[bool, str]:
        """
        Check if position timeout reached

        Args:
            position: Position dictionary
            current_bar_index: Current bar index
            entry_bar_index: Entry bar index

        Returns:
            (timeout, reason) tuple
        """
        bars_in_trade = current_bar_index - entry_bar_index

        if bars_in_trade >= self.max_holding_bars:
            return True, 'TIMEOUT'

        return False, ''

    def calculate_exit_price(
        self,
        position: dict,
        exit_reason: str,
        current_price: float,
        sl_price: Optional[float] = None,
        tp_price: Optional[float] = None
    ) -> float:
        """
        Calculate final exit price with slippage

        Args:
            position: Position dictionary
            exit_reason: Exit reason ('SL', 'TP', 'TIMEOUT', 'MANUAL')
            current_price: Current market price
            sl_price: Stop loss hit price
            tp_price: Take profit hit price

        Returns:
            Final exit price
        """
        # For SL/TP, use the hit price (already includes slippage assumption)
        if exit_reason == 'SL' and sl_price is not None:
            return sl_price

        if exit_reason == 'TP' and tp_price is not None:
            return tp_price

        # For TIMEOUT/MANUAL, use current price with slippage
        if position['side'] == 'LONG':
            # Selling at market - slippage goes against us
            exit_price = current_price * (1 - self.slippage_pct)
        else:  # SHORT
            # Buying at market - slippage goes against us
            exit_price = current_price * (1 + self.slippage_pct)

        return exit_price

    def check_exit_conditions(
        self,
        position: dict,
        current_bar: dict,
        current_bar_index: int,
        entry_bar_index: int
    ) -> tuple[bool, Optional[float], str]:
        """
        Check all exit conditions

        Priority: SL > TP > TIMEOUT

        Args:
            position: Position dictionary
            current_bar: Current bar with OHLC data
            current_bar_index: Current bar index
            entry_bar_index: Entry bar index

        Returns:
            (should_exit, exit_price, reason) tuple
        """
        # Check stop loss (highest priority)
        sl_hit, sl_price, sl_reason = self.check_stop_loss(position, current_bar)
        if sl_hit:
            return True, sl_price, sl_reason

        # Check take profit
        tp_hit, tp_price, tp_reason = self.check_take_profit(position, current_bar)
        if tp_hit:
            return True, tp_price, tp_reason

        # Check timeout
        timeout, timeout_reason = self.check_timeout(position, current_bar_index, entry_bar_index)
        if timeout:
            # Use close price for timeout
            exit_price = self.calculate_exit_price(
                position,
                'TIMEOUT',
                current_bar['close']
            )
            return True, exit_price, timeout_reason

        # No exit condition met
        return False, None, ''

    def prepare_exit(
        self,
        position: dict,
        exit_price: float,
        exit_reason: str,
        timestamp: datetime = None
    ) -> Dict:
        """
        Prepare exit execution details

        Args:
            position: Position dictionary
            exit_price: Exit price
            exit_reason: Exit reason
            timestamp: Exit timestamp

        Returns:
            Exit details dictionary
        """
        # Calculate P&L
        if position['side'] == 'LONG':
            price_change_pct = (exit_price - position['entry_price']) / position['entry_price']
        else:  # SHORT
            price_change_pct = (position['entry_price'] - exit_price) / position['entry_price']

        # Apply leverage
        pnl_pct = price_change_pct * position.get('leverage', 1.0)
        pnl = position['size'] * pnl_pct

        exit_details = {
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl': pnl,
            'pnl_pct': pnl_pct * 100,
            'timestamp': timestamp or datetime.now()
        }

        logger.info(
            f"Exit prepared: {position['side']} @ {exit_price:.2f} "
            f"(P&L: ${pnl:.2f}, {pnl_pct*100:.2f}%) - Reason: {exit_reason}"
        )

        return exit_details

    def log_exit(
        self,
        position: dict,
        exit_details: dict,
        success: bool,
        error_msg: Optional[str] = None
    ):
        """
        Log exit execution

        Args:
            position: Position dictionary
            exit_details: Exit details dictionary
            success: Whether exit was successful
            error_msg: Error message if failed
        """
        log_entry = {
            'timestamp': exit_details['timestamp'],
            'side': position['side'],
            'entry_price': position['entry_price'],
            'exit_price': exit_details['exit_price'],
            'exit_reason': exit_details['exit_reason'],
            'pnl': exit_details['pnl'],
            'pnl_pct': exit_details['pnl_pct'],
            'success': success,
            'error_msg': error_msg
        }

        self.exit_log.append(log_entry)

        if success:
            emoji = '🟢' if exit_details['pnl'] > 0 else '🔴'
            logger.info(
                f"{emoji} Exit executed: {position['side']} @ {exit_details['exit_price']:.2f} "
                f"(P&L: ${exit_details['pnl']:.2f}) - {exit_details['exit_reason']}"
            )
        else:
            logger.error(
                f"❌ Exit failed: {position['side']} - {error_msg}"
            )

    def get_exit_log(self) -> list:
        """Get exit execution log"""
        return self.exit_log

    def get_exit_stats(self) -> dict:
        """Get exit statistics"""
        if not self.exit_log:
            return {
                'total_exits': 0,
                'sl_exits': 0,
                'tp_exits': 0,
                'timeout_exits': 0,
                'manual_exits': 0
            }

        successful_exits = [e for e in self.exit_log if e['success']]

        return {
            'total_exits': len(successful_exits),
            'sl_exits': len([e for e in successful_exits if e['exit_reason'] == 'SL']),
            'tp_exits': len([e for e in successful_exits if e['exit_reason'] == 'TP']),
            'timeout_exits': len([e for e in successful_exits if e['exit_reason'] == 'TIMEOUT']),
            'manual_exits': len([e for e in successful_exits if e['exit_reason'] == 'MANUAL'])
        }
