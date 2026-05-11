"""Integration test: full poll -> evaluate -> risk -> execute cycle."""

from __future__ import annotations

import time

import pytest

from polybot.config.settings import (
    Condition,
    ConditionOperator,
    RiskConfig,
    RuleConfig,
)
from polybot.execution.paper import PaperExecutor
from polybot.risk.manager import RiskManager
from polybot.strategy.engine import StrategyEngine
from polybot.strategy.models import signal_to_order
from polybot.types import Market, PriceSnapshot, TokenPair


@pytest.mark.asyncio
async def test_full_trading_cycle() -> None:
    """Simulate one complete cycle: snapshot -> signal -> risk -> order -> fill."""
    # Setup market
    market = Market(
        id="test-market",
        question="Test market?",
        condition_id="cond-test",
        tokens=TokenPair("cond-test", "yes-test", "no-test"),
        end_date="2026-12-31",
    )
    market_map = {market.id: market}

    # Setup rule: buy if yes_price < 0.30
    rules = [
        RuleConfig(
            name="test_buy",
            conditions=[
                Condition(field="yes_price", operator=ConditionOperator.LT, value=0.30),
            ],
            action="buy_yes",
            size_usdc=50.0,
            cooldown_seconds=0.0,
        ),
    ]

    # Setup components
    engine = StrategyEngine(rules=rules, markets=market_map)
    risk = RiskManager(RiskConfig())
    executor = PaperExecutor(initial_balance=1000.0)

    # Cycle 1: price = 0.20 -> should trigger buy
    snapshots = {
        "test-market": PriceSnapshot("test-market", 0.20, 0.80, 50000.0, 25000.0, time.time()),
    }

    signals = engine.evaluate(snapshots)
    assert len(signals) == 1
    assert signals[0].rule_name == "test_buy"

    # Risk check
    positions = await executor.get_positions()
    balance = await executor.get_balance()
    passed, reason = risk.check_order(signals[0], positions, balance)
    assert passed is True

    # Place order
    order = signal_to_order(signals[0])
    order = await executor.place_order(order)
    assert order.status.name == "OPEN"

    # Process fills (price is below limit, should fill)
    fills = executor.process_snapshots(snapshots)
    assert len(fills) == 1

    # Verify position created
    positions = await executor.get_positions()
    assert len(positions) == 1

    # Verify balance decreased
    balance = await executor.get_balance()
    assert balance < 1000.0

    # Cycle 2: price = 0.50 -> no new signal (0.50 > 0.30)
    snapshots_2 = {
        "test-market": PriceSnapshot("test-market", 0.50, 0.50, 50000.0, 25000.0, time.time()),
    }
    signals_2 = engine.evaluate(snapshots_2)
    assert len(signals_2) == 0

    # Position should have unrealized profit
    executor.process_snapshots(snapshots_2)
    positions = await executor.get_positions()
    assert len(positions) == 1
    assert positions[0].unrealized_pnl > 0  # price went up from 0.20 to 0.50
