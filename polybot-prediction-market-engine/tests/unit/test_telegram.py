"""Tests for Telegram notifier."""

from __future__ import annotations

import pytest

from polybot.notifications.telegram import TelegramNotifier
from polybot.types import Fill, Order, Signal, SignalAction, Side


class TestTelegramFormatters:
    def test_format_signal(self) -> None:
        sig = Signal(
            market_id="m1",
            action=SignalAction.BUY_YES,
            token_id="yes-1",
            target_price=0.35,
            size_usdc=25.0,
            rule_name="cheap_buy",
        )
        text = TelegramNotifier.format_signal(sig)
        assert "cheap_buy" in text
        assert "BUY_YES" in text
        assert "0.3500" in text

    def test_format_order(self) -> None:
        order = Order(
            client_order_id="test-order",
            market_id="m1",
            token_id="yes-1",
            side=Side.BUY,
            price=0.40,
            size=50.0,
        )
        text = TelegramNotifier.format_order(order)
        assert "test-order" in text
        assert "BUY" in text

    def test_format_fill(self) -> None:
        fill = Fill(order_id="order-1", price=0.45, size=100.0, fee=0.0)
        text = TelegramNotifier.format_fill(fill)
        assert "order-1" in text
        assert "0.4500" in text


class TestTelegramNotifyFiltering:
    @pytest.mark.asyncio
    async def test_skip_unsubscribed_events(self) -> None:
        notifier = TelegramNotifier(
            bot_token="fake",
            chat_id="123",
            notify_on=["signal"],  # only signal
        )
        # Should not raise, just skip
        await notifier.notify("order_filled", "test message")
        assert notifier._queue.empty()

    @pytest.mark.asyncio
    async def test_queue_subscribed_event(self) -> None:
        notifier = TelegramNotifier(
            bot_token="fake",
            chat_id="123",
            notify_on=["signal"],
        )
        await notifier.notify("signal", "test signal")
        assert not notifier._queue.empty()
