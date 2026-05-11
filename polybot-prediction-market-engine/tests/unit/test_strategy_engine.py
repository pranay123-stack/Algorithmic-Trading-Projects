"""Tests for the strategy rules engine."""

from __future__ import annotations

import time

import pytest

from polybot.config.settings import Condition, ConditionOperator, RuleConfig
from polybot.strategy.engine import StrategyEngine
from polybot.strategy.models import evaluate_condition, evaluate_rule
from polybot.types import Market, PriceSnapshot, TokenPair


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------

class TestEvaluateCondition:
    @pytest.fixture
    def snap(self) -> PriceSnapshot:
        return PriceSnapshot("m1", 0.35, 0.65, 50000.0, 25000.0, time.time())

    def test_lt_true(self, snap: PriceSnapshot) -> None:
        c = Condition(field="yes_price", operator=ConditionOperator.LT, value=0.40)
        assert evaluate_condition(c, snap) is True

    def test_lt_false(self, snap: PriceSnapshot) -> None:
        c = Condition(field="yes_price", operator=ConditionOperator.LT, value=0.30)
        assert evaluate_condition(c, snap) is False

    def test_le_equal(self, snap: PriceSnapshot) -> None:
        c = Condition(field="yes_price", operator=ConditionOperator.LE, value=0.35)
        assert evaluate_condition(c, snap) is True

    def test_gt_true(self, snap: PriceSnapshot) -> None:
        c = Condition(field="volume_24h", operator=ConditionOperator.GT, value=10000)
        assert evaluate_condition(c, snap) is True

    def test_ge_equal(self, snap: PriceSnapshot) -> None:
        c = Condition(field="liquidity", operator=ConditionOperator.GE, value=25000.0)
        assert evaluate_condition(c, snap) is True

    def test_eq(self, snap: PriceSnapshot) -> None:
        c = Condition(field="yes_price", operator=ConditionOperator.EQ, value=0.35)
        assert evaluate_condition(c, snap) is True

    def test_between_true(self, snap: PriceSnapshot) -> None:
        c = Condition(field="yes_price", operator=ConditionOperator.BETWEEN, value=[0.30, 0.40])
        assert evaluate_condition(c, snap) is True

    def test_between_false(self, snap: PriceSnapshot) -> None:
        c = Condition(field="yes_price", operator=ConditionOperator.BETWEEN, value=[0.50, 0.60])
        assert evaluate_condition(c, snap) is False

    def test_unknown_field(self, snap: PriceSnapshot) -> None:
        c = Condition(field="nonexistent", operator=ConditionOperator.LT, value=1.0)
        assert evaluate_condition(c, snap) is False


class TestEvaluateRule:
    def test_all_conditions_pass(self) -> None:
        snap = PriceSnapshot("m1", 0.15, 0.85, 50000.0, 25000.0, time.time())
        rule = RuleConfig(
            name="test",
            conditions=[
                Condition(field="yes_price", operator=ConditionOperator.LT, value=0.20),
                Condition(field="volume_24h", operator=ConditionOperator.GT, value=10000),
            ],
            action="buy_yes",
        )
        assert evaluate_rule(rule, snap) is True

    def test_one_condition_fails(self) -> None:
        snap = PriceSnapshot("m1", 0.25, 0.75, 50000.0, 25000.0, time.time())
        rule = RuleConfig(
            name="test",
            conditions=[
                Condition(field="yes_price", operator=ConditionOperator.LT, value=0.20),
                Condition(field="volume_24h", operator=ConditionOperator.GT, value=10000),
            ],
            action="buy_yes",
        )
        assert evaluate_rule(rule, snap) is False


# ---------------------------------------------------------------------------
# Strategy engine
# ---------------------------------------------------------------------------

class TestStrategyEngine:
    def test_generates_signal_on_match(
        self,
        sample_rules: list[RuleConfig],
        sample_snapshots: dict[str, PriceSnapshot],
        market_map: dict[str, Market],
    ) -> None:
        engine = StrategyEngine(rules=sample_rules, markets=market_map)
        signals = engine.evaluate(sample_snapshots)
        # "cheap_buy" should fire for market-weather (yes_price=0.10 < 0.20)
        cheap_signals = [s for s in signals if s.rule_name == "cheap_buy"]
        assert len(cheap_signals) >= 1

    def test_no_signal_when_no_match(self, market_map: dict[str, Market]) -> None:
        rules = [
            RuleConfig(
                name="impossible",
                conditions=[
                    Condition(field="yes_price", operator=ConditionOperator.LT, value=0.01),
                ],
                action="buy_yes",
                cooldown_seconds=0.0,
            ),
        ]
        snaps = {
            "market-btc": PriceSnapshot("market-btc", 0.50, 0.50, 1000.0, 500.0, time.time()),
        }
        engine = StrategyEngine(rules=rules, markets=market_map)
        signals = engine.evaluate(snaps)
        assert len(signals) == 0

    def test_disabled_rule_skipped(
        self,
        sample_snapshots: dict[str, PriceSnapshot],
        market_map: dict[str, Market],
    ) -> None:
        rules = [
            RuleConfig(
                name="disabled_rule",
                conditions=[
                    Condition(field="yes_price", operator=ConditionOperator.LT, value=0.99),
                ],
                action="buy_yes",
                enabled=False,
                cooldown_seconds=0.0,
            ),
        ]
        engine = StrategyEngine(rules=rules, markets=market_map)
        signals = engine.evaluate(sample_snapshots)
        assert len(signals) == 0

    def test_cooldown_prevents_refiring(self, market_map: dict[str, Market]) -> None:
        rules = [
            RuleConfig(
                name="cool_rule",
                conditions=[
                    Condition(field="yes_price", operator=ConditionOperator.LT, value=0.99),
                ],
                action="buy_yes",
                cooldown_seconds=9999.0,
            ),
        ]
        snaps = {
            "market-btc": PriceSnapshot("market-btc", 0.50, 0.50, 1000.0, 500.0, time.time()),
        }
        engine = StrategyEngine(rules=rules, markets=market_map)

        # First evaluation generates signal
        signals = engine.evaluate(snaps)
        assert len(signals) >= 1

        # Second evaluation should be blocked by cooldown
        signals = engine.evaluate(snaps)
        assert len(signals) == 0

    def test_market_id_filter(self, market_map: dict[str, Market]) -> None:
        rules = [
            RuleConfig(
                name="targeted",
                market_id="market-btc",
                conditions=[
                    Condition(field="yes_price", operator=ConditionOperator.LT, value=0.99),
                ],
                action="buy_yes",
                cooldown_seconds=0.0,
            ),
        ]
        snaps = {
            "market-btc": PriceSnapshot("market-btc", 0.50, 0.50, 1000.0, 500.0, time.time()),
            "market-election": PriceSnapshot("market-election", 0.50, 0.50, 1000.0, 500.0, time.time()),
        }
        engine = StrategyEngine(rules=rules, markets=market_map)
        signals = engine.evaluate(snaps)
        assert len(signals) == 1
        assert signals[0].market_id == "market-btc"

    def test_stats(self, market_map: dict[str, Market]) -> None:
        rules = [
            RuleConfig(
                name="stat_rule",
                conditions=[
                    Condition(field="yes_price", operator=ConditionOperator.LT, value=0.99),
                ],
                action="buy_yes",
                cooldown_seconds=0.0,
            ),
        ]
        snaps = {
            "market-btc": PriceSnapshot("market-btc", 0.50, 0.50, 1000.0, 500.0, time.time()),
        }
        engine = StrategyEngine(rules=rules, markets=market_map)
        engine.evaluate(snaps)
        stats = engine.stats
        assert stats["evaluations"] >= 1
        assert stats["signals"] >= 1
