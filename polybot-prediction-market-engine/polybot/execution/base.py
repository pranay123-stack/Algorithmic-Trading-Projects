"""Abstract base class for order execution."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from polybot.types import Fill, Order, Position


class BaseExecutor(ABC):
    """Interface that all executors (paper, live) must implement.

    Also acts as an async context manager for resource lifecycle.
    """

    def __init__(self) -> None:
        self._event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def __aenter__(self) -> "BaseExecutor":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        pass

    @abstractmethod
    async def place_order(self, order: Order) -> Order: ...

    @abstractmethod
    async def cancel_order(self, client_order_id: str) -> bool: ...

    @abstractmethod
    async def get_order(self, client_order_id: str) -> Order | None: ...

    @abstractmethod
    async def get_open_orders(self) -> list[Order]: ...

    @abstractmethod
    async def cancel_all(self) -> int: ...

    @abstractmethod
    async def get_positions(self) -> list[Position]: ...

    @abstractmethod
    async def get_balance(self) -> float: ...

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Non-blocking event enqueue for telemetry / notifications."""
        self._event_queue.put_nowait({"type": event_type, **data})
