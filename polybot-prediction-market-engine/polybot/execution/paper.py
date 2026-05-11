"""Paper (simulated) execution engine.

Maintains an internal order book, balance, and position tracker.
Limit orders fill when the market price crosses the order price.
"""

from __future__ import annotations

import time

from polybot.execution.base import BaseExecutor
from polybot.telemetry import get_logger
from polybot.types import (
    Fill,
    Order,
    OrderStatus,
    Position,
    PriceSnapshot,
    Side,
)

logger = get_logger(__name__)


class PaperExecutor(BaseExecutor):
    """Simulates Polymarket order execution locally."""

    def __init__(
        self,
        *,
        initial_balance: float = 1000.0,
        taker_fee_bps: float = 0.0,
    ) -> None:
        super().__init__()
        self._balance = initial_balance
        self._initial_balance = initial_balance
        self._fee_rate = taker_fee_bps / 10_000
        self._resting_orders: dict[str, Order] = {}
        self._filled_orders: dict[str, Order] = {}
        self._positions: dict[str, Position] = {}  # keyed by token_id
        self._fills: list[Fill] = []

    # ------------------------------------------------------------------
    # BaseExecutor interface
    # ------------------------------------------------------------------

    async def place_order(self, order: Order) -> Order:
        cost = order.price * order.size
        fee = cost * self._fee_rate

        if order.side == Side.BUY and (cost + fee) > self._balance:
            order.status = OrderStatus.REJECTED
            logger.warning("order_rejected", reason="insufficient_balance", order_id=order.client_order_id)
            self._emit_event("order_rejected", {"order_id": order.client_order_id, "reason": "insufficient_balance"})
            return order

        order.status = OrderStatus.OPEN
        self._resting_orders[order.client_order_id] = order
        logger.info("order_placed", order_id=order.client_order_id, side=order.side.name, price=order.price, size=order.size)
        self._emit_event("order_placed", {"order_id": order.client_order_id})
        return order

    async def cancel_order(self, client_order_id: str) -> bool:
        order = self._resting_orders.pop(client_order_id, None)
        if order is None:
            return False
        order.status = OrderStatus.CANCELLED
        logger.info("order_cancelled", order_id=client_order_id)
        return True

    async def get_order(self, client_order_id: str) -> Order | None:
        return (
            self._resting_orders.get(client_order_id)
            or self._filled_orders.get(client_order_id)
        )

    async def get_open_orders(self) -> list[Order]:
        return list(self._resting_orders.values())

    async def cancel_all(self) -> int:
        count = len(self._resting_orders)
        for order in self._resting_orders.values():
            order.status = OrderStatus.CANCELLED
        self._resting_orders.clear()
        return count

    async def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    async def get_balance(self) -> float:
        return self._balance

    # ------------------------------------------------------------------
    # Simulation engine
    # ------------------------------------------------------------------

    def process_snapshots(
        self,
        snapshots: dict[str, PriceSnapshot],
    ) -> list[Fill]:
        """Check resting orders against current prices and fill if crossed.

        Called once per polling cycle.
        """
        fills: list[Fill] = []
        filled_ids: list[str] = []

        for order_id, order in self._resting_orders.items():
            snapshot = snapshots.get(order.market_id)
            if snapshot is None:
                continue

            # Determine the relevant price for this token
            fill_price = self._get_fill_price(order, snapshot)
            if fill_price is None:
                continue

            # Check if the limit crosses
            if order.side == Side.BUY and fill_price <= order.price:
                fill = self._execute_fill(order, fill_price)
                fills.append(fill)
                filled_ids.append(order_id)
            elif order.side == Side.SELL and fill_price >= order.price:
                fill = self._execute_fill(order, fill_price)
                fills.append(fill)
                filled_ids.append(order_id)

        # Move filled orders out of resting
        for oid in filled_ids:
            order = self._resting_orders.pop(oid)
            self._filled_orders[oid] = order

        # Mark to market all positions
        for pos in self._positions.values():
            for snap in snapshots.values():
                if snap.market_id == pos.market_id:
                    pos.mark_to_market(snap.yes_price)

        return fills

    def _get_fill_price(
        self,
        order: Order,
        snapshot: PriceSnapshot,
    ) -> float | None:
        """Determine the relevant market price for an order's token."""
        # YES token
        if order.token_id == snapshot.market_id or "yes" in order.token_id.lower():
            return snapshot.yes_price
        # NO token
        if "no" in order.token_id.lower():
            return snapshot.no_price
        # Fallback: use yes_price
        return snapshot.yes_price

    def _execute_fill(self, order: Order, fill_price: float) -> Fill:
        """Record a fill, update balance and position tracking."""
        fee = fill_price * order.size * self._fee_rate
        fill = Fill(
            order_id=order.client_order_id,
            price=fill_price,
            size=order.size,
            fee=fee,
            timestamp=time.time(),
        )
        order.record_fill(fill_price, order.size)
        self._fills.append(fill)

        # Update balance
        if order.side == Side.BUY:
            self._balance -= (fill_price * order.size) + fee
        else:
            self._balance += (fill_price * order.size) - fee

        # Update position
        self._update_position(order, fill_price)

        logger.info(
            "order_filled",
            order_id=order.client_order_id,
            fill_price=fill_price,
            size=order.size,
            fee=fee,
        )
        self._emit_event("order_filled", {
            "order_id": order.client_order_id,
            "fill_price": fill_price,
            "size": order.size,
        })
        return fill

    def _update_position(self, order: Order, fill_price: float) -> None:
        """Create or update a position after a fill."""
        key = order.token_id

        if order.side == Side.BUY:
            existing = self._positions.get(key)
            if existing and existing.side == Side.BUY:
                # Add to position
                total_size = existing.size + order.size
                existing.entry_price = (
                    (existing.entry_price * existing.size + fill_price * order.size)
                    / total_size
                )
                existing.size = total_size
            else:
                self._positions[key] = Position(
                    market_id=order.market_id,
                    token_id=order.token_id,
                    side=Side.BUY,
                    entry_price=fill_price,
                    size=order.size,
                    current_price=fill_price,
                )
        else:
            existing = self._positions.get(key)
            if existing:
                pnl = (fill_price - existing.entry_price) * order.size
                existing.realized_pnl += pnl
                existing.size -= order.size
                if existing.size <= 0:
                    del self._positions[key]

    @property
    def total_pnl(self) -> float:
        """Total realised + unrealised PnL."""
        realized = sum(p.realized_pnl for p in self._positions.values())
        unrealized = sum(p.unrealized_pnl for p in self._positions.values())
        return realized + unrealized
