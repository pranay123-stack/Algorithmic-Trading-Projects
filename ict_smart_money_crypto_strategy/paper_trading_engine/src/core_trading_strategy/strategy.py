"""
Trading Strategy - Standalone Module
ICT × SMC Final Strategy with Independent Indicator Logic
"""

import pandas as pd
import numpy as np
from enum import Enum


class SignalType(Enum):
    """Trade signal types"""
    NONE = 0
    LONG = 1
    SHORT = -1


class TradingStrategy:
    """
    Final ICT Strategy - Standalone Implementation

    Entry Logic:
    - LONG: Bullish bias + (FVG_BULL OR OB_BULL OR SWEEP_LOW)
    - SHORT: Bearish bias + (FVG_BEAR OR OB_BEAR OR SWEEP_HIGH)

    Quality Filters:
    - ATR > 0.3% (volatility filter)
    - Risk < 3% (position sizing filter)
    - Bias alignment required (no counter-trend)
    - Structure-based stops (30-bar lookback)

    Performance (Forward Test Oct-Dec 2024):
    - Sharpe: 1.30
    - Win Rate: 42.1%
    - Profit Factor: 1.70
    """

    def __init__(
        self,
        timeframe: str = '15m',
        rr_ratio: float = 2.0,
        stop_lookback: int = 30,
        min_atr_pct: float = 0.003,
        max_risk_pct: float = 0.03
    ):
        """
        Initialize strategy

        Args:
            timeframe: Trading timeframe (e.g., '15m')
            rr_ratio: Reward:Risk ratio (2.0 = 2:1)
            stop_lookback: Candles to look back for stop loss
            min_atr_pct: Minimum ATR % to trade (0.003 = 0.3%)
            max_risk_pct: Maximum risk per trade (0.03 = 3%)
        """
        self.timeframe = timeframe
        self.rr_ratio = rr_ratio
        self.stop_lookback = stop_lookback
        self.min_atr_pct = min_atr_pct
        self.max_risk_pct = max_risk_pct

    def generate_signals(
        self,
        df: pd.DataFrame,
        use_fvg: bool = True,
        use_ob: bool = True,
        use_sweep: bool = True
    ) -> pd.DataFrame:
        """
        Generate trading signals from indicator data

        Args:
            df: DataFrame with OHLCV + indicator columns
            use_fvg: Use Fair Value Gap signals
            use_ob: Use Order Block signals
            use_sweep: Use Liquidity Sweep signals

        Returns:
            DataFrame with signal columns:
            - action: 'LONG', 'SHORT', or 'HOLD'
            - entry_price: Suggested entry price
            - stop_loss: Stop loss price
            - take_profit: Take profit price
            - signal_reasons: Why this signal was generated
            - risk_pct: Risk as % of entry price
        """
        df = df.copy()

        # Initialize signal columns
        df['signal'] = SignalType.NONE.value
        df['action'] = 'HOLD'
        df['entry_price'] = np.nan
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        df['signal_reasons'] = ''
        df['risk_pct'] = 0.0

        # Verify required columns
        required = ['daily_bias', 'atr_pct', 'fvg_bullish', 'fvg_bearish',
                   'ob_bullish', 'ob_bearish', 'sweep_low', 'sweep_high']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}. Run indicators.calculate_all() first!")

        # Track position state (prevent multiple signals)
        in_position = False
        entry_idx = None

        # Generate signals
        for i in range(100, len(df)):  # Skip first 100 bars for indicator stability
            # Exit position after max holding period
            if in_position:
                bars_in_trade = i - entry_idx
                if bars_in_trade > 80:  # ~20 hours on 15m
                    in_position = False
                    entry_idx = None
                continue

            current_bias = df['daily_bias'].iloc[i]
            current_atr_pct = df['atr_pct'].iloc[i]

            # FILTER 1: Skip if volatility too low
            if pd.notna(current_atr_pct) and current_atr_pct < self.min_atr_pct:
                continue

            # === LONG SIGNALS ===
            if current_bias == 1:  # Bullish bias required
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
                    # Calculate entry and stops
                    entry_price = df['close'].iloc[i]
                    reasons.append('BULL_BIAS')

                    # Stop loss at structure low
                    lookback_start = max(0, i - self.stop_lookback)
                    structure_low = df['low'].iloc[lookback_start:i].min()
                    stop_loss = structure_low * 0.997  # 0.3% buffer

                    risk = entry_price - stop_loss
                    risk_pct = risk / entry_price

                    # FILTER 2: Skip if risk too high
                    if risk_pct > self.max_risk_pct:
                        continue

                    if risk > 0:
                        take_profit = entry_price + (risk * self.rr_ratio)

                        # Set signal
                        df.loc[df.index[i], 'signal'] = SignalType.LONG.value
                        df.loc[df.index[i], 'action'] = 'LONG'
                        df.loc[df.index[i], 'entry_price'] = entry_price
                        df.loc[df.index[i], 'stop_loss'] = stop_loss
                        df.loc[df.index[i], 'take_profit'] = take_profit
                        df.loc[df.index[i], 'signal_reasons'] = ' | '.join(reasons)
                        df.loc[df.index[i], 'risk_pct'] = risk_pct

                        in_position = True
                        entry_idx = i
                        continue

            # === SHORT SIGNALS ===
            elif current_bias == -1:  # Bearish bias required
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
                    # Calculate entry and stops
                    entry_price = df['close'].iloc[i]
                    reasons.append('BEAR_BIAS')

                    # Stop loss at structure high
                    lookback_start = max(0, i - self.stop_lookback)
                    structure_high = df['high'].iloc[lookback_start:i].max()
                    stop_loss = structure_high * 1.003  # 0.3% buffer

                    risk = stop_loss - entry_price
                    risk_pct = risk / entry_price

                    # FILTER 2: Skip if risk too high
                    if risk_pct > self.max_risk_pct:
                        continue

                    if risk > 0:
                        take_profit = entry_price - (risk * self.rr_ratio)

                        # Set signal
                        df.loc[df.index[i], 'signal'] = SignalType.SHORT.value
                        df.loc[df.index[i], 'action'] = 'SHORT'
                        df.loc[df.index[i], 'entry_price'] = entry_price
                        df.loc[df.index[i], 'stop_loss'] = stop_loss
                        df.loc[df.index[i], 'take_profit'] = take_profit
                        df.loc[df.index[i], 'signal_reasons'] = ' | '.join(reasons)
                        df.loc[df.index[i], 'risk_pct'] = risk_pct

                        in_position = True
                        entry_idx = i

        return df

    def get_latest_signal(self, df: pd.DataFrame) -> dict:
        """
        Get the most recent signal from the DataFrame

        Args:
            df: DataFrame with signals (output of generate_signals)

        Returns:
            dict with signal information, or None if no signal
        """
        # Get last row
        last_row = df.iloc[-1]

        if pd.isna(last_row['action']) or last_row['action'] == 'HOLD':
            return None

        return {
            'action': last_row['action'],
            'entry_price': last_row['entry_price'],
            'stop_loss': last_row['stop_loss'],
            'take_profit': last_row['take_profit'],
            'reasons': last_row['signal_reasons'],
            'risk_pct': last_row['risk_pct'],
            'timestamp': df.index[-1]
        }
