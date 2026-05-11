"""Pure functions for evaluating trading conditions against market snapshots.

No side effects — suitable for exhaustive unit testing.
"""

from __future__ import annotations

import time

from polybot.config.settings import Condition, ConditionOperator, RuleConfig
from polybot.types import Market, Order, PriceSnapshot, Signal, SignalAction, Side

_FIELD_MAP = {
    "yes_price": "yes_price",
    "no_price": "no_price",
    "volume_24h": "volume_24h",
    "liquidity": "liquidity",
}

_ACTION_MAP = {
    "buy_yes": SignalAction.BUY_YES,
    "buy_no": SignalAction.BUY_NO,
    "sell_yes": SignalAction.SELL_YES,
    "sell_no": SignalAction.SELL_NO,
}


def evaluate_condition(condition: Condition, snapshot: PriceSnapshot) -> bool:
    """Evaluate a single condition against a price snapshot."""
    attr = _FIELD_MAP.get(condition.field)
    if attr is None:
        return False

    actual = getattr(snapshot, attr)
    op = condition.operator
    val = condition.value

    if op == ConditionOperator.LT:
        return actual < val  # type: ignore[operator]
    if op == ConditionOperator.LE:
        return actual <= val  # type: ignore[operator]
    if op == ConditionOperator.GT:
        return actual > val  # type: ignore[operator]
    if op == ConditionOperator.GE:
        return actual >= val  # type: ignore[operator]
    if op == ConditionOperator.EQ:
        return actual == val
    if op == ConditionOperator.BETWEEN:
        assert isinstance(val, list) and len(val) == 2
        return val[0] <= actual <= val[1]

    return False


def evaluate_rule(rule: RuleConfig, snapshot: PriceSnapshot) -> bool:
    """Evaluate all conditions in a rule (AND logic)."""
    return all(evaluate_condition(c, snapshot) for c in rule.conditions)


def action_to_signal(
    rule: RuleConfig,
    market: Market,
    snapshot: PriceSnapshot,
) -> Signal:
    """Convert a triggered rule into a concrete Signal."""
    action = _ACTION_MAP[rule.action]

    if action in (SignalAction.BUY_YES, SignalAction.SELL_YES):
        token_id = market.tokens.yes_token_id
        target_price = snapshot.yes_price
    else:
        token_id = market.tokens.no_token_id
        target_price = snapshot.no_price

    # Clamp target price to rule bounds
    target_price = max(rule.min_price, min(rule.max_price, target_price))

    return Signal(
        market_id=market.id,
        action=action,
        token_id=token_id,
        target_price=target_price,
        size_usdc=rule.size_usdc,
        rule_name=rule.name,
        timestamp=time.time(),
    )


def signal_to_order(signal: Signal) -> Order:
    """Convert a Signal into an Order ready for execution."""
    if signal.action in (SignalAction.BUY_YES, SignalAction.BUY_NO):
        side = Side.BUY
    else:
        side = Side.SELL

    return Order(
        client_order_id=Order.new_id(),
        market_id=signal.market_id,
        token_id=signal.token_id,
        side=side,
        price=signal.target_price,
        size=signal.size_usdc,
    )
