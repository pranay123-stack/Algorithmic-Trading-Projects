"""Paper trading execution simulator."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from config import Config
from utils.log import get_logger
from utils.types import OrderStatus, Side

log = get_logger(__name__)


class PaperExecutor:
    """Simulates order execution with configurable slippage."""

    def __init__(self, cfg: Config) -> None:
        self.slippage_bps = cfg.execution.slippage_bps
        self._orders: Dict[str, Dict] = {}

    async def execute_order(
        self,
        symbol: str,
        side: Side,
        qty: float,
        price: float,
        order_type: str = "market",
    ) -> Dict:
        """Simulate an immediate fill with slippage."""
        order_id = str(uuid.uuid4())[:12]

        # Apply slippage
        slip_pct = self.slippage_bps / 10000
        if side == Side.LONG:
            fill_price = price * (1 + slip_pct * random.uniform(0.5, 1.0))
        else:
            fill_price = price * (1 - slip_pct * random.uniform(0.5, 1.0))

        order = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side.value,
            "qty": qty,
            "requested_price": price,
            "fill_price": fill_price,
            "status": OrderStatus.FILLED.value,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "order_type": order_type,
        }
        self._orders[order_id] = order

        log.info(
            "PAPER FILL %s %s %.6f @ %.4f (req %.4f, slip %.1f bps)",
            side.value, symbol, qty, fill_price, price,
            abs(fill_price - price) / price * 10000,
        )
        return order

    async def cancel_order(self, order_id: str) -> Dict:
        order = self._orders.get(order_id)
        if order:
            order["status"] = OrderStatus.CANCELLED.value
        return order or {}

    def get_order(self, order_id: str) -> Optional[Dict]:
        return self._orders.get(order_id)
