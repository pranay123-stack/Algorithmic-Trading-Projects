"""Tests for core domain types."""

from __future__ import annotations

from polybot.types import (
    Fill,
    Market,
    MarketStatus,
    Order,
    OrderStatus,
    Position,
    PriceSnapshot,
    Side,
    TokenPair,
)


class TestOrder:
    def test_new_id_unique(self) -> None:
        ids = {Order.new_id() for _ in range(100)}
        assert len(ids) == 100

    def test_record_fill_partial(self) -> None:
        order = Order(
            client_order_id="test",
            market_id="m1",
            token_id="t1",
            side=Side.BUY,
            price=0.50,
            size=100.0,
        )
        order.record_fill(0.48, 50.0)
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_size == 50.0
        assert order.avg_fill_price == 0.48

    def test_record_fill_complete(self) -> None:
        order = Order(
            client_order_id="test",
            market_id="m1",
            token_id="t1",
            side=Side.BUY,
            price=0.50,
            size=100.0,
        )
        order.record_fill(0.50, 100.0)
        assert order.status == OrderStatus.FILLED
        assert order.filled_size == 100.0

    def test_record_fill_multiple(self) -> None:
        order = Order(
            client_order_id="test",
            market_id="m1",
            token_id="t1",
            side=Side.BUY,
            price=0.50,
            size=100.0,
        )
        order.record_fill(0.48, 60.0)
        order.record_fill(0.52, 40.0)
        assert order.status == OrderStatus.FILLED
        expected_avg = (0.48 * 60 + 0.52 * 40) / 100
        assert abs(order.avg_fill_price - expected_avg) < 1e-10


class TestPosition:
    def test_mark_to_market_buy(self) -> None:
        pos = Position(
            market_id="m1",
            token_id="t1",
            side=Side.BUY,
            entry_price=0.40,
            size=100.0,
        )
        pos.mark_to_market(0.55)
        assert pos.current_price == 0.55
        assert abs(pos.unrealized_pnl - 15.0) < 1e-10  # (0.55 - 0.40) * 100

    def test_mark_to_market_sell(self) -> None:
        pos = Position(
            market_id="m1",
            token_id="t1",
            side=Side.SELL,
            entry_price=0.60,
            size=100.0,
        )
        pos.mark_to_market(0.45)
        assert abs(pos.unrealized_pnl - 15.0) < 1e-10  # (0.60 - 0.45) * 100


class TestPriceSnapshot:
    def test_immutable(self) -> None:
        snap = PriceSnapshot("m1", 0.5, 0.5, 1000.0, 500.0, 0.0)
        assert snap.market_id == "m1"
        assert snap.yes_price == 0.5


class TestTokenPair:
    def test_access(self) -> None:
        tp = TokenPair("cond-1", "yes-1", "no-1")
        assert tp.condition_id == "cond-1"
        assert tp.yes_token_id == "yes-1"
        assert tp.no_token_id == "no-1"
