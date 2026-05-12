"""Kalshi API client for fetching markets and order books."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import Config
from .models import Market, OrderBook, OrderBookLevel, Platform

logger = logging.getLogger(__name__)

# Kalshi public endpoints - no auth required for market data
MARKETS_URL = f"{Config.KALSHI_BASE_URL}/markets"


def _parse_market(raw: dict[str, Any]) -> Market:
    """Parse a single Kalshi market response into our Market model."""
    ticker = raw.get("ticker", "")

    # Kalshi may return prices in cents (int) or dollars (float)
    yes_price = raw.get("yes_price_dollars") or raw.get("yes_price")
    no_price = raw.get("no_price_dollars") or raw.get("no_price")

    # Normalize cents to probability (0-1)
    if isinstance(yes_price, (int, float)) and yes_price > 1:
        yes_price = yes_price / 100.0
    if isinstance(no_price, (int, float)) and no_price > 1:
        no_price = no_price / 100.0

    return Market(
        platform=Platform.KALSHI,
        market_id=ticker,
        title=raw.get("title", raw.get("subtitle", "")),
        category=raw.get("category", raw.get("series_ticker", "")),
        status=raw.get("status", ""),
        yes_price=yes_price,
        no_price=no_price,
        volume=float(raw.get("volume", 0)),
    )


async def fetch_markets(
    client: httpx.AsyncClient,
    *,
    status: str = "open",
    limit: int = 200,
    cursor: str | None = None,
) -> tuple[list[Market], str | None]:
    """Fetch a page of Kalshi markets.

    Returns (markets, next_cursor).
    """
    params: dict[str, Any] = {"status": status, "limit": limit}
    if cursor:
        params["cursor"] = cursor

    resp = await client.get(MARKETS_URL, params=params)
    resp.raise_for_status()
    data = resp.json()

    markets = [_parse_market(m) for m in data.get("markets", [])]
    next_cursor = data.get("cursor")
    # Kalshi returns empty string cursor when no more pages
    if not next_cursor:
        next_cursor = None

    logger.info("Kalshi: fetched %d markets (cursor=%s)", len(markets), next_cursor)
    return markets, next_cursor


async def fetch_all_markets(
    client: httpx.AsyncClient,
    *,
    status: str = "open",
    max_pages: int = 10,
) -> list[Market]:
    """Paginate through all open Kalshi markets."""
    all_markets: list[Market] = []
    cursor = None

    for _ in range(max_pages):
        markets, cursor = await fetch_markets(client, status=status, cursor=cursor)
        all_markets.extend(markets)
        if cursor is None:
            break

    logger.info("Kalshi: total %d markets fetched", len(all_markets))
    return all_markets


async def fetch_orderbook(
    client: httpx.AsyncClient,
    ticker: str,
) -> OrderBook:
    """Fetch order book for a specific Kalshi market ticker."""
    url = f"{MARKETS_URL}/{ticker}/orderbook"
    resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json().get("orderbook", resp.json())

    yes_bids = []
    yes_asks = []

    # Kalshi returns yes bids and no bids
    # yes_bids: people wanting to buy YES
    # no_bids: people wanting to buy NO = effectively selling YES
    for entry in data.get("yes", []):
        price = entry[0] if isinstance(entry, list) else entry.get("price", 0)
        size = entry[1] if isinstance(entry, list) else entry.get("quantity", 0)
        # Normalize cents to probability
        if price > 1:
            price = price / 100.0
        yes_bids.append(OrderBookLevel(price=price, size=float(size)))

    for entry in data.get("no", []):
        price = entry[0] if isinstance(entry, list) else entry.get("price", 0)
        size = entry[1] if isinstance(entry, list) else entry.get("quantity", 0)
        if price > 1:
            price = price / 100.0
        # No bid at price P = Yes ask at price (1-P)
        yes_asks.append(OrderBookLevel(price=round(1.0 - price, 4), size=float(size)))

    # Sort: bids descending, asks ascending
    yes_bids.sort(key=lambda x: x.price, reverse=True)
    yes_asks.sort(key=lambda x: x.price)

    return OrderBook(yes_bids=yes_bids, yes_asks=yes_asks)
