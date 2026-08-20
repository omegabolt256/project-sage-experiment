from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(r"D:\Sage\data\tasks.db")


class TaskStore:
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    conversation_id TEXT PRIMARY KEY,
                    task_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save(self, conversation_id: str, task: Any) -> None:
        payload = {
            "task_id": task.task_id,
            "intent": task.intent,
            "topic": task.topic,
            "active_capability": task.active_capability,
            "current_focus": task.current_focus,
            "depth": task.depth,
            "sources": [
                {
                    "source_type": e.source_type,
                    "title": e.title,
                    "url": e.url,
                    "content": e.content,
                    "metadata": e.metadata,
                }
                for e in task.sources
            ],
            "tool_results": task.tool_results,
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks(conversation_id, task_json)
                VALUES(?, ?)
                ON CONFLICT(conversation_id)
                DO UPDATE SET task_json = excluded.task_json
                """,
                (conversation_id, json.dumps(payload, ensure_ascii=False)),
            )
            conn.commit()

    def load(self, conversation_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT task_json FROM tasks WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
        return None if row is None else json.loads(row["task_json"])
