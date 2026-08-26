from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Iterable

from sage.protocol.types import Operation, OperationKind, VectorClock


class OperationLog:
    """
    Durable local operation log.

    One SQLite database per node is intentional:
    nodes append locally and later exchange operations.

    Vector clocks remain in the operation payload so conflict resolution is
    independent of transport.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            self.path,
            check_same_thread=False,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operations (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                target TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                timestamp_ms INTEGER NOT NULL,
                node_id TEXT NOT NULL,
                vector_clock_json TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_operations_target "
            "ON operations(target)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_operations_timestamp "
            "ON operations(timestamp_ms)"
        )
        self._conn.commit()

    def append(self, operation: Operation) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO operations
                (id, kind, target, payload_json, timestamp_ms,
                 node_id, vector_clock_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    operation.id,
                    operation.kind.value,
                    operation.target,
                    json.dumps(
                        dict(operation.payload),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    operation.timestamp_ms,
                    operation.node_id,
                    json.dumps(
                        dict(operation.vector_clock.counters),
                        sort_keys=True,
                    ),
                ),
            )
            self._conn.commit()

    def create(
        self,
        *,
        node_id: str,
        kind: OperationKind,
        target: str,
        payload: dict,
        vector_clock: VectorClock | None = None,
        timestamp_ms: int | None = None,
    ) -> Operation:
        ts = timestamp_ms or int(time.time() * 1000)
        clock = vector_clock or VectorClock()
        clock = clock.increment(node_id)

        operation = Operation(
            id=str(uuid.uuid4()),
            kind=kind,
            target=target,
            payload=payload,
            timestamp_ms=ts,
            node_id=node_id,
            vector_clock=clock,
        )
        self.append(operation)
        return operation

    def get(self, operation_id: str) -> Operation | None:
        row = self._conn.execute(
            """
            SELECT id, kind, target, payload_json, timestamp_ms,
                   node_id, vector_clock_json
            FROM operations
            WHERE id = ?
            """,
            (operation_id,),
        ).fetchone()

        return self._row_to_operation(row) if row else None

    def iter_all(self) -> Iterable[Operation]:
        rows = self._conn.execute(
            """
            SELECT id, kind, target, payload_json, timestamp_ms,
                   node_id, vector_clock_json
            FROM operations
            ORDER BY timestamp_ms, id
            """
        )
        for row in rows:
            yield self._row_to_operation(row)

    def iter_target(self, target: str) -> Iterable[Operation]:
        rows = self._conn.execute(
            """
            SELECT id, kind, target, payload_json, timestamp_ms,
                   node_id, vector_clock_json
            FROM operations
            WHERE target = ?
            ORDER BY timestamp_ms, id
            """,
            (target,),
        )
        for row in rows:
            yield self._row_to_operation(row)

    @staticmethod
    def _row_to_operation(row) -> Operation:
        (
            op_id,
            kind,
            target,
            payload_json,
            timestamp_ms,
            node_id,
            vector_clock_json,
        ) = row

        return Operation(
            id=op_id,
            kind=OperationKind(kind),
            target=target,
            payload=json.loads(payload_json),
            timestamp_ms=timestamp_ms,
            node_id=node_id,
            vector_clock=VectorClock(
                json.loads(vector_clock_json)
            ),
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()