from __future__ import annotations
import re
import sqlparse
from dataclasses import dataclass
from typing import Optional

SELECT_ONLY = re.compile(r"^\s*select\b", re.IGNORECASE | re.DOTALL)
MULTI_STMT = re.compile(r";\s*\S")

@dataclass
class SqlPlan:
    sql: str
    rationale: str

class SqlGuard:
    def __init__(self, max_rows: int = 500):
        self.max_rows = max_rows

    def validate(self, sql: str) -> tuple[bool, str]:
        s = sql.strip()
        if not SELECT_ONLY.search(s):
            return False, "Only SELECT queries are allowed."
        if MULTI_STMT.search(s):
            return False, "Multiple statements are not allowed."
        if re.search(r"\b(drop|alter|insert|update|delete|pragma|attach|detach)\b", s, re.I):
            return False, "Dangerous keyword detected."
        return True, "OK"

    def _remove_limit_in_subqueries(self, s: str) -> str:
        # Remove LIMIT inside parenthesis like "( ... LIMIT n )" -> "( ... )"
        s = re.sub(r"LIMIT\s+\d+\s*\)", ")", s, flags=re.I)
        return s

    def _remove_trailing_commas_before_limit_or_order(self, s: str) -> str:
        # Fix cases like "..., LIMIT" or "..., ORDER BY" by removing a stray comma
        s = re.sub(r",\s*(ORDER\s+BY|LIMIT)\b", r" \1", s, flags=re.I)
        return s

    def _collapse_multiple_limits(self, s: str) -> str:
        # If multiple LIMITs exist, keep the last one and remove earlier ones
        parts = re.split(r"\bLIMIT\s+\d+\b", s, flags=re.I)
        limits = re.findall(r"\bLIMIT\s+\d+\b", s, flags=re.I)
        if not limits:
            return s
        last_limit = limits[-1]
        core = " ".join(parts).strip()
        core = re.sub(r"\s+", " ", core).strip()
        core = re.sub(r"\bLIMIT\s+\d+\s*$", "", core, flags=re.I).strip()
        return core + " " + last_limit

    def apply_autolimit(self, sql: str) -> str:
        s = sql.strip().rstrip(";")

        # 1) Remove LIMITs inside subqueries (common LLM mistake)
        s = self._remove_limit_in_subqueries(s)

        # 2) Remove stray commas before ORDER BY / LIMIT
        s = self._remove_trailing_commas_before_limit_or_order(s)

        # 3) Collapse multiple LIMITs into a single final LIMIT
        s = self._collapse_multiple_limits(s)

        # 4) Remove a trailing stray comma if any
        s = re.sub(r",\s*$", "", s)

        # 5) If LIMIT already at end -> keep it
        if re.search(r"limit\s+\d+\s*$", s, re.I):
            return s

        # 6) Otherwise append one safe LIMIT
        return s + f" LIMIT {self.max_rows}"

    def pretty(self, sql: str) -> str:
        try:
            return sqlparse.format(sql, reindent=True, keyword_case="upper")
        except Exception:
            return sql
