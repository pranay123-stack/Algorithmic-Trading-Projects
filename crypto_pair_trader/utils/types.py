"""Shared domain types used across the system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Signal:
    timestamp: datetime
    pair_leg_a: str
    pair_leg_b: str
    zscore: float
    spread: float
    hedge_ratio: float
    side_a: Side          # side for leg A
    side_b: Side          # side for leg B
    strength: float = 0.0 # abs(zscore) normalised
    meta: dict = field(default_factory=dict)


@dataclass
class TradeRecord:
    trade_id: str
    timestamp_open: datetime
    timestamp_close: Optional[datetime]
    pair_leg_a: str
    pair_leg_b: str
    side_a: Side
    side_b: Side
    qty_a: float
    qty_b: float
    entry_price_a: float
    entry_price_b: float
    exit_price_a: Optional[float] = None
    exit_price_b: Optional[float] = None
    pnl: float = 0.0
    commission: float = 0.0
    hedge_ratio: float = 1.0
    zscore_entry: float = 0.0
    zscore_exit: Optional[float] = None
    exit_reason: str = ""
    meta: dict = field(default_factory=dict)


@dataclass
class PairScore:
    leg_a: str
    leg_b: str
    correlation: float
    cointegration_pvalue: float
    adf_pvalue: float
    half_life: float
    hedge_ratio: float
    avg_daily_volume_a: float
    avg_daily_volume_b: float
    composite_score: float = 0.0
