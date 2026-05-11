"""Pydantic configuration models for Polybot.

All user-facing configuration is validated here. Secrets (private keys,
bot tokens) should be supplied via environment variables, not YAML.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExecutionMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class ConditionOperator(str, Enum):
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    EQ = "eq"
    BETWEEN = "between"


# ---------------------------------------------------------------------------
# Config sections
# ---------------------------------------------------------------------------

class PollingConfig(BaseModel):
    interval_seconds: float = Field(default=5.0, ge=1.0, le=60.0)
    markets_endpoint: str = Field(default="https://clob.polymarket.com")
    timeout_seconds: float = Field(default=10.0, ge=1.0)
    max_retries: int = Field(default=3, ge=0)


class MarketFilter(BaseModel):
    """Filters to select which markets to monitor."""

    tags: list[str] = Field(default_factory=list)
    min_volume_24h: float = Field(default=0.0, ge=0.0)
    min_liquidity: float = Field(default=0.0, ge=0.0)
    market_ids: list[str] = Field(default_factory=list)


class Condition(BaseModel):
    """A single condition in a trading rule."""

    field: str = Field(description="Snapshot attribute: yes_price, no_price, volume_24h, liquidity")
    operator: ConditionOperator
    value: float | list[float] = Field(description="Threshold, or [low, high] for 'between'")

    @model_validator(mode="after")
    def _validate_between(self) -> "Condition":
        if self.operator == ConditionOperator.BETWEEN:
            if not isinstance(self.value, list) or len(self.value) != 2:
                raise ValueError("'between' operator requires a [low, high] list")
        return self


class RuleConfig(BaseModel):
    """A declarative trading rule: conditions + action."""

    name: str
    market_id: str | None = Field(default=None, description="Target a specific market, or None for all")
    conditions: list[Condition] = Field(min_length=1)
    action: str = Field(description="buy_yes | buy_no | sell_yes | sell_no")
    size_usdc: float = Field(default=10.0, gt=0.0)
    max_price: float = Field(default=0.95, gt=0.0, le=0.99)
    min_price: float = Field(default=0.01, ge=0.01, lt=1.0)
    cooldown_seconds: float = Field(default=300.0, ge=0.0)
    enabled: bool = Field(default=True)


class RiskConfig(BaseModel):
    max_position_size_usdc: float = Field(default=100.0, gt=0.0)
    max_total_exposure_usdc: float = Field(default=500.0, gt=0.0)
    max_positions: int = Field(default=10, ge=1)
    max_loss_per_market_usdc: float = Field(default=50.0, gt=0.0)
    daily_loss_limit_usdc: float = Field(default=100.0, gt=0.0)


class ExecutionConfig(BaseModel):
    mode: ExecutionMode = Field(default=ExecutionMode.PAPER)
    initial_balance_usdc: float = Field(default=1000.0, gt=0.0)
    taker_fee_bps: float = Field(default=0.0, ge=0.0)
    polygon_rpc_url: str = Field(default="https://polygon-rpc.com")
    chain_id: int = Field(default=137, description="Polygon mainnet=137, Mumbai=80001")


class TelegramConfig(BaseModel):
    enabled: bool = Field(default=False)
    bot_token: str = Field(default="")
    chat_id: str = Field(default="")
    notify_on: list[str] = Field(
        default=["signal", "order_placed", "order_filled", "error", "risk_breach"],
    )


class TelemetryConfig(BaseModel):
    prometheus_port: int = Field(default=9090, ge=1, le=65535)
    log_level: str = Field(default="INFO")
    audit_db_url: str = Field(default="sqlite:///audit.db")


# ---------------------------------------------------------------------------
# Top-level config
# ---------------------------------------------------------------------------

class PolybotConfig(BaseModel):
    """Root configuration for Polybot."""

    polling: PollingConfig = Field(default_factory=PollingConfig)
    market_filter: MarketFilter = Field(default_factory=MarketFilter)
    rules: list[RuleConfig] = Field(default_factory=list)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
