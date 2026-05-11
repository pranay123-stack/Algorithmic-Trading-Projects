"""Tests for configuration loading and validation."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from polybot.config.loader import load_config
from polybot.config.settings import (
    Condition,
    ConditionOperator,
    PolybotConfig,
    RuleConfig,
)


class TestConfigLoader:
    def test_load_default_config(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("{}")
        config = load_config(cfg_file)
        assert isinstance(config, PolybotConfig)
        assert config.polling.interval_seconds == 5.0

    def test_load_yaml_values(self, tmp_path: Path) -> None:
        data = {"polling": {"interval_seconds": 10.0}, "risk": {"max_positions": 3}}
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump(data))
        config = load_config(cfg_file)
        assert config.polling.interval_seconds == 10.0
        assert config.risk.max_positions == 3

    def test_env_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("{}")
        monkeypatch.setenv("POLYBOT_RISK__MAX_POSITIONS", "7")
        config = load_config(cfg_file)
        assert config.risk.max_positions == 7

    def test_missing_file_uses_defaults(self, tmp_path: Path) -> None:
        config = load_config(tmp_path / "nonexistent.yaml")
        assert isinstance(config, PolybotConfig)

    def test_rules_loaded_from_yaml(self, tmp_path: Path) -> None:
        data = {
            "rules": [
                {
                    "name": "test_rule",
                    "conditions": [{"field": "yes_price", "operator": "lt", "value": 0.5}],
                    "action": "buy_yes",
                }
            ]
        }
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump(data))
        config = load_config(cfg_file)
        assert len(config.rules) == 1
        assert config.rules[0].name == "test_rule"


class TestConditionValidation:
    def test_between_requires_list(self) -> None:
        with pytest.raises(ValueError, match="between"):
            Condition(field="yes_price", operator=ConditionOperator.BETWEEN, value=0.5)

    def test_between_requires_two_elements(self) -> None:
        with pytest.raises(ValueError, match="between"):
            Condition(field="yes_price", operator=ConditionOperator.BETWEEN, value=[0.1])

    def test_between_valid(self) -> None:
        c = Condition(field="yes_price", operator=ConditionOperator.BETWEEN, value=[0.1, 0.5])
        assert c.value == [0.1, 0.5]

    def test_simple_operators(self) -> None:
        for op in ["lt", "le", "gt", "ge", "eq"]:
            c = Condition(field="yes_price", operator=ConditionOperator(op), value=0.5)
            assert c.operator.value == op


class TestRuleValidation:
    def test_rule_requires_conditions(self) -> None:
        with pytest.raises(Exception):
            RuleConfig(name="bad", conditions=[], action="buy_yes")

    def test_rule_defaults(self) -> None:
        r = RuleConfig(
            name="test",
            conditions=[Condition(field="yes_price", operator=ConditionOperator.LT, value=0.5)],
            action="buy_yes",
        )
        assert r.enabled is True
        assert r.cooldown_seconds == 300.0
        assert r.size_usdc == 10.0
