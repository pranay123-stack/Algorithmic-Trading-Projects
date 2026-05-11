"""Rules engine that evaluates user-configured conditions against market data.

Manages per-(rule, market) cooldowns to prevent signal spam.
"""

from __future__ import annotations

import time

from polybot.config.settings import RuleConfig
from polybot.strategy.models import action_to_signal, evaluate_rule
from polybot.telemetry import get_logger
from polybot.types import Market, PriceSnapshot, Signal

logger = get_logger(__name__)


class StrategyEngine:
    """Evaluates declarative YAML rules against current market snapshots."""

    def __init__(
        self,
        rules: list[RuleConfig],
        markets: dict[str, Market],
    ) -> None:
        self._rules = rules
        self._markets = markets
        self._last_triggered: dict[tuple[str, str], float] = {}
        self._eval_count = 0
        self._signal_count = 0

    def evaluate(
        self,
        snapshots: dict[str, PriceSnapshot],
    ) -> list[Signal]:
        """Run all enabled rules against the current snapshots.

        Returns a list of :class:`Signal` objects for rules whose
        conditions are met and whose cooldown has expired.
        """
        signals: list[Signal] = []
        now = time.time()

        for rule in self._rules:
            if not rule.enabled:
                continue

            # Determine which markets this rule applies to
            if rule.market_id:
                target_ids = [rule.market_id] if rule.market_id in snapshots else []
            else:
                target_ids = list(snapshots.keys())

            for market_id in target_ids:
                self._eval_count += 1
                snapshot = snapshots[market_id]
                market = self._markets.get(market_id)
                if market is None:
                    continue

                if self._in_cooldown(rule.name, market_id, now):
                    continue

                if evaluate_rule(rule, snapshot):
                    signal = action_to_signal(rule, market, snapshot)
                    signals.append(signal)
                    self._record_trigger(rule.name, market_id, now)
                    self._signal_count += 1
                    logger.info(
                        "signal_generated",
                        rule=rule.name,
                        market=market_id,
                        action=signal.action.name,
                        price=signal.target_price,
                    )

        return signals

    def _in_cooldown(self, rule_name: str, market_id: str, now: float) -> bool:
        key = (rule_name, market_id)
        last = self._last_triggered.get(key)
        if last is None:
            return False
        rule = next((r for r in self._rules if r.name == rule_name), None)
        if rule is None:
            return False
        return (now - last) < rule.cooldown_seconds

    def _record_trigger(self, rule_name: str, market_id: str, now: float) -> None:
        self._last_triggered[(rule_name, market_id)] = now

    @property
    def stats(self) -> dict[str, int]:
        return {
            "evaluations": self._eval_count,
            "signals": self._signal_count,
        }
