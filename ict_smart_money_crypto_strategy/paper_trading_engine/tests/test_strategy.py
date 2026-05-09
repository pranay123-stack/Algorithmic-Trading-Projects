"""
Unit Tests for Trading Strategy
Tests signal generation and entry/exit logic
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core_trading_strategy.strategy import TradingStrategy


class TestTradingStrategy(unittest.TestCase):
    """Test trading strategy functionality"""

    def setUp(self):
        """Create sample data with indicators"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=200, freq='15min')

        # Generate sample OHLCV with indicators
        prices = [2500 + np.random.randn() * 50 for _ in range(200)]

        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': [p + np.random.randn() * 10 for p in prices],
            'volume': [5000] * 200,
            # Add indicators
            'fvg_bullish': [False] * 200,
            'fvg_bearish': [False] * 200,
            'ob_bullish': [False] * 200,
            'ob_bearish': [False] * 200,
            'sweep_high': [False] * 200,
            'sweep_low': [False] * 200,
            'daily_bias': [0] * 200,
            'atr': [20] * 200,
            'atr_pct': [0.008] * 200,
        })

        # Create a bullish signal at index 100
        df.loc[100, 'fvg_bullish'] = True
        df.loc[100, 'daily_bias'] = 1  # Bullish bias

        # Create a bearish signal at index 150
        df.loc[150, 'fvg_bearish'] = True
        df.loc[150, 'daily_bias'] = -1  # Bearish bias

        df.set_index('timestamp', inplace=True)
        self.df = df

        self.strategy = TradingStrategy(
            timeframe='15m',
            rr_ratio=2.0,
            stop_lookback=30,
            min_atr_pct=0.003,
            max_risk_pct=0.03
        )

    def test_initialization(self):
        """Test strategy can be initialized"""
        self.assertIsNotNone(self.strategy)
        self.assertEqual(self.strategy.timeframe, '15m')
        self.assertEqual(self.strategy.rr_ratio, 2.0)

    def test_generate_signals(self):
        """Test signal generation"""
        try:
            result = self.strategy.generate_signals(self.df.copy())
            self.assertIsInstance(result, pd.DataFrame)
            self.assertIn('signal', result.columns)
            self.assertIn('entry_price', result.columns)
            self.assertIn('stop_loss', result.columns)
            self.assertIn('take_profit', result.columns)
        except Exception as e:
            self.fail(f"Signal generation failed: {e}")

    def test_long_signal_generated(self):
        """Test LONG signal is generated"""
        result = self.strategy.generate_signals(self.df.copy())

        # Check if LONG signal exists at index 100
        signals = result[result['signal'] == 1]
        self.assertGreater(len(signals), 0, "No LONG signals generated")

    def test_short_signal_generated(self):
        """Test SHORT signal is generated"""
        result = self.strategy.generate_signals(self.df.copy())

        # Check if SHORT signal exists at index 150
        signals = result[result['signal'] == -1]
        self.assertGreater(len(signals), 0, "No SHORT signals generated")

    def test_signal_values(self):
        """Test signal values are valid"""
        result = self.strategy.generate_signals(self.df.copy())

        signals = result['signal'].unique()
        for sig in signals:
            self.assertIn(sig, [0, 1, -1], f"Invalid signal value: {sig}")

    def test_stop_loss_calculation(self):
        """Test stop loss is calculated"""
        result = self.strategy.generate_signals(self.df.copy())

        # Get rows with signals
        signal_rows = result[result['signal'] != 0]

        for idx, row in signal_rows.iterrows():
            self.assertIsNotNone(row['stop_loss'], "Stop loss not set")
            self.assertGreater(row['stop_loss'], 0, "Stop loss should be positive")

    def test_take_profit_calculation(self):
        """Test take profit is calculated"""
        result = self.strategy.generate_signals(self.df.copy())

        # Get rows with signals
        signal_rows = result[result['signal'] != 0]

        for idx, row in signal_rows.iterrows():
            self.assertIsNotNone(row['take_profit'], "Take profit not set")
            self.assertGreater(row['take_profit'], 0, "Take profit should be positive")

    def test_risk_reward_ratio(self):
        """Test risk-reward ratio is correct"""
        result = self.strategy.generate_signals(self.df.copy())

        # Get LONG signals
        long_signals = result[result['signal'] == 1]

        for idx, row in long_signals.iterrows():
            entry = row['entry_price']
            sl = row['stop_loss']
            tp = row['take_profit']

            risk = abs(entry - sl)
            reward = abs(tp - entry)

            if risk > 0:
                rr = reward / risk
                self.assertAlmostEqual(
                    rr, self.strategy.rr_ratio, places=1,
                    msg=f"RR ratio should be {self.strategy.rr_ratio}"
                )

    def test_no_signal_without_bias(self):
        """Test no signal generated without bias"""
        df_no_bias = self.df.copy()
        df_no_bias['daily_bias'] = 0  # Neutral bias

        result = self.strategy.generate_signals(df_no_bias)
        self.assertEqual(result['signal'].sum(), 0, "Should not generate signals without bias")

    def test_low_volatility_filter(self):
        """Test low volatility is filtered out"""
        df_low_vol = self.df.copy()
        df_low_vol['atr_pct'] = 0.001  # Below min_atr_pct threshold

        result = self.strategy.generate_signals(df_low_vol)
        # Should have fewer signals or none
        self.assertLessEqual(
            len(result[result['signal'] != 0]),
            len(self.df[self.df['signal'] != 0]) if 'signal' in self.df.columns else 0
        )


if __name__ == '__main__':
    print("Running Trading Strategy Unit Tests...")
    print("=" * 60)
    unittest.main(verbosity=2)
