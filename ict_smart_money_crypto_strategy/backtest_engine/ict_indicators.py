"""
ICT (Inner Circle Trader) and Smart Money Concepts Indicators
Implements FVG, IFVG, Order Blocks, Liquidity Sweeps, SMT, and POI detection
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class BiasDirection(Enum):
    BULLISH = 1
    BEARISH = -1
    NEUTRAL = 0


@dataclass
class FairValueGap:
    """Fair Value Gap structure"""
    start_idx: int
    end_idx: int
    gap_high: float
    gap_low: float
    is_bullish: bool
    filled: bool = False
    fill_idx: Optional[int] = None


@dataclass
class OrderBlock:
    """Order Block / Point of Interest structure"""
    idx: int
    high: float
    low: float
    open: float
    close: float
    is_bullish: bool
    volume: float
    strength: float  # Measure of significance
    mitigated: bool = False


@dataclass
class LiquiditySweep:
    """Liquidity sweep / stop hunt structure"""
    idx: int
    swept_high: float
    swept_low: float
    is_bullish_sweep: bool  # True if sweeping lows then reverses up
    reversal_confirmed: bool = False


class ICTIndicators:
    """
    ICT and Smart Money Concepts indicator calculations
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with OHLCV DataFrame

        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        """
        self.df = df.copy()
        self.fvgs: List[FairValueGap] = []
        self.order_blocks: List[OrderBlock] = []
        self.liquidity_sweeps: List[LiquiditySweep] = []

    def detect_fair_value_gaps(
        self,
        min_gap_size: float = 0.001,  # Minimum gap as % of price
        lookback: int = 50  # How far back to check for fills
    ) -> pd.DataFrame:
        """
        Detect Fair Value Gaps (FVGs)

        A bullish FVG occurs when:
        - candle[i-1].high < candle[i+1].low (gap between candle 1 and 3)
        - Creating an imbalance that price may return to fill

        Args:
            min_gap_size: Minimum gap size as percentage
            lookback: Periods to look back for gap fills

        Returns:
            DataFrame with FVG columns added
        """
        df = self.df.copy()

        # Initialize columns
        df['fvg_bullish'] = False
        df['fvg_bearish'] = False
        df['fvg_high'] = np.nan
        df['fvg_low'] = np.nan
        df['fvg_filled'] = False

        for i in range(2, len(df)):
            # Bullish FVG: gap between candle[i-2].high and candle[i].low
            if df['high'].iloc[i-2] < df['low'].iloc[i]:
                gap_size = (df['low'].iloc[i] - df['high'].iloc[i-2]) / df['close'].iloc[i]

                if gap_size >= min_gap_size:
                    fvg = FairValueGap(
                        start_idx=i-2,
                        end_idx=i,
                        gap_high=df['low'].iloc[i],
                        gap_low=df['high'].iloc[i-2],
                        is_bullish=True
                    )
                    self.fvgs.append(fvg)

                    df.loc[df.index[i], 'fvg_bullish'] = True
                    df.loc[df.index[i], 'fvg_high'] = fvg.gap_high
                    df.loc[df.index[i], 'fvg_low'] = fvg.gap_low

            # Bearish FVG: gap between candle[i-2].low and candle[i].high
            elif df['low'].iloc[i-2] > df['high'].iloc[i]:
                gap_size = (df['low'].iloc[i-2] - df['high'].iloc[i]) / df['close'].iloc[i]

                if gap_size >= min_gap_size:
                    fvg = FairValueGap(
                        start_idx=i-2,
                        end_idx=i,
                        gap_high=df['low'].iloc[i-2],
                        gap_low=df['high'].iloc[i],
                        is_bullish=False
                    )
                    self.fvgs.append(fvg)

                    df.loc[df.index[i], 'fvg_bearish'] = True
                    df.loc[df.index[i], 'fvg_high'] = fvg.gap_high
                    df.loc[df.index[i], 'fvg_low'] = fvg.gap_low

        # Check for FVG fills
        for fvg in self.fvgs:
            for i in range(fvg.end_idx + 1, min(fvg.end_idx + lookback, len(df))):
                if fvg.is_bullish:
                    # Bullish FVG filled when price trades back into gap
                    if df['low'].iloc[i] <= fvg.gap_high:
                        fvg.filled = True
                        fvg.fill_idx = i
                        df.loc[df.index[i], 'fvg_filled'] = True
                        break
                else:
                    # Bearish FVG filled when price trades back into gap
                    if df['high'].iloc[i] >= fvg.gap_low:
                        fvg.filled = True
                        fvg.fill_idx = i
                        df.loc[df.index[i], 'fvg_filled'] = True
                        break

        self.df = df
        return df

    def detect_order_blocks(
        self,
        swing_length: int = 5,
        min_volume_percentile: float = 60
    ) -> pd.DataFrame:
        """
        Detect Order Blocks (OB) / Points of Interest (POI)

        Order blocks are the last bullish/bearish candle before a strong move in opposite direction
        Often represent areas where smart money entered positions

        Args:
            swing_length: Period to identify swing highs/lows
            min_volume_percentile: Minimum volume percentile for significant OB

        Returns:
            DataFrame with order block columns
        """
        df = self.df.copy()

        # Calculate swing highs and lows
        df['swing_high'] = df['high'].rolling(window=swing_length*2+1, center=True).max() == df['high']
        df['swing_low'] = df['low'].rolling(window=swing_length*2+1, center=True).min() == df['low']

        # Calculate volume threshold
        volume_threshold = df['volume'].quantile(min_volume_percentile / 100)

        # Initialize columns
        df['ob_bullish'] = False
        df['ob_bearish'] = False
        df['ob_high'] = np.nan
        df['ob_low'] = np.nan
        df['ob_strength'] = 0.0

        for i in range(swing_length, len(df) - swing_length):
            # Bullish Order Block: last red candle before swing low, then rally
            if df['swing_low'].iloc[i]:
                # Look for last bearish candle before swing low
                for j in range(i-1, max(0, i-swing_length), -1):
                    if df['close'].iloc[j] < df['open'].iloc[j]:  # Bearish candle
                        # Calculate strength based on volume and body size
                        body_size = abs(df['close'].iloc[j] - df['open'].iloc[j])
                        vol_ratio = df['volume'].iloc[j] / volume_threshold

                        if df['volume'].iloc[j] >= volume_threshold:
                            strength = body_size * vol_ratio

                            ob = OrderBlock(
                                idx=j,
                                high=df['high'].iloc[j],
                                low=df['low'].iloc[j],
                                open=df['open'].iloc[j],
                                close=df['close'].iloc[j],
                                is_bullish=True,
                                volume=df['volume'].iloc[j],
                                strength=strength
                            )
                            self.order_blocks.append(ob)

                            df.loc[df.index[j], 'ob_bullish'] = True
                            df.loc[df.index[j], 'ob_high'] = ob.high
                            df.loc[df.index[j], 'ob_low'] = ob.low
                            df.loc[df.index[j], 'ob_strength'] = strength
                            break

            # Bearish Order Block: last green candle before swing high, then decline
            if df['swing_high'].iloc[i]:
                # Look for last bullish candle before swing high
                for j in range(i-1, max(0, i-swing_length), -1):
                    if df['close'].iloc[j] > df['open'].iloc[j]:  # Bullish candle
                        body_size = abs(df['close'].iloc[j] - df['open'].iloc[j])
                        vol_ratio = df['volume'].iloc[j] / volume_threshold

                        if df['volume'].iloc[j] >= volume_threshold:
                            strength = body_size * vol_ratio

                            ob = OrderBlock(
                                idx=j,
                                high=df['high'].iloc[j],
                                low=df['low'].iloc[j],
                                open=df['open'].iloc[j],
                                close=df['close'].iloc[j],
                                is_bullish=False,
                                volume=df['volume'].iloc[j],
                                strength=strength
                            )
                            self.order_blocks.append(ob)

                            df.loc[df.index[j], 'ob_bearish'] = True
                            df.loc[df.index[j], 'ob_high'] = ob.high
                            df.loc[df.index[j], 'ob_low'] = ob.low
                            df.loc[df.index[j], 'ob_strength'] = strength
                            break

        self.df = df
        return df

    def detect_liquidity_sweeps(
        self,
        lookback: int = 20,
        sweep_threshold: float = 0.002,  # % beyond high/low
        reversal_threshold: float = 0.005  # % reversal to confirm
    ) -> pd.DataFrame:
        """
        Detect liquidity sweeps / stop hunts

        Occurs when price briefly breaks a swing high/low (taking liquidity)
        then reverses sharply in the opposite direction

        Args:
            lookback: Period to identify local highs/lows
            sweep_threshold: How far beyond high/low to qualify as sweep
            reversal_threshold: Reversal size to confirm sweep

        Returns:
            DataFrame with liquidity sweep columns
        """
        df = self.df.copy()

        # Calculate rolling highs and lows
        df['local_high'] = df['high'].rolling(window=lookback, center=False).max()
        df['local_low'] = df['low'].rolling(window=lookback, center=False).min()

        # Initialize columns
        df['sweep_high'] = False
        df['sweep_low'] = False
        df['liquidity_sweep'] = 0  # 1 for bullish sweep, -1 for bearish

        for i in range(lookback + 5, len(df)):
            local_high = df['local_high'].iloc[i-1]
            local_low = df['local_low'].iloc[i-1]

            # Bullish sweep: take lows then reverse up
            if df['low'].iloc[i] < local_low * (1 - sweep_threshold):
                # Check for reversal in next few candles
                for j in range(i+1, min(i+5, len(df))):
                    if df['close'].iloc[j] > df['low'].iloc[i] * (1 + reversal_threshold):
                        sweep = LiquiditySweep(
                            idx=i,
                            swept_high=df['high'].iloc[i],
                            swept_low=df['low'].iloc[i],
                            is_bullish_sweep=True,
                            reversal_confirmed=True
                        )
                        self.liquidity_sweeps.append(sweep)

                        df.loc[df.index[i], 'sweep_low'] = True
                        df.loc[df.index[i], 'liquidity_sweep'] = 1
                        break

            # Bearish sweep: take highs then reverse down
            if df['high'].iloc[i] > local_high * (1 + sweep_threshold):
                # Check for reversal
                for j in range(i+1, min(i+5, len(df))):
                    if df['close'].iloc[j] < df['high'].iloc[i] * (1 - reversal_threshold):
                        sweep = LiquiditySweep(
                            idx=i,
                            swept_high=df['high'].iloc[i],
                            swept_low=df['low'].iloc[i],
                            is_bullish_sweep=False,
                            reversal_confirmed=True
                        )
                        self.liquidity_sweeps.append(sweep)

                        df.loc[df.index[i], 'sweep_high'] = True
                        df.loc[df.index[i], 'liquidity_sweep'] = -1
                        break

        self.df = df
        return df

    def calculate_daily_bias(self, use_htf_data: bool = False) -> pd.DataFrame:
        """
        Calculate daily bias based on structure and FVGs

        Args:
            use_htf_data: If True, uses higher timeframe columns if available

        Returns:
            DataFrame with daily_bias column
        """
        df = self.df.copy()

        # Simple daily bias based on price structure
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # Bias conditions
        df['daily_bias'] = BiasDirection.NEUTRAL.value

        # Bullish bias: price above EMAs, bullish FVGs, bullish order blocks
        bullish_condition = (
            (df['close'] > df['ema_50']) &
            (df['ema_50'] > df['ema_200'])
        )

        # Bearish bias
        bearish_condition = (
            (df['close'] < df['ema_50']) &
            (df['ema_50'] < df['ema_200'])
        )

        df.loc[bullish_condition, 'daily_bias'] = BiasDirection.BULLISH.value
        df.loc[bearish_condition, 'daily_bias'] = BiasDirection.BEARISH.value

        self.df = df
        return df

    def detect_smt_divergence(
        self,
        correlated_df: pd.DataFrame,
        lookback: int = 10
    ) -> pd.DataFrame:
        """
        Detect Smart Money Tool (SMT) divergence

        SMT divergence occurs when two correlated assets (e.g., BTC and ETH)
        make divergent highs or lows, indicating smart money manipulation

        Args:
            correlated_df: DataFrame of correlated asset
            lookback: Period for swing detection

        Returns:
            DataFrame with SMT divergence signals
        """
        df = self.df.copy()

        # Calculate swing highs/lows for both assets
        df['swing_high'] = df['high'].rolling(window=lookback*2+1, center=True).max() == df['high']
        df['swing_low'] = df['low'].rolling(window=lookback*2+1, center=True).min() == df['low']

        corr_df = correlated_df.copy()
        corr_df['swing_high'] = corr_df['high'].rolling(window=lookback*2+1, center=True).max() == corr_df['high']
        corr_df['swing_low'] = corr_df['low'].rolling(window=lookback*2+1, center=True).min() == corr_df['low']

        # Align dataframes by index
        aligned = pd.merge(
            df[['high', 'low', 'swing_high', 'swing_low']],
            corr_df[['high', 'low', 'swing_high', 'swing_low']],
            left_index=True,
            right_index=True,
            suffixes=('', '_corr')
        )

        # Detect divergences
        aligned['smt_bullish'] = False
        aligned['smt_bearish'] = False

        for i in range(lookback, len(aligned)):
            # Bullish SMT: primary makes lower low, correlated makes higher low
            if aligned['swing_low'].iloc[i]:
                # Find previous swing low
                prev_lows = aligned['swing_low'].iloc[max(0, i-50):i]
                if prev_lows.any():
                    prev_idx = prev_lows[::-1].idxmax()
                    if aligned['low'].iloc[i] < aligned.loc[prev_idx, 'low']:
                        # Check correlated asset
                        if aligned['swing_low_corr'].iloc[i]:
                            corr_prev_lows = aligned['swing_low_corr'].iloc[max(0, i-50):i]
                            if corr_prev_lows.any():
                                corr_prev_idx = corr_prev_lows[::-1].idxmax()
                                if aligned['low_corr'].iloc[i] > aligned.loc[corr_prev_idx, 'low_corr']:
                                    aligned.loc[aligned.index[i], 'smt_bullish'] = True

            # Bearish SMT: primary makes higher high, correlated makes lower high
            if aligned['swing_high'].iloc[i]:
                prev_highs = aligned['swing_high'].iloc[max(0, i-50):i]
                if prev_highs.any():
                    prev_idx = prev_highs[::-1].idxmax()
                    if aligned['high'].iloc[i] > aligned.loc[prev_idx, 'high']:
                        if aligned['swing_high_corr'].iloc[i]:
                            corr_prev_highs = aligned['swing_high_corr'].iloc[max(0, i-50):i]
                            if corr_prev_highs.any():
                                corr_prev_idx = corr_prev_highs[::-1].idxmax()
                                if aligned['high_corr'].iloc[i] < aligned.loc[corr_prev_idx, 'high_corr']:
                                    aligned.loc[aligned.index[i], 'smt_bearish'] = True

        # Merge back to main df
        df['smt_bullish'] = aligned['smt_bullish']
        df['smt_bearish'] = aligned['smt_bearish']

        self.df = df
        return df

    def get_higher_timeframe_poi(
        self,
        htf_df: pd.DataFrame,
        htf_name: str = '4h'
    ) -> pd.DataFrame:
        """
        Get Points of Interest from higher timeframe and project to current timeframe

        Args:
            htf_df: Higher timeframe DataFrame
            htf_name: Name for column prefixes

        Returns:
            Current timeframe df with HTF POI zones
        """
        # Detect order blocks on HTF
        htf_indicators = ICTIndicators(htf_df)
        htf_indicators.detect_order_blocks()

        # Get active order blocks (most recent non-mitigated)
        htf_obs = [ob for ob in htf_indicators.order_blocks if not ob.mitigated]

        # Sort by strength
        htf_obs.sort(key=lambda x: x.strength, reverse=True)

        # Take top N strongest order blocks
        top_obs = htf_obs[:10] if len(htf_obs) > 10 else htf_obs

        # Project to current timeframe
        df = self.df.copy()
        df[f'htf_poi_bullish_{htf_name}'] = False
        df[f'htf_poi_bearish_{htf_name}'] = False
        df[f'htf_poi_high_{htf_name}'] = np.nan
        df[f'htf_poi_low_{htf_name}'] = np.nan

        for ob in top_obs:
            # Mark candles within HTF order block range
            in_range = (df['low'] <= ob.high) & (df['high'] >= ob.low)

            if ob.is_bullish:
                df.loc[in_range, f'htf_poi_bullish_{htf_name}'] = True
            else:
                df.loc[in_range, f'htf_poi_bearish_{htf_name}'] = True

            df.loc[in_range, f'htf_poi_high_{htf_name}'] = ob.high
            df.loc[in_range, f'htf_poi_low_{htf_name}'] = ob.low

        self.df = df
        return df

    def calculate_all_indicators(self) -> pd.DataFrame:
        """Calculate all ICT indicators"""
        self.detect_fair_value_gaps()
        self.detect_order_blocks()
        self.detect_liquidity_sweeps()
        self.calculate_daily_bias()

        return self.df


if __name__ == "__main__":
    # Example usage
    import ccxt

    # Fetch some sample data
    exchange = ccxt.binance({'enableRateLimit': True})
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '5m', limit=1000)

    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # Calculate indicators
    ict = ICTIndicators(df)
    result = ict.calculate_all_indicators()

    print("\nICT Indicators calculated:")
    print(result[['close', 'fvg_bullish', 'fvg_bearish', 'ob_bullish', 'ob_bearish', 'liquidity_sweep']].tail(20))
