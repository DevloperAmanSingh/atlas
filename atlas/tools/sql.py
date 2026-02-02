"""SQL execution tool."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from atlas.core.tools import tool

_DANGEROUS = {"drop", "delete", "truncate", "insert", "update", "alter", "create"}


def create_sql_tool(db_url: str):
    """Create SQL execution tool for the agent."""
    engine = create_engine(db_url)

    @tool
    def execute_sql(query: str, limit: int = 50) -> str:
        """Execute a read-only SQL query and return results as markdown."""
        if not query or not query.strip():
            return "Error: query is required."
        if limit <= 0:
            return "Error: limit must be positive."

        sql = query.strip()
        lowered = re.sub(r"\s+", " ", sql.lower())

        if not (lowered.startswith("select") or lowered.startswith("with")):
            return "Error: only SELECT queries are allowed."

        for keyword in _DANGEROUS:
            if f" {keyword} " in f" {lowered} ":
                return f"Error: query contains dangerous keyword: {keyword}"

        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                if not result.returns_rows:
                    return "No rows returned."

                rows = result.fetchmany(limit)
                if not rows:
                    return "No rows returned."

                headers = list(result.keys())
                lines = [
                    "| " + " | ".join(headers) + " |",
                    "| " + " | ".join(["---"] * len(headers)) + " |",
                ]
                for row in rows:
                    lines.append("| " + " | ".join(_format_cell(value) for value in row) + " |")

                if len(rows) == limit:
                    lines.append(f"\n_Showing first {limit} rows._")

                return "\n".join(lines)
        except SQLAlchemyError as exc:
            return f"Error: {exc}"

    return execute_sql


def _format_cell(value: Any) -> str:
    if value is None:
        return "NULL"
    text_value = str(value)
    return text_value.replace("\n", " ")
