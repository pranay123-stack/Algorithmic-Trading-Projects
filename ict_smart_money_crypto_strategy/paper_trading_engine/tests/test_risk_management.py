"""
Unit Tests for Risk Management
Tests position sizing, risk limits, drawdown protection
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core_trading_strategy.risk_management import RiskManager


class TestRiskManager(unittest.TestCase):
    """Test risk management functionality"""

    def setUp(self):
        """Initialize risk manager"""
        self.risk_manager = RiskManager(
            initial_capital=10000,
            risk_per_trade_pct=0.02,
            max_daily_loss_pct=0.05,
            max_drawdown_pct=0.25,
            max_position_size_pct=0.20,
            leverage=5.0
        )

    def test_initialization(self):
        """Test risk manager can be initialized"""
        self.assertIsNotNone(self.risk_manager)
        self.assertEqual(self.risk_manager.initial_capital, 10000)
        self.assertEqual(self.risk_manager.current_capital, 10000)

    def test_calculate_position_size(self):
        """Test position size calculation"""
        entry_price = 2500
        stop_loss = 2450  # 2% risk
        direction = 'LONG'

        position_size = self.risk_manager.calculate_position_size(
            entry_price=entry_price,
            stop_loss=stop_loss,
            direction=direction
        )

        self.assertIsNotNone(position_size)
        self.assertGreater(position_size, 0)

    def test_position_size_within_limits(self):
        """Test position size doesn't exceed max"""
        entry_price = 2500
        stop_loss = 2499  # Very tight stop (0.04%)
        direction = 'LONG'

        position_size = self.risk_manager.calculate_position_size(
            entry_price=entry_price,
            stop_loss=stop_loss,
            direction=direction
        )

        max_position = self.risk_manager.current_capital * 0.20 * self.risk_manager.leverage

        self.assertLessEqual(
            position_size, max_position,
            "Position size exceeds maximum"
        )

    def test_update_capital_profit(self):
        """Test capital update with profit"""
        initial = self.risk_manager.current_capital
        pnl = 500  # $500 profit

        self.risk_manager.update_capital(pnl)

        self.assertEqual(self.risk_manager.current_capital, initial + pnl)
        self.assertGreater(self.risk_manager.peak_capital, initial)

    def test_update_capital_loss(self):
        """Test capital update with loss"""
        initial = self.risk_manager.current_capital
        pnl = -300  # $300 loss

        self.risk_manager.update_capital(pnl)

        self.assertEqual(self.risk_manager.current_capital, initial + pnl)

    def test_drawdown_calculation(self):
        """Test drawdown is calculated correctly"""
        # Make a loss
        self.risk_manager.update_capital(-2000)  # -20% loss

        stats = self.risk_manager.get_stats()
        drawdown = stats['current_dd_pct'] / 100  # Convert percentage to decimal

        self.assertAlmostEqual(drawdown, 0.20, places=2)  # 20%
        self.assertAlmostEqual(self.risk_manager.max_drawdown_reached / 100, 0.20, places=2)

    def test_daily_loss_limit(self):
        """Test daily loss limit check"""
        # Make a small loss
        self.risk_manager.update_capital(-400)  # -4% (below 5% limit)
        limits = self.risk_manager.check_risk_limits()
        self.assertFalse(limits['daily_limit_breached'])

        # Make a large loss
        self.risk_manager.update_capital(-200)  # Total -6% (exceeds 5% limit)
        limits = self.risk_manager.check_risk_limits()
        self.assertTrue(limits['daily_limit_breached'])

    def test_max_drawdown_limit(self):
        """Test max drawdown limit check"""
        # Make moderate loss
        self.risk_manager.update_capital(-2000)  # -20% (below 25% limit)
        limits = self.risk_manager.check_risk_limits()
        self.assertFalse(limits['dd_limit_breached'])

        # Make large loss
        self.risk_manager.update_capital(-800)  # Total -28% (exceeds 25% limit)
        limits = self.risk_manager.check_risk_limits()
        self.assertTrue(limits['dd_limit_breached'])

    def test_reset_daily_metrics(self):
        """Test daily metrics reset"""
        # Make a loss
        self.risk_manager.update_capital(-500)
        self.assertEqual(self.risk_manager.daily_pnl, -500)

        # Reset
        self.risk_manager.reset_daily_metrics()
        self.assertEqual(self.risk_manager.daily_pnl, 0)

    def test_get_stats(self):
        """Test get_stats returns correct information"""
        stats = self.risk_manager.get_stats()

        self.assertIn('current_capital', stats)
        self.assertIn('total_return_pct', stats)
        self.assertIn('current_dd_pct', stats)
        self.assertIn('max_dd_reached', stats)

    def test_leverage_application(self):
        """Test leverage is applied correctly"""
        entry_price = 2500
        stop_loss = 2400  # 4% risk
        direction = 'LONG'

        position_size = self.risk_manager.calculate_position_size(
            entry_price=entry_price,
            stop_loss=stop_loss,
            direction=direction
        )

        # Position size should be greater than 0
        self.assertGreater(position_size, 0)


class TestRiskManagerEdgeCases(unittest.TestCase):
    """Test edge cases in risk management"""

    def test_zero_capital(self):
        """Test behavior with zero capital"""
        risk_manager = RiskManager(
            initial_capital=10000,
            risk_per_trade_pct=0.02,
            max_daily_loss_pct=0.05,
            max_drawdown_pct=0.25,
            max_position_size_pct=0.20,
            leverage=5.0
        )

        # Lose all capital
        risk_manager.update_capital(-10000)

        position_size = risk_manager.calculate_position_size(
            entry_price=2500,
            stop_loss=2450,
            direction='LONG'
        )

        self.assertEqual(position_size, 0, "Should not allow trading with zero capital")

    def test_invalid_stop_loss(self):
        """Test with stop loss equal to entry price"""
        risk_manager = RiskManager(
            initial_capital=10000,
            risk_per_trade_pct=0.02,
            max_daily_loss_pct=0.05,
            max_drawdown_pct=0.25,
            max_position_size_pct=0.20,
            leverage=5.0
        )

        position_size = risk_manager.calculate_position_size(
            entry_price=2500,
            stop_loss=2500,  # Same as entry
            direction='LONG'
        )

        self.assertEqual(position_size, 0, "Should return 0 for invalid stop loss")


if __name__ == '__main__':
    print("Running Risk Management Unit Tests...")
    print("=" * 60)
    unittest.main(verbosity=2)
