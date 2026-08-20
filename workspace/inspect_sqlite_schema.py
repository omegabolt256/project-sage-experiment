import sqlite3
from pathlib import Path

for p in Path(r"D:\Sage\data").glob("*.db"):
    print(f"\n=== {p.name} ===")

    with sqlite3.connect(p) as conn:
        rows = conn.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='table' ORDER BY name"
        ).fetchall()

        for name, sql in rows:
            print(f"\nTABLE: {name}")
            print(sql)

            print("COLUMNS:")
            for column in conn.execute(f"PRAGMA table_info({name})"):
                print(column)
