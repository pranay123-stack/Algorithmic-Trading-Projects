"""
ICT Indicators - Standalone Module
No dependencies on backtest folder
"""

import pandas as pd
import numpy as np


class ICTIndicators:
    """
    Inner Circle Trader (ICT) Indicators

    Detects:
    - Fair Value Gaps (FVG)
    - Order Blocks (OB)
    - Liquidity Sweeps
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with OHLCV DataFrame

        Args:
            df: DataFrame with columns [open, high, low, close, volume]
        """
        self.df = df.copy()

    def detect_fair_value_gaps(self, min_gap_size: float = 0.0005, lookback: int = 40):
        """
        Detect Fair Value Gaps (FVG)

        A FVG is a 3-candle pattern where there's a gap:
        - Bullish FVG: candle[0].low > candle[2].high
        - Bearish FVG: candle[0].high < candle[2].low

        Args:
            min_gap_size: Minimum gap size as fraction (0.0005 = 0.05%)
            lookback: How many candles to look back for valid gaps
        """
        self.df['fvg_bullish'] = False
        self.df['fvg_bearish'] = False
        self.df['fvg_price'] = np.nan

        for i in range(2, len(self.df)):
            current_low = self.df['low'].iloc[i]
            current_high = self.df['high'].iloc[i]
            prev2_high = self.df['high'].iloc[i-2]
            prev2_low = self.df['low'].iloc[i-2]

            # Bullish FVG: gap up
            if current_low > prev2_high:
                gap_size = (current_low - prev2_high) / prev2_high
                if gap_size >= min_gap_size:
                    # Check if gap is still valid (not filled in last N candles)
                    if i >= lookback:
                        filled = False
                        for j in range(max(i-lookback, 2), i):
                            if self.df['low'].iloc[j] <= prev2_high:
                                filled = True
                                break
                        if not filled:
                            self.df.loc[self.df.index[i], 'fvg_bullish'] = True
                            self.df.loc[self.df.index[i], 'fvg_price'] = (current_low + prev2_high) / 2
                    else:
                        self.df.loc[self.df.index[i], 'fvg_bullish'] = True
                        self.df.loc[self.df.index[i], 'fvg_price'] = (current_low + prev2_high) / 2

            # Bearish FVG: gap down
            elif current_high < prev2_low:
                gap_size = (prev2_low - current_high) / current_high
                if gap_size >= min_gap_size:
                    # Check if gap is still valid
                    if i >= lookback:
                        filled = False
                        for j in range(max(i-lookback, 2), i):
                            if self.df['high'].iloc[j] >= prev2_low:
                                filled = True
                                break
                        if not filled:
                            self.df.loc[self.df.index[i], 'fvg_bearish'] = True
                            self.df.loc[self.df.index[i], 'fvg_price'] = (current_high + prev2_low) / 2
                    else:
                        self.df.loc[self.df.index[i], 'fvg_bearish'] = True
                        self.df.loc[self.df.index[i], 'fvg_price'] = (current_high + prev2_low) / 2

    def detect_order_blocks(self, swing_length: int = 5, min_volume_percentile: float = 40):
        """
        Detect Order Blocks (OB)

        Order blocks are areas where institutions placed large orders.
        Identified by swing highs/lows with above-average volume.

        Args:
            swing_length: Candles on each side to identify swing
            min_volume_percentile: Minimum volume percentile (40 = top 60%)
        """
        self.df['ob_bullish'] = False
        self.df['ob_bearish'] = False
        self.df['ob_price'] = np.nan

        # Calculate volume threshold
        volume_threshold = self.df['volume'].quantile(min_volume_percentile / 100)

        for i in range(swing_length, len(self.df) - swing_length):
            current_vol = self.df['volume'].iloc[i]

            # Only consider high volume candles
            if current_vol < volume_threshold:
                continue

            # Check for swing low (bullish OB)
            is_swing_low = True
            current_low = self.df['low'].iloc[i]
            for j in range(i - swing_length, i + swing_length + 1):
                if j != i and self.df['low'].iloc[j] < current_low:
                    is_swing_low = False
                    break

            if is_swing_low:
                self.df.loc[self.df.index[i], 'ob_bullish'] = True
                self.df.loc[self.df.index[i], 'ob_price'] = self.df['low'].iloc[i]

            # Check for swing high (bearish OB)
            is_swing_high = True
            current_high = self.df['high'].iloc[i]
            for j in range(i - swing_length, i + swing_length + 1):
                if j != i and self.df['high'].iloc[j] > current_high:
                    is_swing_high = False
                    break

            if is_swing_high:
                self.df.loc[self.df.index[i], 'ob_bearish'] = True
                self.df.loc[self.df.index[i], 'ob_price'] = self.df['high'].iloc[i]

    def detect_liquidity_sweeps(self, lookback: int = 15, sweep_threshold: float = 0.0005):
        """
        Detect Liquidity Sweeps

        A sweep occurs when price briefly goes beyond a high/low
        and then reverses (stop hunt).

        Args:
            lookback: How many candles to look back for highs/lows
            sweep_threshold: Minimum distance beyond high/low (0.0005 = 0.05%)
        """
        self.df['sweep_low'] = False
        self.df['sweep_high'] = False
        self.df['sweep_price'] = np.nan

        for i in range(lookback + 1, len(self.df)):
            current_high = self.df['high'].iloc[i]
            current_low = self.df['low'].iloc[i]
            current_close = self.df['close'].iloc[i]
            prev_close = self.df['close'].iloc[i-1]

            # Find recent low (for bullish sweep)
            recent_low = self.df['low'].iloc[i-lookback:i].min()

            # Sweep low: price goes below recent low but closes above it
            if current_low < recent_low:
                distance = (recent_low - current_low) / recent_low
                if distance >= sweep_threshold and current_close > recent_low:
                    self.df.loc[self.df.index[i], 'sweep_low'] = True
                    self.df.loc[self.df.index[i], 'sweep_price'] = recent_low

            # Find recent high (for bearish sweep)
            recent_high = self.df['high'].iloc[i-lookback:i].max()

            # Sweep high: price goes above recent high but closes below it
            if current_high > recent_high:
                distance = (current_high - recent_high) / recent_high
                if distance >= sweep_threshold and current_close < recent_high:
                    self.df.loc[self.df.index[i], 'sweep_high'] = True
                    self.df.loc[self.df.index[i], 'sweep_price'] = recent_high

    def calculate_daily_bias(self):
        """
        Calculate daily bias (trend direction)

        Simple method: EMA(50)
        - Bullish if close > EMA(50)
        - Bearish if close < EMA(50)
        """
        ema_50 = self.df['close'].ewm(span=50, adjust=False).mean()
        self.df['daily_bias'] = 0
        self.df.loc[self.df['close'] > ema_50, 'daily_bias'] = 1   # Bullish
        self.df.loc[self.df['close'] < ema_50, 'daily_bias'] = -1  # Bearish

    def calculate_atr(self, period: int = 14):
        """
        Calculate Average True Range (volatility measure)

        Args:
            period: ATR period (default 14)
        """
        high_low = self.df['high'] - self.df['low']
        high_close = np.abs(self.df['high'] - self.df['close'].shift())
        low_close = np.abs(self.df['low'] - self.df['close'].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)

        self.df['atr'] = true_range.rolling(period).mean()
        self.df['atr_pct'] = self.df['atr'] / self.df['close']

    def calculate_all(
        self,
        fvg_min_gap: float = 0.0005,
        fvg_lookback: int = 40,
        ob_swing: int = 5,
        ob_volume_pct: float = 40,
        sweep_lookback: int = 15,
        sweep_threshold: float = 0.0005,
        atr_period: int = 14
    ):
        """
        Calculate all ICT indicators at once

        Convenient method to run all detections with one call
        """
        self.detect_fair_value_gaps(min_gap_size=fvg_min_gap, lookback=fvg_lookback)
        self.detect_order_blocks(swing_length=ob_swing, min_volume_percentile=ob_volume_pct)
        self.detect_liquidity_sweeps(lookback=sweep_lookback, sweep_threshold=sweep_threshold)
        self.calculate_daily_bias()
        self.calculate_atr(period=atr_period)

        return self.df
