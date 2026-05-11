"""Tests for the paper (simulated) executor."""

from __future__ import annotations

import pytest

from polybot.execution.paper import PaperExecutor
from polybot.types import Order, OrderStatus, PriceSnapshot, Side


@pytest.fixture
def executor() -> PaperExecutor:
    return PaperExecutor(initial_balance=1000.0, taker_fee_bps=0.0)


class TestPaperExecutor:
    @pytest.mark.asyncio
    async def test_place_order(self, executor: PaperExecutor) -> None:
        order = Order(
            client_order_id=Order.new_id(),
            market_id="m1",
            token_id="yes-1",
            side=Side.BUY,
            price=0.40,
            size=100.0,
        )
        result = await executor.place_order(order)
        assert result.status == OrderStatus.OPEN
        open_orders = await executor.get_open_orders()
        assert len(open_orders) == 1

    @pytest.mark.asyncio
    async def test_reject_insufficient_balance(self, executor: PaperExecutor) -> None:
        order = Order(
            client_order_id=Order.new_id(),
            market_id="m1",
            token_id="yes-1",
            side=Side.BUY,
            price=0.50,
            size=3000.0,  # 0.50 * 3000 = 1500 > 1000 balance
        )
        result = await executor.place_order(order)
        assert result.status == OrderStatus.REJECTED

    @pytest.mark.asyncio
    async def test_cancel_order(self, executor: PaperExecutor) -> None:
        order = Order(
            client_order_id="cancel-me",
            market_id="m1",
            token_id="yes-1",
            side=Side.BUY,
            price=0.40,
            size=10.0,
        )
        await executor.place_order(order)
        assert await executor.cancel_order("cancel-me") is True
        assert await executor.cancel_order("nonexistent") is False
        assert len(await executor.get_open_orders()) == 0

    @pytest.mark.asyncio
    async def test_cancel_all(self, executor: PaperExecutor) -> None:
        for i in range(3):
            await executor.place_order(
                Order(
                    client_order_id=f"order-{i}",
                    market_id="m1",
                    token_id="yes-1",
                    side=Side.BUY,
                    price=0.40,
                    size=10.0,
                )
            )
        assert await executor.cancel_all() == 3
        assert len(await executor.get_open_orders()) == 0

    @pytest.mark.asyncio
    async def test_fill_buy_order(self, executor: PaperExecutor) -> None:
        order = Order(
            client_order_id="fill-me",
            market_id="m1",
            token_id="yes-1",
            side=Side.BUY,
            price=0.50,
            size=100.0,
        )
        await executor.place_order(order)

        # Price drops below limit -> should fill
        snapshots = {"m1": PriceSnapshot("m1", 0.45, 0.55, 1000.0, 500.0, 0.0)}
        fills = executor.process_snapshots(snapshots)
        assert len(fills) == 1
        assert fills[0].price == 0.45
        assert fills[0].size == 100.0

        # Balance should decrease
        balance = await executor.get_balance()
        assert balance < 1000.0

    @pytest.mark.asyncio
    async def test_fill_sell_order(self, executor: PaperExecutor) -> None:
        # First buy a position
        buy = Order(
            client_order_id="buy-first",
            market_id="m1",
            token_id="yes-1",
            side=Side.BUY,
            price=0.50,
            size=100.0,
        )
        await executor.place_order(buy)
        executor.process_snapshots({"m1": PriceSnapshot("m1", 0.45, 0.55, 1000.0, 500.0, 0.0)})

        # Now sell
        sell = Order(
            client_order_id="sell-it",
            market_id="m1",
            token_id="yes-1",
            side=Side.SELL,
            price=0.60,
            size=100.0,
        )
        await executor.place_order(sell)
        fills = executor.process_snapshots({"m1": PriceSnapshot("m1", 0.65, 0.35, 1000.0, 500.0, 0.0)})
        assert len(fills) == 1

    @pytest.mark.asyncio
    async def test_no_fill_when_price_not_crossed(self, executor: PaperExecutor) -> None:
        order = Order(
            client_order_id="no-fill",
            market_id="m1",
            token_id="yes-1",
            side=Side.BUY,
            price=0.30,
            size=100.0,
        )
        await executor.place_order(order)

        # Price above limit -> no fill
        snapshots = {"m1": PriceSnapshot("m1", 0.50, 0.50, 1000.0, 500.0, 0.0)}
        fills = executor.process_snapshots(snapshots)
        assert len(fills) == 0
        assert len(await executor.get_open_orders()) == 1

    @pytest.mark.asyncio
    async def test_position_tracking(self, executor: PaperExecutor) -> None:
        order = Order(
            client_order_id="pos-track",
            market_id="m1",
            token_id="yes-1",
            side=Side.BUY,
            price=0.50,
            size=100.0,
        )
        await executor.place_order(order)
        executor.process_snapshots({"m1": PriceSnapshot("m1", 0.45, 0.55, 1000.0, 500.0, 0.0)})

        positions = await executor.get_positions()
        assert len(positions) == 1
        assert positions[0].market_id == "m1"
        assert positions[0].entry_price == 0.45

    @pytest.mark.asyncio
    async def test_get_balance(self, executor: PaperExecutor) -> None:
        balance = await executor.get_balance()
        assert balance == 1000.0
