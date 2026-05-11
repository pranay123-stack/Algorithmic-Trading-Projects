"""Append-only audit log with dual persistence: SQLite + JSONL sidecar.

Every significant event (signal, order, fill, risk breach) is recorded
for post-hoc analysis and compliance.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import aiosqlite

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS audit_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   REAL    NOT NULL,
    event_type  TEXT    NOT NULL,
    payload     TEXT    NOT NULL,
    trace_id    TEXT    DEFAULT ''
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events (event_type);
"""

_INSERT = """
INSERT INTO audit_events (timestamp, event_type, payload, trace_id)
VALUES (?, ?, ?, ?);
"""


class AuditLog:
    """Async audit logger backed by SQLite and a JSONL sidecar file."""

    def __init__(self, db_url: str = "sqlite:///audit.db") -> None:
        # Strip sqlite:/// prefix to get the file path
        db_path = db_url.replace("sqlite:///", "")
        self._db_path = db_path
        self._jsonl_path = Path(db_path).with_suffix(".jsonl")
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.execute(_CREATE_TABLE)
        await self._db.execute(_CREATE_INDEX)
        await self._db.commit()

    async def log_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        trace_id: str = "",
    ) -> None:
        ts = time.time()
        payload_json = json.dumps(payload, default=str)

        if self._db is not None:
            await self._db.execute(_INSERT, (ts, event_type, payload_json, trace_id))
            await self._db.commit()

        record = {
            "timestamp": ts,
            "event_type": event_type,
            "payload": payload,
            "trace_id": trace_id,
        }
        with open(self._jsonl_path, "a") as fh:
            fh.write(json.dumps(record, default=str) + "\n")

    async def query_events(
        self,
        event_type: str | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if self._db is None:
            return []

        query = "SELECT timestamp, event_type, payload, trace_id FROM audit_events"
        conditions: list[str] = []
        params: list[Any] = []

        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = await self._db.execute(query, params)
        rows = await cursor.fetchall()
        return [
            {
                "timestamp": row[0],
                "event_type": row[1],
                "payload": json.loads(row[2]),
                "trace_id": row[3],
            }
            for row in rows
        ]

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None
