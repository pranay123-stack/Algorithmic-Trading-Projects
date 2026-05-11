"""Telegram notification service.

Sends formatted alerts via the Telegram Bot API using raw aiohttp
(no framework dependency).  Messages are queued and sent from a
background task to avoid blocking the main loop.
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from polybot.telemetry import get_logger
from polybot.types import Fill, Order, Signal

logger = get_logger(__name__)

_TELEGRAM_API = "https://api.telegram.org"

_EMOJI = {
    "signal": "\U0001f50d",       # magnifying glass
    "order_placed": "\U0001f4cb", # clipboard
    "order_filled": "\u2705",     # check mark
    "error": "\U0001f534",        # red circle
    "risk_breach": "\u26a0\ufe0f",  # warning
}


class TelegramNotifier:
    """Async Telegram notifier with background send loop."""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        notify_on: list[str] | None = None,
    ) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._notify_on = set(notify_on or ["signal", "order_placed", "order_filled", "error", "risk_breach"])
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """Start the background send loop."""
        self._session = aiohttp.ClientSession()
        self._task = asyncio.create_task(self._send_loop())

    async def stop(self) -> None:
        """Drain the queue and stop."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._session:
            await self._session.close()

    async def notify(
        self,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Queue a notification if event_type is in the notify_on list."""
        if event_type not in self._notify_on:
            return

        emoji = _EMOJI.get(event_type, "\u2139\ufe0f")
        text = f"{emoji} *{event_type.upper()}*\n{message}"
        self._queue.put_nowait(text)

    async def _send_loop(self) -> None:
        """Background task that drains the message queue."""
        while True:
            text = await self._queue.get()
            try:
                await self._send_message(text)
            except Exception as exc:
                logger.warning("telegram_send_error", error=str(exc))

    async def _send_message(self, text: str) -> None:
        """POST to the Telegram Bot API."""
        if not self._session:
            return

        url = f"{_TELEGRAM_API}/bot{self._bot_token}/sendMessage"
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }

        async with self._session.post(url, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.warning("telegram_api_error", status=resp.status, body=body)

    # ------------------------------------------------------------------
    # Message formatters
    # ------------------------------------------------------------------

    @staticmethod
    def format_signal(signal: Signal) -> str:
        return (
            f"Rule: {signal.rule_name}\n"
            f"Action: {signal.action.name}\n"
            f"Market: {signal.market_id}\n"
            f"Price: {signal.target_price:.4f}\n"
            f"Size: ${signal.size_usdc:.2f}"
        )

    @staticmethod
    def format_order(order: Order) -> str:
        return (
            f"Order: {order.client_order_id}\n"
            f"Side: {order.side.name}\n"
            f"Price: {order.price:.4f}\n"
            f"Size: ${order.size:.2f}\n"
            f"Status: {order.status.name}"
        )

    @staticmethod
    def format_fill(fill: Fill) -> str:
        return (
            f"Order: {fill.order_id}\n"
            f"Price: {fill.price:.4f}\n"
            f"Size: ${fill.size:.2f}\n"
            f"Fee: ${fill.fee:.4f}"
        )
