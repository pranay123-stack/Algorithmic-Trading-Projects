"""Core domain types for Polybot.

Enums for categorical state, NamedTuples for immutable value objects,
and dataclasses (slots=True) for mutable domain entities.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, NamedTuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Side(Enum):
    BUY = auto()
    SELL = auto()


class OrderStatus(Enum):
    PENDING = auto()
    OPEN = auto()
    FILLED = auto()
    PARTIALLY_FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()


class OrderType(Enum):
    LIMIT = auto()


class SignalAction(Enum):
    BUY_YES = auto()
    BUY_NO = auto()
    SELL_YES = auto()
    SELL_NO = auto()


class MarketStatus(Enum):
    ACTIVE = auto()
    CLOSED = auto()
    RESOLVED = auto()


# ---------------------------------------------------------------------------
# Immutable value objects (NamedTuple)
# ---------------------------------------------------------------------------

class TokenPair(NamedTuple):
    """YES / NO condition-token pair on Polymarket."""

    condition_id: str
    yes_token_id: str
    no_token_id: str


class OrderBookLevel(NamedTuple):
    price: float   # 0.01 – 0.99
    size: float    # USDC amount


class OrderBookSnapshot(NamedTuple):
    token_id: str
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    timestamp: float


class PriceSnapshot(NamedTuple):
    """Point-in-time price state of a prediction market."""

    market_id: str
    yes_price: float   # 0.0 – 1.0
    no_price: float
    volume_24h: float
    liquidity: float
    timestamp: float


# ---------------------------------------------------------------------------
# Mutable domain objects (dataclass with slots)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Market:
    """A Polymarket prediction market."""

    id: str
    question: str
    condition_id: str
    tokens: TokenPair
    end_date: str
    status: MarketStatus = MarketStatus.ACTIVE
    last_price: PriceSnapshot | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Signal:
    """Trade signal emitted by the rules engine."""

    market_id: str
    action: SignalAction
    token_id: str
    target_price: float
    size_usdc: float
    rule_name: str
    score: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Order:
    """Limit order with fill tracking."""

    client_order_id: str
    market_id: str
    token_id: str
    side: Side
    price: float         # 0.01 – 0.99
    size: float          # USDC notional
    order_type: OrderType = OrderType.LIMIT
    status: OrderStatus = OrderStatus.PENDING
    created_at: float = field(default_factory=time.time)
    filled_size: float = 0.0
    avg_fill_price: float = 0.0

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:16]

    def record_fill(self, fill_price: float, fill_size: float) -> None:
        prev_notional = self.avg_fill_price * self.filled_size
        self.filled_size += fill_size
        self.avg_fill_price = (
            (prev_notional + fill_price * fill_size) / self.filled_size
            if self.filled_size > 0
            else 0.0
        )
        if self.filled_size >= self.size:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED


@dataclass(slots=True)
class Position:
    """Tracked position in a prediction market."""

    market_id: str
    token_id: str
    side: Side
    entry_price: float
    size: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    opened_at: float = field(default_factory=time.time)

    def mark_to_market(self, price: float) -> None:
        self.current_price = price
        if self.side == Side.BUY:
            self.unrealized_pnl = (price - self.entry_price) * self.size
        else:
            self.unrealized_pnl = (self.entry_price - price) * self.size


@dataclass(slots=True)
class Fill:
    """A single execution fill."""

    order_id: str
    price: float
    size: float
    fee: float = 0.0
    timestamp: float = field(default_factory=time.time)
