"""Learning system wrapper for Atlas."""

from __future__ import annotations

from typing import Any

from atlas.core.knowledge import KnowledgeBase
from atlas.core.tools import tool


class LearningSystem:
    """Simple learning system backed by a knowledge base."""

    def __init__(self, knowledge: KnowledgeBase) -> None:
        self.knowledge = knowledge

        @tool
        def search_learnings(query: str, limit: int = 5) -> str:
            """Search past learnings for relevant context."""
            results = self.knowledge.search(query, limit=limit)
            return _format_results(results, header="## Learnings")

        @tool
        def save_learning(title: str, learning: str) -> str:
            """Save a new learning discovered during analysis."""
            if not title or not title.strip():
                return "Error: title is required."
            if not learning or not learning.strip():
                return "Error: learning is required."

            metadata = {"type": "learning", "title": title.strip()}
            self.knowledge.insert(
                name=title.strip(),
                content=learning.strip(),
                metadata=metadata,
                skip_if_exists=False,
            )
            return f"Saved learning: {title.strip()}"

        self._search_learnings_tool = search_learnings
        self._save_learning_tool = save_learning

    @property
    def tools(self) -> list[Any]:
        return [self._search_learnings_tool, self._save_learning_tool]

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self.knowledge.search(query, limit=limit)


def _format_results(results: list[dict[str, Any]], *, header: str) -> str:
    if not results:
        return "No results found."

    lines = [header, ""]
    for row in results:
        meta = row.get("metadata") or {}
        title = meta.get("title") or meta.get("name") or f"Result {row.get('id')}"
        content = row.get("content", "")
        snippet = content[:300].strip().replace("\n", " ")
        lines.append(f"- **{title}**: {snippet}")

    return "\n".join(lines)
