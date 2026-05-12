"""WebSocket streaming for real-time candle / trade data."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Coroutine, Dict, List, Optional

import websockets

from utils.log import get_logger

log = get_logger(__name__)

# Binance-style WS base URLs
_WS_URLS = {
    "binance": "wss://stream.binance.com:9443/ws",
    "bybit": "wss://stream.bybit.com/v5/public/spot",
    "okx": "wss://ws.okx.com:8443/ws/v5/public",
}


class WebSocketStream:
    """Manages a persistent WS connection for multiple symbols."""

    def __init__(
        self,
        exchange_name: str,
        symbols: List[str],
        timeframe: str = "5m",
        on_candle: Optional[Callable[[str, Dict[str, Any]], Coroutine]] = None,
    ) -> None:
        self.exchange_name = exchange_name.lower()
        self.symbols = symbols
        self.timeframe = timeframe
        self.on_candle = on_candle
        self._ws = None
        self._running = False

    def _build_binance_url(self) -> str:
        tf_map = {"1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m"}
        tf = tf_map.get(self.timeframe, "5m")
        streams = "/".join(
            f"{s.replace('/', '').lower()}@kline_{tf}" for s in self.symbols
        )
        return f"wss://stream.binance.com:9443/stream?streams={streams}"

    def _parse_binance(self, raw: Dict) -> Optional[Dict[str, Any]]:
        data = raw.get("data", {})
        k = data.get("k", {})
        if not k or not k.get("x"):  # only closed candles
            return None
        symbol = k["s"]
        return {
            "symbol": symbol,
            "timestamp": k["t"],
            "open": float(k["o"]),
            "high": float(k["h"]),
            "low": float(k["l"]),
            "close": float(k["c"]),
            "volume": float(k["v"]),
        }

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                url = self._build_binance_url() if self.exchange_name == "binance" else _WS_URLS.get(self.exchange_name, "")
                log.info("WS connecting to %s", url)
                async with websockets.connect(url, ping_interval=20) as ws:
                    self._ws = ws
                    # For bybit/okx send subscription messages
                    if self.exchange_name == "bybit":
                        sub = {"op": "subscribe", "args": [
                            f"kline.{self.timeframe}.{s.replace('/', '')}" for s in self.symbols
                        ]}
                        await ws.send(json.dumps(sub))
                    elif self.exchange_name == "okx":
                        sub = {"op": "subscribe", "args": [
                            {"channel": f"candle{self.timeframe}", "instId": s.replace("/", "-")}
                            for s in self.symbols
                        ]}
                        await ws.send(json.dumps(sub))

                    async for msg in ws:
                        if not self._running:
                            break
                        try:
                            data = json.loads(msg)
                            candle = self._parse_binance(data) if self.exchange_name == "binance" else data
                            if candle and self.on_candle:
                                await self.on_candle(candle.get("symbol", ""), candle)
                        except (json.JSONDecodeError, KeyError) as e:
                            log.warning("WS parse error: %s", e)
            except Exception as e:
                log.error("WS connection error: %s — reconnecting in 5s", e)
                await asyncio.sleep(5)

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
