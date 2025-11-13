from __future__ import annotations
import os
import json
import time
import requests
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import pandas as pd
from backend.db import DB
from backend.nl2sql import SqlGuard, SqlPlan

class ToolChoice(str, Enum):
    ASK = "ask"
    EXPLAIN = "explain"
    TRANSLATE = "translate"

@dataclass
class AgentResult:
    kind: str  # text | table | error
    text: Optional[str] = None
    frame: Optional[pd.DataFrame] = None
    sql: Optional[str] = None
    message: Optional[str] = None

class LLMClient:
    def __init__(self, api_key: str | None, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.provider = "gemini" if "gemini" in model_name else "openrouter"

    def complete(self, system: str, user: str) -> str:
        if not self.api_key:
            # Offline demo: trivial heuristic answer
            return "SELECT * FROM olist_orders_dataset LIMIT 5"
        if self.provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1/models/{self.model_name}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": system + "\n\n" + user}
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0.1}
            }
            r = requests.post(url, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                return json.dumps(data)
        else:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role":"system","content":system},
                    {"role":"user","content":user}
                ],
                "temperature": 0.1,
            }
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

class DataAgent:
    def __init__(self, provider_api_key: str | None, model_name: str, max_rows: int = 500, sql_timeout: int = 20):
        self.llm = LLMClient(provider_api_key, model_name)
        self.guard = SqlGuard(max_rows=max_rows)
        self.max_rows = max_rows
        self.sql_timeout = sql_timeout

    def _schema_prompt(self, db: DB) -> str:
        schema = db.describe_schema()
        return f"""
You are a world-class data analyst. Output ONLY valid SQLite SQL — nothing else.

IMPORTANT RULE ABOUT DATES:
- The Olist dataset contains dates only between 2016 and 2018.
- NEVER use DATE('now') or CURRENT_DATE.
- Whenever the user asks for a time period (e.g., "last 2 quarters", "last 6 months"):
  ALWAYS compute dates relative to the dataset using:
  (SELECT DATE(MAX(order_purchase_timestamp), '-X months') FROM olist_orders_dataset)
  Example:
  WHERE order_purchase_timestamp >= (
      SELECT DATE(MAX(order_purchase_timestamp), '-6 months')
      FROM olist_orders_dataset
  )

STRICT RULES:
- Use only: SELECT, FROM, JOIN, WHERE, GROUP BY, ORDER BY, LIMIT.
- LIMIT must appear ONLY at the end of the query.
- NEVER use LIMIT inside subqueries.
- NEVER add two LIMITs.
- If using aggregation, ALWAYS include GROUP BY.
- Do NOT use: QUALIFY, HAVING without GROUP BY, window functions, USING(), ILIKE.
- Use explicit JOIN ON statements.

Return ONLY the SQL. No explanations.

Schema:\n{schema}
""".strip()


    def _postprocess_to_sql(self, raw: str) -> str:
        text = raw.strip()
        fence = "```"
        if fence in text:
            inner = text.split(fence)
            candidates = [c for c in inner if "select" in c.lower()]
            text = candidates[-1] if candidates else text
        text = text.replace("sql", "")
        idx = text.lower().find("select")
        return text[idx:].strip() if idx >= 0 else text

    def answer_query(self, question: str, db: DB) -> AgentResult:
        try:
            sys = self._schema_prompt(db)
            usr = f"Question: {question}\nReturn only SQL for SQLite."
            raw = self.llm.complete(sys, usr)

            # Print raw model output to the server console (Streamlit logs)
            print("\\n=== LLM RAW OUTPUT START ===")
            print(raw)
            print("=== LLM RAW OUTPUT END ===\\n")

            sql = self._postprocess_to_sql(raw)

            print("\\n=== POST-PROCESSED SQL BEFORE GUARD ===")
            print(sql)
            print("=== END ===\\n")

            ok, why = self.guard.validate(sql)
            if not ok:
                return AgentResult(kind="error", message=f"Blocked query: {why}", sql=sql)

            sql = self.guard.apply_autolimit(sql)
            pretty = self.guard.pretty(sql)

            print("\\n=== FINAL SQL TO EXECUTE ===")
            print(pretty)
            print("=== END ===\\n")

            frame = db.run_select(sql, limit=self.max_rows)
            if frame.empty:
                return AgentResult(kind="text", text=f"No rows returned.\\n\\nSQL:\\n```sql\\n{pretty}\\n```")
            return AgentResult(kind="table", frame=frame, sql=pretty)
        except Exception as e:
            return AgentResult(kind="error", message=str(e))
