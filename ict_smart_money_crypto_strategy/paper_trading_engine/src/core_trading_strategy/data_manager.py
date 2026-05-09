"""
Data Manager Module
Handles market data fetching and management
(Cache removed - aligned scheduler fetches only on candle close)
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import time
import os
from dotenv import load_dotenv
from src.logger.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


class DataManager:
    """
    Manages market data

    Features:
    - Exchange connection handling
    - Real-time data fetching
    - Historical data management
    - Error handling and retries

    Note: Cache removed - with aligned scheduler, bot only fetches
    once per candle close, so caching is unnecessary.
    """

    def __init__(
        self,
        exchange_name: str = 'binance',
        testnet: bool = True,
        lookback_candles: int = 500,
        retry_attempts: int = 3,
        retry_delay: int = 5
    ):
        """
        Initialize data manager

        Args:
            exchange_name: Exchange name (e.g., 'binance')
            testnet: Use testnet (True) or production (False)
            lookback_candles: Number of historical candles to maintain
            retry_attempts: Number of retry attempts on failure
            retry_delay: Delay between retries (seconds)
        """
        self.exchange_name = exchange_name
        self.testnet = testnet
        self.lookback_candles = lookback_candles
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        # Initialize exchange
        self.exchange = self._initialize_exchange()

    def _initialize_exchange(self) -> ccxt.Exchange:
        """
        Initialize exchange connection with API keys from environment

        Returns:
            CCXT exchange object
        """
        try:
            exchange_class = getattr(ccxt, self.exchange_name)

            # Load API keys from .env file
            if self.testnet:
                api_key = os.getenv('BINANCE_TESTNET_API_KEY', '')
                secret_key = os.getenv('BINANCE_TESTNET_SECRET_KEY', '')
                mode = "Testnet"
            else:
                api_key = os.getenv('BINANCE_API_KEY', '')
                secret_key = os.getenv('BINANCE_SECRET_KEY', '')
                mode = "Production (Read-Only)"

            # Initialize exchange configuration
            config = {
                'enableRateLimit': True,
            }

            # Add API keys if available
            if api_key and secret_key:
                config['apiKey'] = api_key
                config['secret'] = secret_key
                logger.info(f"API keys loaded from environment ({mode} mode)")
            else:
                logger.warning(f"No API keys found in .env file - using public endpoints only")

            exchange = exchange_class(config)

            if self.testnet:
                # Set testnet URLs
                if self.exchange_name == 'binance':
                    exchange.set_sandbox_mode(True)
                    logger.info("Using Binance Testnet")
                else:
                    logger.warning(f"Testnet not configured for {self.exchange_name}")
            else:
                logger.info(f"Using REAL Binance (Production) with READ-ONLY API keys")

            logger.info(f"Exchange initialized: {self.exchange_name}")
            return exchange

        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            raise

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: Optional[int] = None,
        since: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data with retry logic

        Args:
            symbol: Trading symbol (e.g., 'ETH/USDT')
            timeframe: Timeframe (e.g., '15m')
            limit: Number of candles to fetch
            since: Timestamp to fetch from (ms)

        Returns:
            DataFrame with OHLCV data
        """
        limit = limit or self.lookback_candles

        logger.debug(f"Starting OHLCV fetch: {symbol} {timeframe}, limit={limit}, since={since}")

        for attempt in range(self.retry_attempts):
            try:
                logger.debug(f"Fetch attempt {attempt + 1}/{self.retry_attempts}: Calling exchange API...")

                # Fetch data
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit,
                    since=since
                )

                logger.debug(f"Received {len(ohlcv)} raw OHLCV records from exchange")

                # Convert to DataFrame
                df = pd.DataFrame(
                    ohlcv,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)

                logger.debug(
                    f"Converted to DataFrame: {len(df)} candles, "
                    f"range: {df.index[0]} to {df.index[-1]}, "
                    f"latest close: {df['close'].iloc[-1]:.2f}"
                )

                logger.info(f"📊 Fetched {len(df)} candles for {symbol} {timeframe}")

                return df

            except Exception as e:
                logger.warning(
                    f"Fetch attempt {attempt + 1}/{self.retry_attempts} failed: {e}"
                )

                if attempt < self.retry_attempts - 1:
                    logger.debug(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to fetch OHLCV after {self.retry_attempts} attempts")
                    raise

    def update_data(
        self,
        symbol: str,
        timeframe: str
    ) -> pd.DataFrame:
        """
        Fetch fresh market data

        Note: Simplified - always fetches fresh data since aligned scheduler
        only calls this once per candle close.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe

        Returns:
            Fresh DataFrame
        """
        logger.debug(f"update_data called for {symbol} {timeframe}")
        return self.fetch_ohlcv(symbol, timeframe)

    def get_stats(self) -> dict:
        """Get data manager statistics"""
        return {
            'exchange': self.exchange_name,
            'testnet': self.testnet,
            'lookback_candles': self.lookback_candles
        }
