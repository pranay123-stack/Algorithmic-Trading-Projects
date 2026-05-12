"""Async exchange abstraction over CCXT."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import ccxt.async_support as ccxt_async
import pandas as pd

from config import Config
from utils.log import get_logger

log = get_logger(__name__)


class ExchangeClient:
    """Unified async wrapper around a CCXT exchange instance."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        exc_cfg = cfg.exchange
        cls = getattr(ccxt_async, exc_cfg.name)
        params: Dict[str, Any] = {
            "apiKey": exc_cfg.api_key or None,
            "secret": exc_cfg.api_secret or None,
            "enableRateLimit": exc_cfg.rate_limit,
            "timeout": exc_cfg.timeout,
        }
        if exc_cfg.passphrase:
            params["password"] = exc_cfg.passphrase
        if exc_cfg.testnet:
            params["sandbox"] = True

        self._exchange: ccxt_async.Exchange = cls(params)
        self._markets_loaded = False

    async def _ensure_markets(self) -> None:
        if not self._markets_loaded:
            await self._exchange.load_markets()
            self._markets_loaded = True

    # ── Market data ────────────────────────────────────────

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "5m",
        since: Optional[int] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        await self._ensure_markets()
        raw = await self._exchange.fetch_ohlcv(
            symbol, timeframe=timeframe, since=since, limit=limit
        )
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        return df

    async def fetch_history(
        self, symbol: str, timeframe: str, days: int
    ) -> pd.DataFrame:
        """Paginate backwards to get `days` of history."""
        await self._ensure_markets()
        now = datetime.utcnow()
        since_dt = now - timedelta(days=days)
        since_ms = int(since_dt.timestamp() * 1000)

        all_frames: List[pd.DataFrame] = []
        cursor = since_ms
        while True:
            raw = await self._exchange.fetch_ohlcv(
                symbol, timeframe=timeframe, since=cursor, limit=1000
            )
            if not raw:
                break
            df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            all_frames.append(df)
            last_ts = raw[-1][0]
            if last_ts >= int(now.timestamp() * 1000) or len(raw) < 1000:
                break
            cursor = last_ts + 1
            await asyncio.sleep(self._exchange.rateLimit / 1000)

        if not all_frames:
            return pd.DataFrame()
        result = pd.concat(all_frames)
        return result[~result.index.duplicated(keep="last")].sort_index()

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        await self._ensure_markets()
        return await self._exchange.fetch_ticker(symbol)

    async def fetch_order_book(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        await self._ensure_markets()
        return await self._exchange.fetch_order_book(symbol, limit=limit)

    # ── Trading ────────────────────────────────────────────

    async def create_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str = "limit",
        price: Optional[float] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        await self._ensure_markets()
        log.info("ORDER %s %s %.6f %s @ %s", side, symbol, amount, order_type, price)
        return await self._exchange.create_order(
            symbol, order_type, side, amount, price, params or {}
        )

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        await self._ensure_markets()
        return await self._exchange.cancel_order(order_id, symbol)

    async def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        await self._ensure_markets()
        return await self._exchange.fetch_order(order_id, symbol)

    async def fetch_balance(self) -> Dict[str, Any]:
        await self._ensure_markets()
        return await self._exchange.fetch_balance()

    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        await self._ensure_markets()
        return await self._exchange.fetch_open_orders(symbol)

    # ── Helpers ─────────────────────────────────────────────

    def market_info(self, symbol: str) -> Dict[str, Any]:
        return self._exchange.markets.get(symbol, {})

    async def close(self) -> None:
        await self._exchange.close()
