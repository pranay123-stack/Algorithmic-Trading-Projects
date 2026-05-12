"""Persistence layer — SQLite (default) or PostgreSQL."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from config import Config
from utils.types import TradeRecord, Signal

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS trades (
    trade_id        TEXT PRIMARY KEY,
    timestamp_open  TEXT NOT NULL,
    timestamp_close TEXT,
    pair_leg_a      TEXT NOT NULL,
    pair_leg_b      TEXT NOT NULL,
    side_a          TEXT NOT NULL,
    side_b          TEXT NOT NULL,
    qty_a           REAL NOT NULL,
    qty_b           REAL NOT NULL,
    entry_price_a   REAL NOT NULL,
    entry_price_b   REAL NOT NULL,
    exit_price_a    REAL,
    exit_price_b    REAL,
    pnl             REAL DEFAULT 0,
    commission      REAL DEFAULT 0,
    hedge_ratio     REAL DEFAULT 1,
    zscore_entry    REAL DEFAULT 0,
    zscore_exit     REAL,
    exit_reason     TEXT DEFAULT '',
    meta            TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    pair_leg_a  TEXT NOT NULL,
    pair_leg_b  TEXT NOT NULL,
    zscore      REAL NOT NULL,
    spread      REAL NOT NULL,
    hedge_ratio REAL NOT NULL,
    side_a      TEXT NOT NULL,
    side_b      TEXT NOT NULL,
    strength    REAL DEFAULT 0,
    meta        TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS market_data (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol    TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open      REAL NOT NULL,
    high      REAL NOT NULL,
    low       REAL NOT NULL,
    close     REAL NOT NULL,
    volume    REAL NOT NULL,
    UNIQUE(symbol, timeframe, timestamp)
);

CREATE TABLE IF NOT EXISTS pnl_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    equity      REAL NOT NULL,
    daily_pnl   REAL NOT NULL,
    open_pairs  INTEGER DEFAULT 0,
    meta        TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS backtest_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    params          TEXT NOT NULL,
    total_trades    INTEGER,
    win_rate        REAL,
    sharpe          REAL,
    profit_factor   REAL,
    max_drawdown    REAL,
    final_equity    REAL,
    meta            TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_trades_open ON trades(timestamp_open);
CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_md_sym_tf ON market_data(symbol, timeframe, timestamp);
"""


class DatabaseStore:
    def __init__(self, cfg: Config | None = None):
        if cfg is None:
            cfg = Config.load()
        db_cfg = cfg.database
        if db_cfg.engine == "sqlite":
            db_path = Path(db_cfg.sqlite_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(_SCHEMA_SQL)
        else:
            try:
                import psycopg2
                self._conn = psycopg2.connect(db_cfg.pg_dsn)
                with self._conn.cursor() as cur:
                    cur.execute(_SCHEMA_SQL.replace("AUTOINCREMENT", ""))
                self._conn.commit()
            except ImportError:
                raise ImportError("psycopg2 required for PostgreSQL support")

    @contextmanager
    def _cursor(self) -> Generator:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cur.close()

    # ── Trades ──────────────────────────────────────────────

    def insert_trade(self, t: TradeRecord) -> None:
        with self._cursor() as cur:
            cur.execute(
                """INSERT OR REPLACE INTO trades
                   (trade_id, timestamp_open, timestamp_close,
                    pair_leg_a, pair_leg_b, side_a, side_b,
                    qty_a, qty_b, entry_price_a, entry_price_b,
                    exit_price_a, exit_price_b, pnl, commission,
                    hedge_ratio, zscore_entry, zscore_exit, exit_reason, meta)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    t.trade_id,
                    t.timestamp_open.isoformat(),
                    t.timestamp_close.isoformat() if t.timestamp_close else None,
                    t.pair_leg_a, t.pair_leg_b,
                    t.side_a.value, t.side_b.value,
                    t.qty_a, t.qty_b,
                    t.entry_price_a, t.entry_price_b,
                    t.exit_price_a, t.exit_price_b,
                    t.pnl, t.commission,
                    t.hedge_ratio, t.zscore_entry, t.zscore_exit,
                    t.exit_reason, json.dumps(t.meta),
                ),
            )

    def update_trade_close(
        self, trade_id: str, exit_price_a: float, exit_price_b: float,
        pnl: float, commission: float, zscore_exit: float, exit_reason: str,
        timestamp_close: datetime,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                """UPDATE trades SET exit_price_a=?, exit_price_b=?,
                   pnl=?, commission=?, zscore_exit=?, exit_reason=?,
                   timestamp_close=? WHERE trade_id=?""",
                (exit_price_a, exit_price_b, pnl, commission,
                 zscore_exit, exit_reason, timestamp_close.isoformat(), trade_id),
            )

    def get_open_trades(self) -> List[Dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM trades WHERE timestamp_close IS NULL")
            return [dict(r) for r in cur.fetchall()]

    def get_all_trades(self, limit: int = 500) -> List[Dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM trades ORDER BY timestamp_open DESC LIMIT ?", (limit,)
            )
            return [dict(r) for r in cur.fetchall()]

    def get_daily_pnl(self, date_str: str) -> float:
        with self._cursor() as cur:
            cur.execute(
                """SELECT COALESCE(SUM(pnl),0) FROM trades
                   WHERE timestamp_close IS NOT NULL
                   AND date(timestamp_close) = ?""",
                (date_str,),
            )
            return cur.fetchone()[0]

    # ── Signals ─────────────────────────────────────────────

    def insert_signal(self, s: Signal) -> None:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO signals
                   (timestamp, pair_leg_a, pair_leg_b, zscore, spread,
                    hedge_ratio, side_a, side_b, strength, meta)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    s.timestamp.isoformat(),
                    s.pair_leg_a, s.pair_leg_b,
                    s.zscore, s.spread, s.hedge_ratio,
                    s.side_a.value, s.side_b.value,
                    s.strength, json.dumps(s.meta),
                ),
            )

    # ── Market Data ─────────────────────────────────────────

    def upsert_candles(self, symbol: str, timeframe: str, candles: List[Dict]) -> None:
        with self._cursor() as cur:
            for c in candles:
                cur.execute(
                    """INSERT OR REPLACE INTO market_data
                       (symbol, timeframe, timestamp, open, high, low, close, volume)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (symbol, timeframe, c["timestamp"], c["open"],
                     c["high"], c["low"], c["close"], c["volume"]),
                )

    def get_candles(
        self, symbol: str, timeframe: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute(
                """SELECT * FROM market_data
                   WHERE symbol=? AND timeframe=?
                   ORDER BY timestamp DESC LIMIT ?""",
                (symbol, timeframe, limit),
            )
            return [dict(r) for r in cur.fetchall()]

    # ── PnL Snapshots ──────────────────────────────────────

    def insert_pnl_snapshot(
        self, equity: float, daily_pnl: float, open_pairs: int
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO pnl_snapshots (timestamp, equity, daily_pnl, open_pairs)
                   VALUES (?,?,?,?)""",
                (datetime.now(tz=timezone.utc).isoformat(), equity, daily_pnl, open_pairs),
            )

    # ── Backtest ───────────────────────────────────────────

    def insert_backtest_result(self, result: Dict[str, Any]) -> None:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO backtest_results
                   (run_id, timestamp, params, total_trades, win_rate,
                    sharpe, profit_factor, max_drawdown, final_equity, meta)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    result["run_id"],
                    datetime.now(tz=timezone.utc).isoformat(),
                    json.dumps(result.get("params", {})),
                    result.get("total_trades", 0),
                    result.get("win_rate", 0),
                    result.get("sharpe", 0),
                    result.get("profit_factor", 0),
                    result.get("max_drawdown", 0),
                    result.get("final_equity", 0),
                    json.dumps(result.get("meta", {})),
                ),
            )

    def close(self) -> None:
        self._conn.close()
