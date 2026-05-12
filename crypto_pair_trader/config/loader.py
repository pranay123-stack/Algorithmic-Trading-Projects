"""Centralised, immutable configuration loader."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


def _deep_merge(base: dict, override: dict) -> dict:
    merged = base.copy()
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


@dataclass(frozen=True)
class ExchangeCfg:
    name: str = "binance"
    testnet: bool = True
    api_key: str = ""
    api_secret: str = ""
    passphrase: str = ""
    rate_limit: bool = True
    timeout: int = 30000


@dataclass(frozen=True)
class DataCfg:
    timeframe: str = "5m"
    history_days: int = 7
    candle_limit: int = 1000
    cache_dir: str = "data/cache"
    use_websocket: bool = True


@dataclass(frozen=True)
class PairSelectionCfg:
    universe: List[str] = field(default_factory=list)
    min_correlation: float = 0.75
    max_correlation: float = 0.995
    cointegration_pvalue: float = 0.05
    adf_pvalue: float = 0.05
    min_half_life: int = 5
    max_half_life: int = 200
    hedge_ratio_window: int = 120
    min_daily_volume_usd: float = 5_000_000
    min_avg_spread_ticks: float = 0
    rescore_interval_minutes: int = 60
    max_pairs: int = 5


@dataclass(frozen=True)
class StrategyCfg:
    zscore_entry: float = 2.0
    zscore_exit: float = 0.5
    zscore_stop: float = 4.0
    lookback: int = 60
    min_half_life: int = 5
    max_holding_minutes: int = 240
    spread_widening_mult: float = 2.0
    vol_filter_window: int = 30
    vol_filter_max_ratio: float = 3.0
    trend_filter_window: int = 60
    trend_filter_adx_thresh: float = 35.0


@dataclass(frozen=True)
class RiskCfg:
    max_position_usd: float = 10000
    max_pair_exposure_pct: float = 0.20
    max_portfolio_exposure_pct: float = 0.60
    max_daily_loss_usd: float = 500
    max_daily_loss_pct: float = 0.05
    max_open_pairs: int = 3
    dollar_neutral_tolerance: float = 0.05
    session_end_utc: str = "23:45"
    capital: float = 50000


@dataclass(frozen=True)
class ExecutionCfg:
    order_type: str = "limit"
    limit_chase_ticks: int = 2
    max_retries: int = 3
    retry_delay_s: float = 1.0
    partial_fill_timeout_s: float = 10.0
    slippage_bps: float = 5.0


@dataclass(frozen=True)
class BacktestCfg:
    start_date: str = "2024-06-01"
    end_date: str = "2024-08-01"
    initial_capital: float = 50000
    commission_bps: float = 4.0
    slippage_bps: float = 3.0


@dataclass(frozen=True)
class DashboardCfg:
    host: str = "0.0.0.0"
    port: int = 8501
    refresh_seconds: int = 5


@dataclass(frozen=True)
class DatabaseCfg:
    engine: str = "sqlite"
    sqlite_path: str = "data/trades.db"
    pg_dsn: str = ""


@dataclass(frozen=True)
class LoggingCfg:
    level: str = "INFO"
    file: str = "logs/pair_trader.log"
    max_bytes: int = 10_485_760
    backup_count: int = 5


class Config:
    """Singleton-ish config — load once, pass everywhere."""

    _instance: Config | None = None

    def __init__(self, raw: Dict[str, Any]) -> None:
        self.mode: str = raw.get("mode", "paper")
        self.exchange = ExchangeCfg(**raw.get("exchange", {}))
        self.data = DataCfg(**raw.get("data", {}))
        self.pair_selection = PairSelectionCfg(**raw.get("pair_selection", {}))
        self.strategy = StrategyCfg(**raw.get("strategy", {}))
        self.risk = RiskCfg(**raw.get("risk", {}))
        self.execution = ExecutionCfg(**raw.get("execution", {}))
        self.backtest = BacktestCfg(**raw.get("backtest", {}))
        self.dashboard = DashboardCfg(**raw.get("dashboard", {}))
        self.database = DatabaseCfg(**raw.get("database", {}))
        self.logging = LoggingCfg(**raw.get("logging", {}))

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        if cls._instance is not None:
            return cls._instance

        if path is None:
            path = os.environ.get(
                "PAIR_TRADER_CONFIG",
                Path(__file__).resolve().parent / "settings.yaml",
            )
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")

        with open(path) as f:
            raw = yaml.safe_load(f) or {}

        # Allow env-var overrides for secrets
        exc = raw.setdefault("exchange", {})
        exc["api_key"] = os.environ.get("EXCHANGE_API_KEY", exc.get("api_key", ""))
        exc["api_secret"] = os.environ.get("EXCHANGE_API_SECRET", exc.get("api_secret", ""))
        exc["passphrase"] = os.environ.get("EXCHANGE_PASSPHRASE", exc.get("passphrase", ""))

        # Optional local override file
        local_path = path.parent / "settings.local.yaml"
        if local_path.exists():
            with open(local_path) as f:
                local_raw = yaml.safe_load(f) or {}
            raw = _deep_merge(raw, local_raw)

        cls._instance = cls(raw)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
