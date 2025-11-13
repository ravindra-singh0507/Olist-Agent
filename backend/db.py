from __future__ import annotations
import sqlite3
import pandas as pd
from typing import Any

class DB:
    def __init__(self, path: str):
        self.path = path

    def connect(self):
        con = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        con.row_factory = sqlite3.Row
        return con

    def run_select(self, sql: str, params: tuple[Any,...] | None = None, limit: int | None = None) -> pd.DataFrame:
        sql_clean = sql.strip().rstrip(";")

    # Add LIMIT if missing
        if limit is not None and " limit " not in sql_clean.lower():
            sql_clean += f" LIMIT {int(limit)}"

        try:
            with self.connect() as con:
                cur = con.execute(sql_clean, params or tuple())
                rows = cur.fetchall()
                if not rows:
                    return pd.DataFrame()
                return pd.DataFrame([dict(r) for r in rows])
        except sqlite3.OperationalError as e:
            # 🔥 THE MOST IMPORTANT FIX
            raise sqlite3.OperationalError(
                f"{e}\n\nWhile executing SQL:\n{sql_clean}"
            )


    def list_tables(self) -> list[str]:
        with self.connect() as con:
            cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1;")
            return [r[0] for r in cur.fetchall()]

    def describe_schema(self) -> str:
        schema_lines = []
        with self.connect() as con:
            for t in self.list_tables():
                schema_lines.append(f"-- {t}")
                cur = con.execute(f"PRAGMA table_info('{t}');")
                cols = [f"  {r[1]} {r[2]}" for r in cur.fetchall()]
                schema_lines.extend(cols)
        return "\n".join(schema_lines)