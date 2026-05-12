"""Tracks open positions across both paper and live modes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from database.store import DatabaseStore
from utils.log import get_logger
from utils.types import Side, TradeRecord

log = get_logger(__name__)


class PositionTracker:
    """Maps pair positions to trade records; handles open/close lifecycle."""

    def __init__(self, db: DatabaseStore) -> None:
        self.db = db
        self._open: Dict[str, TradeRecord] = {}

    def pair_key(self, leg_a: str, leg_b: str) -> str:
        return f"{leg_a}|{leg_b}"

    def open_trade(
        self,
        leg_a: str,
        leg_b: str,
        side_a: Side,
        side_b: Side,
        qty_a: float,
        qty_b: float,
        price_a: float,
        price_b: float,
        hedge_ratio: float,
        zscore_entry: float,
    ) -> TradeRecord:
        trade_id = str(uuid.uuid4())[:12]
        trade = TradeRecord(
            trade_id=trade_id,
            timestamp_open=datetime.now(tz=timezone.utc),
            timestamp_close=None,
            pair_leg_a=leg_a,
            pair_leg_b=leg_b,
            side_a=side_a,
            side_b=side_b,
            qty_a=qty_a,
            qty_b=qty_b,
            entry_price_a=price_a,
            entry_price_b=price_b,
            hedge_ratio=hedge_ratio,
            zscore_entry=zscore_entry,
        )
        key = self.pair_key(leg_a, leg_b)
        self._open[key] = trade
        self.db.insert_trade(trade)
        log.info("OPENED trade %s  %s  %s/%s", trade_id, key, side_a.value, side_b.value)
        return trade

    def close_trade(
        self,
        leg_a: str,
        leg_b: str,
        exit_price_a: float,
        exit_price_b: float,
        zscore_exit: float,
        exit_reason: str,
        commission: float = 0.0,
    ) -> Optional[TradeRecord]:
        key = self.pair_key(leg_a, leg_b)
        trade = self._open.pop(key, None)
        if trade is None:
            log.warning("No open trade for %s", key)
            return None

        # Compute PnL
        if trade.side_a == Side.LONG:
            pnl_a = (exit_price_a - trade.entry_price_a) * trade.qty_a
        else:
            pnl_a = (trade.entry_price_a - exit_price_a) * trade.qty_a

        if trade.side_b == Side.LONG:
            pnl_b = (exit_price_b - trade.entry_price_b) * trade.qty_b
        else:
            pnl_b = (trade.entry_price_b - exit_price_b) * trade.qty_b

        total_pnl = pnl_a + pnl_b - commission
        now = datetime.now(tz=timezone.utc)

        trade.exit_price_a = exit_price_a
        trade.exit_price_b = exit_price_b
        trade.pnl = total_pnl
        trade.commission = commission
        trade.zscore_exit = zscore_exit
        trade.exit_reason = exit_reason
        trade.timestamp_close = now

        self.db.update_trade_close(
            trade.trade_id, exit_price_a, exit_price_b,
            total_pnl, commission, zscore_exit, exit_reason, now,
        )
        log.info(
            "CLOSED trade %s  PnL=$%.2f  reason=%s",
            trade.trade_id, total_pnl, exit_reason,
        )
        return trade

    def get_open_trades(self) -> Dict[str, TradeRecord]:
        return dict(self._open)

    def is_open(self, leg_a: str, leg_b: str) -> bool:
        return self.pair_key(leg_a, leg_b) in self._open
