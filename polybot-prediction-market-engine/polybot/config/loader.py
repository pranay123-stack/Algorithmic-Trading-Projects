"""YAML configuration loader with environment-variable overrides.

Environment variables with the prefix ``POLYBOT_`` are merged into the
config tree.  Double underscores denote nesting::

    POLYBOT_RISK__MAX_POSITIONS=5  ->  risk.max_positions = 5
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from polybot.config.settings import PolybotConfig

_ENV_PREFIX = "POLYBOT_"


def load_config(path: str | Path) -> PolybotConfig:
    """Load YAML config, overlay env overrides, and validate via Pydantic."""
    raw: dict[str, Any] = {}
    config_path = Path(path)
    if config_path.exists():
        with open(config_path) as fh:
            raw = yaml.safe_load(fh) or {}

    overrides = _collect_env_overrides()
    if overrides:
        _deep_merge(raw, overrides)

    return PolybotConfig(**raw)


def _collect_env_overrides() -> dict[str, Any]:
    """Collect POLYBOT_ prefixed env vars into a nested dict."""
    result: dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(_ENV_PREFIX):
            continue
        parts = key[len(_ENV_PREFIX) :].lower().split("__")
        _set_nested(result, parts, _coerce_value(value))
    return result


def _set_nested(d: dict[str, Any], keys: list[str], value: Any) -> None:
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def _coerce_value(raw: str) -> Any:
    """Best-effort coerce string env var to Python primitive."""
    if raw.lower() in ("true", "yes"):
        return True
    if raw.lower() in ("false", "no"):
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Recursively merge *override* into *base* in place."""
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
