"""Knowledge base built on the vector store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from atlas.core.vector_store import VectorStore


class KnowledgeBase:
    """High-level knowledge base wrapper."""

    def __init__(self, *, name: str, vector_store: VectorStore) -> None:
        self.name = name
        self.vector_store = vector_store

    def insert(
        self,
        *,
        content: str,
        metadata: dict[str, Any] | None = None,
        name: str | None = None,
        skip_if_exists: bool = False,
    ) -> int | None:
        meta = metadata.copy() if metadata else {}
        if name:
            meta.setdefault("name", name)

        if skip_if_exists and name:
            if self.vector_store.exists_by_metadata("name", name):
                return None

        return self.vector_store.add(content, meta)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self.vector_store.search(query, limit=limit, hybrid=True)

    def load_from_directory(self, path: Path | str) -> int:
        base = Path(path)
        if not base.exists():
            return 0

        count = 0
        for file_path in sorted(base.rglob("*")):
            if not file_path.is_file() or file_path.name.startswith("."):
                continue

            if file_path.suffix.lower() not in {".json", ".sql", ".md", ".txt"}:
                continue

            try:
                content = file_path.read_text()
            except OSError:
                continue

            metadata = {
                "source": str(file_path),
                "filename": file_path.name,
            }
            inserted = self.insert(
                name=file_path.stem,
                content=content,
                metadata=metadata,
                skip_if_exists=True,
            )
            if inserted is not None:
                count += 1

        return count

    def load_json(self, payload: dict[str, Any], *, name: str | None = None) -> int | None:
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        return self.insert(content=content, metadata={"type": "json"}, name=name, skip_if_exists=True)
