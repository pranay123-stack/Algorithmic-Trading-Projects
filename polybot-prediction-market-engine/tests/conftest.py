"""Shared test fixtures for Polybot."""

from __future__ import annotations

import time

import pytest

from polybot.config.settings import (
    Condition,
    ConditionOperator,
    PolybotConfig,
    RiskConfig,
    RuleConfig,
)
from polybot.types import Market, MarketStatus, PriceSnapshot, TokenPair


@pytest.fixture
def config() -> PolybotConfig:
    """Default config with factory defaults."""
    return PolybotConfig()


@pytest.fixture
def sample_markets() -> list[Market]:
    """Three realistic prediction markets."""
    return [
        Market(
            id="market-btc",
            question="Will BTC exceed $100k by end of 2026?",
            condition_id="cond-btc",
            tokens=TokenPair("cond-btc", "yes-btc", "no-btc"),
            end_date="2026-12-31",
            tags=["crypto"],
        ),
        Market(
            id="market-election",
            question="Will candidate X win the election?",
            condition_id="cond-elec",
            tokens=TokenPair("cond-elec", "yes-elec", "no-elec"),
            end_date="2026-11-05",
            tags=["politics"],
        ),
        Market(
            id="market-weather",
            question="Will it rain in NYC tomorrow?",
            condition_id="cond-weather",
            tokens=TokenPair("cond-weather", "yes-weather", "no-weather"),
            end_date="2026-05-12",
            tags=["weather"],
        ),
    ]


@pytest.fixture
def market_map(sample_markets: list[Market]) -> dict[str, Market]:
    return {m.id: m for m in sample_markets}


@pytest.fixture
def sample_snapshots() -> dict[str, PriceSnapshot]:
    """Price snapshots for the three sample markets."""
    ts = time.time()
    return {
        "market-btc": PriceSnapshot("market-btc", 0.35, 0.65, 50000.0, 25000.0, ts),
        "market-election": PriceSnapshot("market-election", 0.72, 0.28, 120000.0, 80000.0, ts),
        "market-weather": PriceSnapshot("market-weather", 0.10, 0.90, 2000.0, 500.0, ts),
    }


@pytest.fixture
def sample_rules() -> list[RuleConfig]:
    """Three sample trading rules."""
    return [
        RuleConfig(
            name="cheap_buy",
            conditions=[
                Condition(field="yes_price", operator=ConditionOperator.LT, value=0.20),
            ],
            action="buy_yes",
            size_usdc=10.0,
            cooldown_seconds=0.0,
        ),
        RuleConfig(
            name="high_volume_buy",
            conditions=[
                Condition(field="yes_price", operator=ConditionOperator.LT, value=0.40),
                Condition(field="volume_24h", operator=ConditionOperator.GT, value=10000),
            ],
            action="buy_yes",
            size_usdc=25.0,
            cooldown_seconds=0.0,
        ),
        RuleConfig(
            name="expensive_sell",
            conditions=[
                Condition(field="yes_price", operator=ConditionOperator.GT, value=0.85),
            ],
            action="sell_yes",
            size_usdc=15.0,
            cooldown_seconds=0.0,
        ),
    ]


@pytest.fixture
def risk_config() -> RiskConfig:
    return RiskConfig(
        max_position_size_usdc=100.0,
        max_total_exposure_usdc=500.0,
        max_positions=5,
        max_loss_per_market_usdc=50.0,
        daily_loss_limit_usdc=100.0,
    )
