"""
Unit Tests for ICT Indicators
Tests FVG, Order Blocks, Liquidity Sweeps, Daily Bias
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core_trading_strategy.indicators import ICTIndicators


class TestICTIndicators(unittest.TestCase):
    """Test ICT indicators functionality"""

    def setUp(self):
        """Create sample OHLCV data"""
        # Create 200 candles of sample data
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=200, freq='15min')

        # Generate realistic price data
        price = 2500
        prices = [price]
        for _ in range(199):
            change = np.random.randn() * 10  # Random walk
            price = price + change
            prices.append(max(price, 1000))  # Floor at 1000

        # Create OHLCV
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.randn() * 0.005)) for p in prices],
            'low': [p * (1 - abs(np.random.randn() * 0.005)) for p in prices],
            'close': [p + np.random.randn() * 5 for p in prices],
            'volume': [np.random.randint(1000, 10000) for _ in prices]
        })

        df.set_index('timestamp', inplace=True)
        self.df = df
        self.indicators = ICTIndicators(df.copy())

    def test_initialization(self):
        """Test ICTIndicators can be initialized"""
        self.assertIsNotNone(self.indicators)
        self.assertIsInstance(self.indicators.df, pd.DataFrame)
        self.assertEqual(len(self.indicators.df), 200)

    def test_detect_fair_value_gaps(self):
        """Test FVG detection"""
        try:
            self.indicators.detect_fair_value_gaps(
                min_gap_size=0.0005,
                lookback=40
            )
            self.assertIn('fvg_bullish', self.indicators.df.columns)
            self.assertIn('fvg_bearish', self.indicators.df.columns)
        except Exception as e:
            self.fail(f"FVG detection failed: {e}")

    def test_detect_order_blocks(self):
        """Test Order Block detection"""
        try:
            self.indicators.detect_order_blocks(
                swing_length=5,
                min_volume_percentile=40
            )
            self.assertIn('ob_bullish', self.indicators.df.columns)
            self.assertIn('ob_bearish', self.indicators.df.columns)
        except Exception as e:
            self.fail(f"Order Block detection failed: {e}")

    def test_detect_liquidity_sweeps(self):
        """Test Liquidity Sweep detection"""
        try:
            self.indicators.detect_liquidity_sweeps(
                lookback=15,
                sweep_threshold=0.0005
            )
            self.assertIn('sweep_high', self.indicators.df.columns)
            self.assertIn('sweep_low', self.indicators.df.columns)
        except Exception as e:
            self.fail(f"Liquidity Sweep detection failed: {e}")

    def test_calculate_daily_bias(self):
        """Test Daily Bias calculation"""
        try:
            self.indicators.calculate_daily_bias()
            self.assertIn('daily_bias', self.indicators.df.columns)
        except Exception as e:
            self.fail(f"Daily Bias calculation failed: {e}")

    def test_calculate_atr(self):
        """Test ATR calculation"""
        try:
            self.indicators.calculate_atr(period=14)
            self.assertIn('atr', self.indicators.df.columns)
            self.assertIn('atr_pct', self.indicators.df.columns)
        except Exception as e:
            self.fail(f"ATR calculation failed: {e}")

    def test_calculate_all(self):
        """Test calculate_all method"""
        try:
            result = self.indicators.calculate_all(
                fvg_min_gap=0.0005,
                fvg_lookback=40,
                ob_swing=5,
                ob_volume_pct=40,
                sweep_lookback=15,
                sweep_threshold=0.0005,
                atr_period=14
            )
            self.assertIsInstance(result, pd.DataFrame)

            # Check all indicators are present
            expected_columns = [
                'fvg_bullish', 'fvg_bearish',
                'ob_bullish', 'ob_bearish',
                'sweep_high', 'sweep_low',
                'daily_bias', 'atr', 'atr_pct'
            ]
            for col in expected_columns:
                self.assertIn(col, result.columns, f"Missing column: {col}")

        except Exception as e:
            self.fail(f"calculate_all failed: {e}")

    def test_empty_dataframe(self):
        """Test handling of empty dataframe"""
        empty_df = pd.DataFrame()
        with self.assertRaises(Exception):
            ICTIndicators(empty_df)

    def test_insufficient_data(self):
        """Test with insufficient data (< 50 candles)"""
        small_df = self.df.head(10).copy()
        indicators = ICTIndicators(small_df)

        # Should handle gracefully (may return NaN or empty results)
        try:
            result = indicators.calculate_all()
            self.assertIsInstance(result, pd.DataFrame)
        except Exception as e:
            # Expected - insufficient data
            pass


class TestIndicatorValues(unittest.TestCase):
    """Test indicator values are reasonable"""

    def setUp(self):
        """Create deterministic test data"""
        dates = pd.date_range('2024-01-01', periods=100, freq='15min')

        # Create data with known FVG
        df = pd.DataFrame({
            'timestamp': dates,
            'open': [2500] * 100,
            'high': [2510] * 100,
            'low': [2490] * 100,
            'close': [2500] * 100,
            'volume': [5000] * 100
        })

        # Create a bullish FVG at index 50
        df.loc[48, 'high'] = 2480
        df.loc[49, 'low'] = 2490
        df.loc[49, 'high'] = 2495
        df.loc[50, 'low'] = 2505  # Gap between 2495 and 2505

        df.set_index('timestamp', inplace=True)
        self.df = df
        self.indicators = ICTIndicators(df.copy())

    def test_fvg_values_are_boolean(self):
        """Test FVG signals are boolean"""
        self.indicators.detect_fair_value_gaps()
        self.assertTrue(self.indicators.df['fvg_bullish'].dtype == bool or self.indicators.df['fvg_bullish'].dtype == 'bool')
        self.assertTrue(self.indicators.df['fvg_bearish'].dtype == bool or self.indicators.df['fvg_bearish'].dtype == 'bool')

    def test_atr_values_are_positive(self):
        """Test ATR values are positive"""
        self.indicators.calculate_atr()
        atr_values = self.indicators.df['atr'].dropna()
        self.assertTrue((atr_values >= 0).all(), "ATR should be non-negative")


if __name__ == '__main__':
    print("Running ICT Indicators Unit Tests...")
    print("=" * 60)
    unittest.main(verbosity=2)
