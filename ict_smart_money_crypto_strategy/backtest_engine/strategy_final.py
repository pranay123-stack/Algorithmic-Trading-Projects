"""
FINAL ICT Strategy - Independent Indicators with Quality Filters
STANDALONE VERSION - No dependencies on other strategy files
"""

import pandas as pd
import numpy as np
from enum import Enum


class SignalType(Enum):
    """Signal types"""
    NONE = 0
    LONG = 1
    SHORT = -1


class FinalICTStrategy:
    """
    Final working ICT strategy with independent indicator logic

    Key Features:
    1. Independent indicators (FVG OR OB OR Sweep) + bias required
    2. Quality filters: ATR > 0.3%, Risk < 3%, Bias alignment
    3. Structure-based stop loss (30-bar lookback)
    4. 2:1 reward-risk ratio

    Results (Oct-Dec 2024 Forward Test):
    - Sharpe: 1.30
    - Win Rate: 42.1%
    - Return: +25.7%
    - Profit Factor: 1.70
    """

    def __init__(
        self,
        base_tf: str = '15m',
        risk_per_trade: float = 0.02,
        rr_ratio: float = 2.0,
        max_position_size: float = 0.1
    ):
        """
        Initialize strategy

        Args:
            base_tf: Base timeframe (e.g., '15m')
            risk_per_trade: Risk per trade as decimal (0.02 = 2%)
            rr_ratio: Reward-risk ratio (2.0 = 2:1)
            max_position_size: Max position as fraction of capital
        """
        self.base_tf = base_tf
        self.risk_per_trade = risk_per_trade
        self.rr_ratio = rr_ratio
        self.max_position_size = max_position_size

    def calculate_daily_bias(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate daily bias from price action

        Simple method:
        - Bullish if close > EMA(50)
        - Bearish if close < EMA(50)
        """
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        bias = pd.Series(0, index=df.index)
        bias[df['close'] > ema_50] = 1   # Bullish
        bias[df['close'] < ema_50] = -1  # Bearish
        return bias

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range for volatility filter"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(period).mean()
        return atr

    def generate_signals(
        self,
        df: pd.DataFrame,
        use_fvg: bool = True,
        use_ob: bool = True,
        use_sweep: bool = True,
        min_atr_pct: float = 0.003  # Minimum 0.3% ATR
    ) -> pd.DataFrame:
        """
        Generate trading signals with quality filters

        Entry Logic (Independent OR):
        - LONG: Bullish bias + (FVG_BULL OR OB_BULL OR SWEEP_LOW)
        - SHORT: Bearish bias + (FVG_BEAR OR OB_BEAR OR SWEEP_HIGH)

        Quality Filters:
        1. MUST have bias alignment (no counter-trend trading)
        2. ATR > min_atr_pct (only trade when volatile enough)
        3. Risk < 3% (skip trades with excessive risk)
        4. Structure-based stops (30-bar lookback)

        Args:
            df: DataFrame with OHLCV and ICT indicator columns
            use_fvg: Use Fair Value Gap signals
            use_ob: Use Order Block signals
            use_sweep: Use Liquidity Sweep signals
            min_atr_pct: Minimum ATR as % of price

        Returns:
            DataFrame with signal columns added:
            - action: 'LONG', 'SHORT', or 'HOLD'
            - entry_price: Entry price if signal
            - stop_loss: Stop loss price
            - take_profit: Take profit price
            - signal_reasons: List of reasons for signal
        """
        df = df.copy()

        # Initialize signal columns
        df['signal'] = SignalType.NONE.value
        df['action'] = 'HOLD'
        df['entry_price'] = np.nan
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        df['confidence'] = 0.0
        df['signal_reasons'] = ''

        # Verify required columns exist
        required = ['fvg_bullish', 'fvg_bearish',
                   'ob_bullish', 'ob_bearish',
                   'sweep_high', 'sweep_low']
        missing = [c for c in required if c not in df.columns]
        if missing:
            print(f"⚠️  Missing indicator columns: {missing}")
            print(f"    Make sure to run ICTIndicators.detect_*() methods first!")
            return df

        # Calculate daily bias if not present
        if 'daily_bias' not in df.columns:
            df['daily_bias'] = self.calculate_daily_bias(df)

        # Calculate ATR for volatility filter
        atr = self.calculate_atr(df)
        atr_pct = atr / df['close']
        df['atr_pct'] = atr_pct

        # Track position state (prevent multiple signals)
        in_position = False
        entry_idx = None

        # Generate signals
        for i in range(100, len(df)):  # Skip first 100 bars for indicators
            if in_position:
                # Exit after 80 bars (~20 hours on 15m)
                bars_in_trade = i - entry_idx
                if bars_in_trade > 80:
                    in_position = False
                    entry_idx = None
                continue

            current_bias = df['daily_bias'].iloc[i]
            current_atr_pct = atr_pct.iloc[i]

            # FILTER 1: Skip if volatility too low
            if pd.notna(current_atr_pct) and current_atr_pct < min_atr_pct:
                continue

            # === LONG SIGNALS (Bullish Bias Required) ===
            if current_bias == 1:
                reasons = []
                has_signal = False

                # Check indicators independently (OR logic)
                if use_fvg and df['fvg_bullish'].iloc[i]:
                    reasons.append('BULL_FVG')
                    has_signal = True

                if use_ob and df['ob_bullish'].iloc[i]:
                    reasons.append('BULL_OB')
                    has_signal = True

                if use_sweep and df['sweep_low'].iloc[i]:
                    reasons.append('SWEEP_LOW')
                    has_signal = True

                if has_signal:
                    reasons.append('BULL_BIAS')
                    entry_price = df['close'].iloc[i]

                    # Stop loss at recent structure low (30-bar lookback)
                    lookback_start = max(0, i - 30)
                    structure_low = df['low'].iloc[lookback_start:i].min()
                    stop_loss = structure_low * 0.997  # 0.3% buffer below

                    risk = entry_price - stop_loss
                    risk_pct = risk / entry_price

                    # FILTER 2: Skip if risk > 3%
                    if risk_pct > 0.03:
                        continue

                    if risk > 0:
                        take_profit = entry_price + (risk * self.rr_ratio)

                        # Confidence based on number of indicators (not used for filtering)
                        num_indicators = len([r for r in reasons if r != 'BULL_BIAS'])
                        confidence = min(num_indicators / 3.0, 1.0)

                        # Set signal
                        df.loc[df.index[i], 'signal'] = SignalType.LONG.value
                        df.loc[df.index[i], 'action'] = 'LONG'
                        df.loc[df.index[i], 'entry_price'] = entry_price
                        df.loc[df.index[i], 'stop_loss'] = stop_loss
                        df.loc[df.index[i], 'take_profit'] = take_profit
                        df.loc[df.index[i], 'confidence'] = confidence
                        df.loc[df.index[i], 'signal_reasons'] = ' | '.join(reasons)

                        in_position = True
                        entry_idx = i
                        continue

            # === SHORT SIGNALS (Bearish Bias Required) ===
            elif current_bias == -1:
                reasons = []
                has_signal = False

                # Check indicators independently (OR logic)
                if use_fvg and df['fvg_bearish'].iloc[i]:
                    reasons.append('BEAR_FVG')
                    has_signal = True

                if use_ob and df['ob_bearish'].iloc[i]:
                    reasons.append('BEAR_OB')
                    has_signal = True

                if use_sweep and df['sweep_high'].iloc[i]:
                    reasons.append('SWEEP_HIGH')
                    has_signal = True

                if has_signal:
                    reasons.append('BEAR_BIAS')
                    entry_price = df['close'].iloc[i]

                    # Stop loss at recent structure high (30-bar lookback)
                    lookback_start = max(0, i - 30)
                    structure_high = df['high'].iloc[lookback_start:i].max()
                    stop_loss = structure_high * 1.003  # 0.3% buffer above

                    risk = stop_loss - entry_price
                    risk_pct = risk / entry_price

                    # FILTER 2: Skip if risk > 3%
                    if risk_pct > 0.03:
                        continue

                    if risk > 0:
                        take_profit = entry_price - (risk * self.rr_ratio)

                        # Confidence based on number of indicators
                        num_indicators = len([r for r in reasons if r != 'BEAR_BIAS'])
                        confidence = min(num_indicators / 3.0, 1.0)

                        # Set signal
                        df.loc[df.index[i], 'signal'] = SignalType.SHORT.value
                        df.loc[df.index[i], 'action'] = 'SHORT'
                        df.loc[df.index[i], 'entry_price'] = entry_price
                        df.loc[df.index[i], 'stop_loss'] = stop_loss
                        df.loc[df.index[i], 'take_profit'] = take_profit
                        df.loc[df.index[i], 'confidence'] = confidence
                        df.loc[df.index[i], 'signal_reasons'] = ' | '.join(reasons)

                        in_position = True
                        entry_idx = i

        return df
