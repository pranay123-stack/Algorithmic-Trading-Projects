from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Platform(str, Enum):
    KALSHI = "kalshi"
    POLYMARKET = "polymarket"


@dataclass
class OrderBookLevel:
    price: float  # probability 0.0-1.0
    size: float   # quantity in dollars or shares


@dataclass
class OrderBook:
    yes_bids: list[OrderBookLevel] = field(default_factory=list)
    yes_asks: list[OrderBookLevel] = field(default_factory=list)

    @property
    def best_yes_bid(self) -> float | None:
        return max((l.price for l in self.yes_bids), default=None)

    @property
    def best_yes_ask(self) -> float | None:
        return min((l.price for l in self.yes_asks), default=None)

    @property
    def best_no_bid(self) -> float | None:
        """Best no bid = 1 - best yes ask."""
        ask = self.best_yes_ask
        return round(1.0 - ask, 4) if ask is not None else None

    @property
    def best_no_ask(self) -> float | None:
        """Best no ask = 1 - best yes bid."""
        bid = self.best_yes_bid
        return round(1.0 - bid, 4) if bid is not None else None


@dataclass
class Market:
    platform: Platform
    market_id: str          # platform-specific ID (ticker for Kalshi, condition_id for Poly)
    title: str              # the question / market title
    category: str = ""
    status: str = "active"
    yes_price: float | None = None   # last/mid yes price (0-1)
    no_price: float | None = None
    volume: float = 0.0
    order_book: OrderBook | None = None
    # For Polymarket: need token IDs to fetch order book
    clob_token_ids: list[str] = field(default_factory=list)

    @property
    def mid_yes(self) -> float | None:
        if self.order_book:
            bid = self.order_book.best_yes_bid
            ask = self.order_book.best_yes_ask
            if bid is not None and ask is not None:
                return round((bid + ask) / 2, 4)
        return self.yes_price


@dataclass
class MarketMatch:
    kalshi_market: Market
    poly_market: Market
    similarity: float  # 0.0-1.0

    def __repr__(self) -> str:
        return (
            f"Match(sim={self.similarity:.3f})\n"
            f"  K: {self.kalshi_market.title}\n"
            f"  P: {self.poly_market.title}"
        )


@dataclass
class ArbOpportunity:
    match: MarketMatch
    spread_pct: float       # positive = profitable
    direction: str          # e.g. "BUY YES on Kalshi, BUY NO on Polymarket"
    kalshi_price: float
    poly_price: float
    expected_profit_per_dollar: float

    def summary(self) -> str:
        return (
            f"ARB {self.spread_pct:+.2f}% | {self.direction}\n"
            f"  Kalshi: {self.kalshi_price:.3f} | Poly: {self.poly_price:.3f}\n"
            f"  Profit/$ {self.expected_profit_per_dollar:.4f}\n"
            f"  K: {self.match.kalshi_market.title}\n"
            f"  P: {self.match.poly_market.title}\n"
            f"  Similarity: {self.match.similarity:.3f}"
        )
