"""Live order execution with retry logic and partial fill handling."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, Optional

from config import Config
from exchanges.base import ExchangeClient
from utils.log import get_logger
from utils.types import OrderStatus, Side

log = get_logger(__name__)


class LiveExecutor:
    """Wraps exchange client with retry, chase, and partial-fill logic."""

    def __init__(self, cfg: Config, exchange: ExchangeClient) -> None:
        self.cfg = cfg
        self.exc = cfg.execution
        self.exchange = exchange

    async def execute_order(
        self,
        symbol: str,
        side: Side,
        qty: float,
        price: float,
        order_type: Optional[str] = None,
    ) -> Dict:
        otype = order_type or self.exc.order_type
        ccxt_side = "buy" if side == Side.LONG else "sell"

        for attempt in range(1, self.exc.max_retries + 1):
            try:
                if otype == "market":
                    result = await self.exchange.create_order(
                        symbol, ccxt_side, qty, "market"
                    )
                else:
                    result = await self.exchange.create_order(
                        symbol, ccxt_side, qty, "limit", price
                    )

                order_id = result["id"]

                # Wait for fill
                filled = await self._wait_for_fill(order_id, symbol)
                if filled:
                    return filled

                # Partial fill handling — cancel and retry remainder
                order_info = await self.exchange.fetch_order(order_id, symbol)
                filled_qty = order_info.get("filled", 0)
                remaining = qty - filled_qty

                if filled_qty > 0:
                    log.warning(
                        "Partial fill %.6f / %.6f on %s — cancelling remainder",
                        filled_qty, qty, symbol,
                    )

                await self.exchange.cancel_order(order_id, symbol)

                if remaining > 0 and attempt < self.exc.max_retries:
                    # Chase: adjust price
                    chase_adj = self.exc.limit_chase_ticks * 0.01
                    if side == Side.LONG:
                        price *= (1 + chase_adj)
                    else:
                        price *= (1 - chase_adj)
                    qty = remaining
                    log.info("Retrying %s %s remaining %.6f @ %.4f (attempt %d)",
                             ccxt_side, symbol, qty, price, attempt + 1)
                    await asyncio.sleep(self.exc.retry_delay_s)
                    continue

                return order_info

            except Exception as e:
                log.error("Order error attempt %d: %s", attempt, e)
                if attempt < self.exc.max_retries:
                    await asyncio.sleep(self.exc.retry_delay_s)
                else:
                    raise

        return {"status": OrderStatus.REJECTED.value, "error": "Max retries exceeded"}

    async def _wait_for_fill(self, order_id: str, symbol: str) -> Optional[Dict]:
        """Poll until filled or timeout."""
        deadline = asyncio.get_event_loop().time() + self.exc.partial_fill_timeout_s
        while asyncio.get_event_loop().time() < deadline:
            order = await self.exchange.fetch_order(order_id, symbol)
            status = order.get("status", "")
            if status == "closed":
                log.info("LIVE FILL %s %s", order_id, symbol)
                return order
            if status in ("canceled", "cancelled", "expired", "rejected"):
                return None
            await asyncio.sleep(0.5)
        return None

    async def cancel_order(self, order_id: str, symbol: str) -> Dict:
        return await self.exchange.cancel_order(order_id, symbol)
