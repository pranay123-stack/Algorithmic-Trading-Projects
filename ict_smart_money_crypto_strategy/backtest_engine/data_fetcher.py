"""
CCXT Data Fetcher for Multi-Timeframe Analysis
Fetches historical data from Binance for ICT/SMC strategy
"""
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time


class MultiTimeframeDataFetcher:
    """Fetches and manages multi-timeframe OHLCV data from Binance"""

    def __init__(self, symbol: str = 'BTC/USDT', exchange_id: str = 'binance'):
        """
        Initialize data fetcher

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            exchange_id: CCXT exchange identifier
        """
        self.symbol = symbol
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}  # Use futures for more liquidity
        })
        self.timeframes = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        }
        self.data_cache: Dict[str, pd.DataFrame] = {}

    def fetch_ohlcv(
        self,
        timeframe: str,
        since: Optional[datetime] = None,
        limit: int = 1000,
        days_back: int = 90
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a specific timeframe

        Args:
            timeframe: Candle timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            since: Start datetime (if None, uses days_back)
            limit: Max candles per request
            days_back: Days to look back if since is None

        Returns:
            DataFrame with OHLCV data
        """
        if since is None:
            since = datetime.now() - timedelta(days=days_back)

        since_ts = int(since.timestamp() * 1000)
        all_candles = []

        print(f"Fetching {timeframe} data for {self.symbol}...")

        while True:
            try:
                candles = self.exchange.fetch_ohlcv(
                    self.symbol,
                    timeframe=timeframe,
                    since=since_ts,
                    limit=limit
                )

                if not candles:
                    break

                all_candles.extend(candles)

                # Update since_ts to last candle timestamp
                since_ts = candles[-1][0] + 1

                # Break if we've caught up to current time
                if len(candles) < limit:
                    break

                time.sleep(self.exchange.rateLimit / 1000)

            except Exception as e:
                print(f"Error fetching {timeframe} data: {e}")
                break

        # Convert to DataFrame
        df = pd.DataFrame(
            all_candles,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df = df.astype(float)

        print(f"Fetched {len(df)} {timeframe} candles from {df.index[0]} to {df.index[-1]}")

        return df

    def fetch_multi_timeframe(
        self,
        timeframes: List[str] = ['1m', '5m', '15m', '1h', '4h', '1d'],
        days_back: int = 90
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple timeframes

        Args:
            timeframes: List of timeframes to fetch
            days_back: Days of historical data

        Returns:
            Dictionary mapping timeframe -> DataFrame
        """
        data = {}

        for tf in timeframes:
            df = self.fetch_ohlcv(tf, days_back=days_back)
            data[tf] = df
            self.data_cache[tf] = df

        return data

    def align_timeframes(
        self,
        base_tf: str = '5m',
        higher_tfs: List[str] = ['1h', '4h', '1d']
    ) -> pd.DataFrame:
        """
        Align higher timeframe data to base timeframe
        Useful for accessing HTF context on lower timeframe candles

        Args:
            base_tf: Base timeframe for trading
            higher_tfs: Higher timeframes for context

        Returns:
            Merged DataFrame with all timeframes aligned
        """
        if base_tf not in self.data_cache:
            raise ValueError(f"Base timeframe {base_tf} not in cache. Fetch data first.")

        base_df = self.data_cache[base_tf].copy()

        for htf in higher_tfs:
            if htf not in self.data_cache:
                print(f"Warning: {htf} not in cache, skipping")
                continue

            htf_df = self.data_cache[htf].copy()

            # Rename columns to include timeframe
            htf_df.columns = [f'{col}_{htf}' for col in htf_df.columns]

            # Merge using forward fill (each lower TF candle gets most recent HTF data)
            base_df = pd.merge_asof(
                base_df.reset_index(),
                htf_df.reset_index().rename(columns={'timestamp': f'timestamp_{htf}'}),
                left_on='timestamp',
                right_on=f'timestamp_{htf}',
                direction='backward'
            )
            base_df.set_index('timestamp', inplace=True)
            base_df.drop(columns=[f'timestamp_{htf}'], inplace=True, errors='ignore')

        return base_df

    def save_to_csv(self, output_dir: str = './data'):
        """Save cached data to CSV files"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        for tf, df in self.data_cache.items():
            filename = f"{output_dir}/{self.symbol.replace('/', '_')}_{tf}.csv"
            df.to_csv(filename)
            print(f"Saved {tf} data to {filename}")

    def load_from_csv(self, input_dir: str = './data') -> Dict[str, pd.DataFrame]:
        """Load data from CSV files"""
        import os
        import glob

        pattern = f"{input_dir}/{self.symbol.replace('/', '_')}_*.csv"
        files = glob.glob(pattern)

        for file in files:
            # Extract timeframe from filename
            tf = file.split('_')[-1].replace('.csv', '')
            df = pd.read_csv(file, index_col='timestamp', parse_dates=True)
            self.data_cache[tf] = df
            print(f"Loaded {tf} data from {file}")

        return self.data_cache


if __name__ == "__main__":
    # Example usage
    fetcher = MultiTimeframeDataFetcher(symbol='BTC/USDT')

    # Fetch multi-timeframe data
    data = fetcher.fetch_multi_timeframe(
        timeframes=['5m', '15m', '1h', '4h', '1d'],
        days_back=60
    )

    # Align timeframes
    aligned_df = fetcher.align_timeframes(
        base_tf='5m',
        higher_tfs=['1h', '4h', '1d']
    )

    print("\nAligned DataFrame shape:", aligned_df.shape)
    print(aligned_df.head())

    # Save to CSV
    fetcher.save_to_csv('./data')
