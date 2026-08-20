import sqlite3
from pathlib import Path

for p in Path(r"D:\Sage\data").glob("*.db"):
    with sqlite3.connect(p) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

    print(f"{p.name}: {tables}")
