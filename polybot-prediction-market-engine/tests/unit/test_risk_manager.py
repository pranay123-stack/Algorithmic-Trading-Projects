"""Tests for the risk manager."""

from __future__ import annotations

import pytest

from polybot.config.settings import RiskConfig
from polybot.risk.manager import RiskManager
from polybot.types import Position, Signal, SignalAction, Side


@pytest.fixture
def risk(risk_config: RiskConfig) -> RiskManager:
    return RiskManager(risk_config)


def _make_signal(size: float = 10.0, market_id: str = "m1") -> Signal:
    return Signal(
        market_id=market_id,
        action=SignalAction.BUY_YES,
        token_id="yes-1",
        target_price=0.40,
        size_usdc=size,
        rule_name="test",
    )


def _make_position(
    market_id: str = "m1",
    size: float = 50.0,
    current_price: float = 0.50,
    unrealized_pnl: float = 0.0,
) -> Position:
    return Position(
        market_id=market_id,
        token_id="yes-1",
        side=Side.BUY,
        entry_price=0.40,
        size=size,
        current_price=current_price,
        unrealized_pnl=unrealized_pnl,
    )


class TestRiskManager:
    def test_approved_order(self, risk: RiskManager) -> None:
        passed, reason = risk.check_order(_make_signal(), [], 500.0)
        assert passed is True
        assert reason == "approved"

    def test_max_positions(self, risk: RiskManager) -> None:
        positions = [_make_position(market_id=f"m{i}") for i in range(5)]
        passed, reason = risk.check_order(_make_signal(), positions, 500.0)
        assert passed is False
        assert reason == "max_positions_reached"

    def test_exceeds_max_position_size(self, risk: RiskManager) -> None:
        passed, reason = risk.check_order(_make_signal(size=200.0), [], 500.0)
        assert passed is False
        assert reason == "exceeds_max_position_size"

    def test_exceeds_max_exposure(self, risk: RiskManager) -> None:
        # 4 positions * 300 size * 0.50 price = 600 total exposure > 500 limit
        positions = [_make_position(market_id=f"m{i}", size=300.0, current_price=0.50) for i in range(4)]
        passed, reason = risk.check_order(_make_signal(size=50.0), positions, 500.0)
        assert passed is False
        assert reason == "exceeds_max_total_exposure"

    def test_max_loss_per_market(self, risk: RiskManager) -> None:
        positions = [_make_position(unrealized_pnl=-55.0)]
        passed, reason = risk.check_order(_make_signal(), positions, 500.0)
        assert passed is False
        assert reason == "max_loss_per_market_reached"

    def test_daily_loss_limit(self, risk: RiskManager) -> None:
        risk.update_daily_pnl(-101.0)
        passed, reason = risk.check_order(_make_signal(), [], 500.0)
        assert passed is False
        assert "daily_loss_limit" in reason

    def test_insufficient_balance(self, risk: RiskManager) -> None:
        signal = _make_signal(size=100.0)
        # price * size = 0.40 * 100 = 40, balance = 10
        passed, reason = risk.check_order(signal, [], 10.0)
        assert passed is False
        assert reason == "insufficient_balance"

    def test_reset_daily(self, risk: RiskManager) -> None:
        risk.update_daily_pnl(-101.0)
        assert risk.is_halted is True
        risk.reset_daily()
        assert risk.is_halted is False
        assert risk.daily_pnl == 0.0

    def test_stats(self, risk: RiskManager) -> None:
        stats = risk.stats
        assert "daily_pnl" in stats
        assert "halted" in stats
