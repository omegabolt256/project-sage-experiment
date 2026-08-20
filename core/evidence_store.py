from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

DB_PATH = Path(r"D:\Sage\data\evidence.db")


class EvidenceStore:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evidence (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_evidence_conversation
                ON evidence(conversation_id)
            """)
            conn.commit()

    def add(
        self,
        conversation_id: str,
        source_type: str,
        title: str = "",
        url: str = "",
        content: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        evidence_id = str(uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO evidence(
                    id, conversation_id, source_type,
                    title, url, content, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    conversation_id,
                    source_type,
                    title,
                    url,
                    content,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )
            conn.commit()
        return evidence_id

    def list_for_conversation(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, source_type, title, url, content,
                       metadata_json, created_at
                FROM evidence
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (conversation_id, limit),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "source_type": row["source_type"],
                "title": row["title"],
                "url": row["url"],
                "content": row["content"],
                "metadata": json.loads(row["metadata_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def clear_conversation(self, conversation_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM evidence WHERE conversation_id = ?",
                (conversation_id,),
            )
            conn.commit()
