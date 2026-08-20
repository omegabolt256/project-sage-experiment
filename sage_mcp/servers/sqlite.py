from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from mcp.server import MCPServer


ALLOWED_DATABASES = {
    Path(r"D:\Sage\data\tasks.db").resolve(),
    Path(r"D:\Sage\data\evidence.db").resolve(),
}


server = MCPServer("sage-sqlite")


def _database(path: str) -> Path:
    db = Path(path).resolve()

    if db not in ALLOWED_DATABASES:
        raise ValueError(
            f"Database is not allowed: {path}"
        )

    if not db.exists():
        raise FileNotFoundError(
            f"Database does not exist: {path}"
        )

    return db


def _valid_identifier(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            value,
        )
    )


@server.tool()
def sqlite_list_tables(database: str) -> list[str]:
    """List tables in an allowed Sage SQLite database."""
    db = _database(database)

    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' ORDER BY name"
        ).fetchall()

    return [row[0] for row in rows]


@server.tool()
def sqlite_schema(
    database: str,
    table: str,
) -> dict:
    """Return the schema of a table."""
    db = _database(database)

    if not _valid_identifier(table):
        raise ValueError("Invalid table name.")

    with sqlite3.connect(db) as conn:
        columns = conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()

    if not columns:
        raise ValueError(
            f"Table not found: {table}"
        )

    return {
        "database": str(db),
        "table": table,
        "columns": [
            {
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "notnull": bool(row[3]),
                "default": row[4],
                "primary_key": bool(row[5]),
            }
            for row in columns
        ],
    }


@server.tool()
def sqlite_query(
    database: str,
    sql: str,
) -> list[dict]:
    """Execute a read-only SQL query."""
    db = _database(database)
    statement = sql.strip()

    if not statement:
        raise ValueError("SQL query cannot be empty.")

    if not re.match(
        r"(?is)^(SELECT|PRAGMA|WITH)\b",
        statement,
    ):
        raise ValueError(
            "sqlite_query only permits SELECT, PRAGMA, or WITH queries."
        )

    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(statement).fetchall()

    return [dict(row) for row in rows]


@server.tool()
def sqlite_execute(
    database: str,
    sql: str,
) -> dict:
    """Execute a state-changing SQL statement."""
    db = _database(database)
    statement = sql.strip()

    if not statement:
        raise ValueError("SQL statement cannot be empty.")

    with sqlite3.connect(db) as conn:
        cursor = conn.execute(statement)
        conn.commit()

    return {
        "database": str(db),
        "rows_affected": cursor.rowcount,
    }


if __name__ == "__main__":
    server.run("stdio")
