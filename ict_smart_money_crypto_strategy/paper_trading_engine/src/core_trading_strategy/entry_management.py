"""
Entry Management Module
Handles entry signal validation and execution logic
"""

import logging
from datetime import datetime
from typing import Optional, Dict
import pandas as pd

logger = logging.getLogger(__name__)


class EntryManager:
    """
    Manages trade entry logic

    Features:
    - Entry signal validation
    - Entry execution coordination
    - Slippage handling
    - Entry logging and tracking
    """

    def __init__(
        self,
        min_atr_pct: float = 0.003,
        max_risk_pct: float = 0.03,
        slippage_pct: float = 0.0005
    ):
        """
        Initialize entry manager

        Args:
            min_atr_pct: Minimum ATR percentage to enter (0.003 = 0.3%)
            max_risk_pct: Maximum risk percentage to enter (0.03 = 3%)
            slippage_pct: Expected slippage (0.0005 = 0.05%)
        """
        self.min_atr_pct = min_atr_pct
        self.max_risk_pct = max_risk_pct
        self.slippage_pct = slippage_pct
        self.entry_log = []

    def validate_entry_signal(
        self,
        signal: dict,
        current_price: float,
        atr_pct: Optional[float] = None
    ) -> tuple[bool, str]:
        """
        Validate entry signal before execution

        Args:
            signal: Signal dictionary with entry details
            current_price: Current market price
            atr_pct: Current ATR percentage (optional)

        Returns:
            (is_valid, reason) tuple
        """
        # Check if signal has required fields
        required_fields = ['action', 'entry_price', 'stop_loss', 'take_profit']
        missing = [f for f in required_fields if f not in signal or signal[f] is None]
        if missing:
            return False, f"Missing fields: {missing}"

        # Check if action is valid
        if signal['action'] not in ['LONG', 'SHORT']:
            return False, f"Invalid action: {signal['action']}"

        # Check ATR filter
        if atr_pct is not None and atr_pct < self.min_atr_pct:
            return False, f"ATR too low: {atr_pct:.4f} < {self.min_atr_pct:.4f}"

        # Check risk percentage
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']

        if signal['action'] == 'LONG':
            risk_pct = (entry_price - stop_loss) / entry_price
        else:  # SHORT
            risk_pct = (stop_loss - entry_price) / entry_price

        if risk_pct > self.max_risk_pct:
            return False, f"Risk too high: {risk_pct:.4f} > {self.max_risk_pct:.4f}"

        if risk_pct <= 0:
            return False, f"Invalid risk: {risk_pct:.4f}"

        # Check if entry price is reasonable (within 1% of current price)
        price_diff_pct = abs(entry_price - current_price) / current_price
        if price_diff_pct > 0.01:
            return False, f"Entry price too far from current: {price_diff_pct:.4f}"

        # All checks passed
        return True, "Valid"

    def calculate_execution_price(
        self,
        signal: dict,
        current_price: float
    ) -> float:
        """
        Calculate execution price with slippage

        Args:
            signal: Signal dictionary
            current_price: Current market price

        Returns:
            Execution price
        """
        # Apply slippage
        if signal['action'] == 'LONG':
            execution_price = current_price * (1 + self.slippage_pct)
        else:  # SHORT
            execution_price = current_price * (1 - self.slippage_pct)

        return execution_price

    def prepare_entry(
        self,
        signal: dict,
        current_price: float,
        capital: float,
        risk_per_trade_pct: float,
        leverage: float,
        atr_pct: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Prepare entry execution details

        Args:
            signal: Signal dictionary
            current_price: Current market price
            capital: Available capital
            risk_per_trade_pct: Risk per trade percentage
            leverage: Trading leverage
            atr_pct: Current ATR percentage

        Returns:
            Entry details dictionary or None if invalid
        """
        # Validate signal
        is_valid, reason = self.validate_entry_signal(signal, current_price, atr_pct)

        if not is_valid:
            logger.info(f"Entry rejected: {reason}")
            return None

        # Calculate execution price
        execution_price = self.calculate_execution_price(signal, current_price)

        # Calculate position size
        if signal['action'] == 'LONG':
            stop_distance = execution_price - signal['stop_loss']
        else:  # SHORT
            stop_distance = signal['stop_loss'] - execution_price

        risk_amount = capital * risk_per_trade_pct
        position_value = (risk_amount / stop_distance) * execution_price
        position_size = position_value * leverage

        # Cap at maximum position size (20% of capital)
        max_position = capital * 0.20 * leverage
        position_size = min(position_size, max_position)

        # Prepare entry details
        entry_details = {
            'action': signal['action'],
            'execution_price': execution_price,
            'position_size': position_size,
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'risk_amount': risk_amount,
            'signal_reasons': signal.get('reasons', ''),
            'timestamp': datetime.now(),
            'validation_reason': reason
        }

        logger.info(
            f"Entry prepared: {signal['action']} @ {execution_price:.2f} "
            f"(Size: ${position_size:.2f}, Risk: ${risk_amount:.2f})"
        )

        return entry_details

    def log_entry(
        self,
        entry_details: dict,
        success: bool,
        error_msg: Optional[str] = None
    ):
        """
        Log entry execution

        Args:
            entry_details: Entry details dictionary
            success: Whether entry was successful
            error_msg: Error message if failed
        """
        log_entry = {
            'timestamp': entry_details['timestamp'],
            'action': entry_details['action'],
            'execution_price': entry_details['execution_price'],
            'position_size': entry_details['position_size'],
            'stop_loss': entry_details['stop_loss'],
            'take_profit': entry_details['take_profit'],
            'signal_reasons': entry_details.get('signal_reasons', ''),
            'success': success,
            'error_msg': error_msg
        }

        self.entry_log.append(log_entry)

        if success:
            logger.info(
                f"✅ Entry executed: {entry_details['action']} @ {entry_details['execution_price']:.2f}"
            )
        else:
            logger.error(
                f"❌ Entry failed: {entry_details['action']} - {error_msg}"
            )

    def get_entry_log(self) -> list:
        """Get entry execution log"""
        return self.entry_log

    def get_entry_stats(self) -> dict:
        """Get entry statistics"""
        if not self.entry_log:
            return {
                'total_attempts': 0,
                'successful_entries': 0,
                'failed_entries': 0,
                'success_rate': 0.0
            }

        successful = len([e for e in self.entry_log if e['success']])
        failed = len([e for e in self.entry_log if not e['success']])

        return {
            'total_attempts': len(self.entry_log),
            'successful_entries': successful,
            'failed_entries': failed,
            'success_rate': (successful / len(self.entry_log)) * 100 if self.entry_log else 0.0
        }
