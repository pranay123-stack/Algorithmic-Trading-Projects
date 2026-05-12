"""Polymarket API client for fetching markets and order books via Gamma + CLOB APIs."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import Config
from .models import Market, OrderBook, OrderBookLevel, Platform

logger = logging.getLogger(__name__)

GAMMA_MARKETS_URL = f"{Config.POLY_GAMMA_URL}/markets"
GAMMA_EVENTS_URL = f"{Config.POLY_GAMMA_URL}/events"
CLOB_BOOK_URL = f"{Config.POLY_CLOB_URL}/book"


def _parse_market(raw: dict[str, Any]) -> Market:
    """Parse a single Polymarket Gamma market into our Market model."""
    # clob_token_ids is a JSON string like '["token0","token1"]' or a list
    token_ids = raw.get("clobTokenIds") or raw.get("clob_token_ids") or []
    if isinstance(token_ids, str):
        import json
        try:
            token_ids = json.loads(token_ids)
        except (json.JSONDecodeError, TypeError):
            token_ids = []

    # Outcomes pricing
    outcomes_prices = raw.get("outcomePrices") or raw.get("outcome_prices") or "[]"
    if isinstance(outcomes_prices, str):
        import json
        try:
            outcomes_prices = json.loads(outcomes_prices)
        except (json.JSONDecodeError, TypeError):
            outcomes_prices = []

    yes_price = float(outcomes_prices[0]) if len(outcomes_prices) > 0 else None
    no_price = float(outcomes_prices[1]) if len(outcomes_prices) > 1 else None

    return Market(
        platform=Platform.POLYMARKET,
        market_id=raw.get("condition_id", raw.get("conditionId", "")),
        title=raw.get("question", raw.get("title", "")),
        category=raw.get("category", raw.get("groupItemTitle", "")),
        status="active" if raw.get("active") or raw.get("accepting_orders") else "closed",
        yes_price=yes_price,
        no_price=no_price,
        volume=float(raw.get("volume", raw.get("volumeNum", 0)) or 0),
        clob_token_ids=token_ids,
    )


async def fetch_markets(
    client: httpx.AsyncClient,
    *,
    active: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> list[Market]:
    """Fetch a page of Polymarket markets from Gamma API."""
    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
        "active": str(active).lower(),
        "closed": "false",
    }

    resp = await client.get(GAMMA_MARKETS_URL, params=params)
    resp.raise_for_status()
    data = resp.json()

    # Gamma returns a list directly
    raw_markets = data if isinstance(data, list) else data.get("data", data.get("markets", []))
    markets = [_parse_market(m) for m in raw_markets]

    logger.info("Polymarket: fetched %d markets (offset=%d)", len(markets), offset)
    return markets


async def fetch_all_markets(
    client: httpx.AsyncClient,
    *,
    active: bool = True,
    max_pages: int = 10,
    page_size: int = 100,
) -> list[Market]:
    """Paginate through Polymarket Gamma markets."""
    all_markets: list[Market] = []

    for page in range(max_pages):
        offset = page * page_size
        markets = await fetch_markets(client, active=active, limit=page_size, offset=offset)
        all_markets.extend(markets)
        if len(markets) < page_size:
            break

    logger.info("Polymarket: total %d markets fetched", len(all_markets))
    return all_markets


async def fetch_orderbook(
    client: httpx.AsyncClient,
    token_id: str,
) -> OrderBook:
    """Fetch order book for a Polymarket token from CLOB API."""
    resp = await client.get(CLOB_BOOK_URL, params={"token_id": token_id})
    resp.raise_for_status()
    data = resp.json()

    yes_bids = []
    yes_asks = []

    for entry in data.get("bids", []):
        price = float(entry.get("price", 0))
        size = float(entry.get("size", 0))
        yes_bids.append(OrderBookLevel(price=price, size=size))

    for entry in data.get("asks", []):
        price = float(entry.get("price", 0))
        size = float(entry.get("size", 0))
        yes_asks.append(OrderBookLevel(price=price, size=size))

    yes_bids.sort(key=lambda x: x.price, reverse=True)
    yes_asks.sort(key=lambda x: x.price)

    return OrderBook(yes_bids=yes_bids, yes_asks=yes_asks)
