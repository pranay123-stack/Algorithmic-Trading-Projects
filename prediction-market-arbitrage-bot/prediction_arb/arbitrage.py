"""Arbitrage detection engine.

Compares prices between matched Kalshi and Polymarket markets
to identify cross-platform arbitrage opportunities.

Arbitrage logic for binary markets:
  - Both platforms sell YES and NO contracts that pay $1 if the outcome occurs.
  - Arb exists when: buy YES on platform A + buy NO on platform B < $1
    i.e., you lock in a guaranteed profit regardless of outcome.
  - Spread = 1 - (best_yes_A + best_no_B) or 1 - (best_no_A + best_yes_B)
    Positive spread = profitable arb.
"""

from __future__ import annotations

import logging

from .config import Config
from .models import ArbOpportunity, MarketMatch

logger = logging.getLogger(__name__)


def _get_prices(match: MarketMatch) -> tuple[
    float | None, float | None, float | None, float | None
]:
    """Extract best YES/NO prices from both sides of a match.

    Returns (kalshi_yes, kalshi_no, poly_yes, poly_no).
    Prefers order book prices; falls back to mid/last prices.
    """
    km = match.kalshi_market
    pm = match.poly_market

    # Kalshi prices
    if km.order_book:
        k_yes = km.order_book.best_yes_ask  # cost to buy YES
        k_no = km.order_book.best_no_ask    # cost to buy NO
    else:
        k_yes = km.yes_price
        k_no = km.no_price or (1.0 - k_yes if k_yes is not None else None)

    # Polymarket prices
    if pm.order_book:
        p_yes = pm.order_book.best_yes_ask  # cost to buy YES
        p_no = pm.order_book.best_no_ask    # cost to buy NO
    else:
        p_yes = pm.yes_price
        p_no = pm.no_price or (1.0 - p_yes if p_yes is not None else None)

    return k_yes, k_no, p_yes, p_no


def detect_arbitrage(
    matches: list[MarketMatch],
    min_spread_pct: float | None = None,
) -> list[ArbOpportunity]:
    """Detect arbitrage opportunities across matched markets.

    For each match, checks two directions:
    1. Buy YES on Kalshi + Buy NO on Polymarket
    2. Buy YES on Polymarket + Buy NO on Kalshi

    Returns opportunities where spread > min_spread_pct.
    """
    min_spread = min_spread_pct if min_spread_pct is not None else Config.MIN_ARB_SPREAD
    opportunities: list[ArbOpportunity] = []

    for match in matches:
        k_yes, k_no, p_yes, p_no = _get_prices(match)

        # Direction 1: Buy YES on Kalshi, Buy NO on Polymarket
        if k_yes is not None and p_no is not None:
            total_cost = k_yes + p_no
            spread = (1.0 - total_cost) * 100  # as percentage
            if spread >= min_spread:
                opportunities.append(ArbOpportunity(
                    match=match,
                    spread_pct=spread,
                    direction="BUY YES on Kalshi + BUY NO on Polymarket",
                    kalshi_price=k_yes,
                    poly_price=p_no,
                    expected_profit_per_dollar=round((1.0 - total_cost) / total_cost, 4) if total_cost > 0 else 0,
                ))

        # Direction 2: Buy YES on Polymarket, Buy NO on Kalshi
        if p_yes is not None and k_no is not None:
            total_cost = p_yes + k_no
            spread = (1.0 - total_cost) * 100
            if spread >= min_spread:
                opportunities.append(ArbOpportunity(
                    match=match,
                    spread_pct=spread,
                    direction="BUY YES on Polymarket + BUY NO on Kalshi",
                    kalshi_price=k_no,
                    poly_price=p_yes,
                    expected_profit_per_dollar=round((1.0 - total_cost) / total_cost, 4) if total_cost > 0 else 0,
                ))

    # Sort by spread descending (most profitable first)
    opportunities.sort(key=lambda o: o.spread_pct, reverse=True)

    logger.info(
        "Found %d arb opportunities (min_spread=%.1f%%)",
        len(opportunities), min_spread,
    )
    return opportunities
