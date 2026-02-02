"""Vector store backed by pgvector."""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI
from pgvector.psycopg import register_vector
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Integer, MetaData, Table, Text, Column, create_engine, event, func, select, text
from sqlalchemy.engine import Engine


class VectorStore:
    """Postgres vector store with optional hybrid search."""

    def __init__(
        self,
        *,
        db_url: str,
        table_name: str,
        embedding_model: str = "text-embedding-3-small",
        embedding_dim: int = 1536,
    ) -> None:
        self.db_url = db_url
        self.table_name = table_name
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
        self.engine = create_engine(db_url)
        self._client: OpenAI | None = None

        event.listen(self.engine, "connect", self._register_vector)

        metadata = MetaData()
        self.table = Table(
            table_name,
            metadata,
            Column("id", Integer, primary_key=True),
            Column("content", Text, nullable=False),
            Column("embedding", Vector(embedding_dim)),
            Column("metadata", JSON, nullable=True),
            Column("created_at", DateTime, server_default=func.now(), nullable=False),
        )
        self.metadata = metadata
        

    def _register_vector(self, dbapi_connection, _):
        register_vector(dbapi_connection)

    def create(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        self.metadata.create_all(self.engine, tables=[self.table])
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx "
                    f"ON {self.table_name} USING ivfflat (embedding vector_cosine_ops)"
                )
            )
            conn.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {self.table_name}_content_fts_idx "
                    f"ON {self.table_name} USING gin (to_tsvector('english', content))"
                )
            )

    def drop(self) -> None:
        self.metadata.drop_all(self.engine, tables=[self.table])

    def add(self, content: str, metadata: dict[str, Any] | None = None) -> int:
        embedding = self._embed_texts([content])[0]
        with self.engine.begin() as conn:
            result = conn.execute(
                self.table.insert().values(content=content, embedding=embedding, metadata=metadata or {})
            )
            inserted_id = result.inserted_primary_key[0]
        return int(inserted_id)

    def delete(self, item_id: int) -> None:
        with self.engine.begin() as conn:
            conn.execute(self.table.delete().where(self.table.c.id == item_id))

    def exists_by_metadata(self, key: str, value: str) -> bool:
        stmt = text(
            f"SELECT 1 FROM {self.table_name} WHERE metadata ->> :key = :value LIMIT 1"
        )
        with self.engine.connect() as conn:
            result = conn.execute(stmt, {"key": key, "value": value}).first()
        return result is not None

    def search(self, query: str, limit: int = 5, hybrid: bool = True) -> list[dict[str, Any]]:
        query_embedding = self._embed_texts([query])[0]
        semantic = self._semantic_search(query_embedding, limit=max(limit, 10))
        if not hybrid:
            return semantic[:limit]

        keyword = self._keyword_search(query, limit=max(limit, 10))
        if not keyword:
            return semantic[:limit]

        return self._rrf_merge(semantic, keyword, limit=limit)

    def _semantic_search(self, embedding: list[float], limit: int) -> list[dict[str, Any]]:
        distance = self.table.c.embedding.cosine_distance(embedding)
        stmt = (
            select(
                self.table.c.id,
                self.table.c.content,
                self.table.c.metadata,
                (1 - distance).label("score"),
            )
            .order_by(distance)
            .limit(limit)
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

    def _keyword_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        tsvector = func.to_tsvector("english", self.table.c.content)
        tsquery = func.plainto_tsquery("english", query)
        rank = func.ts_rank_cd(tsvector, tsquery)
        stmt = (
            select(
                self.table.c.id,
                self.table.c.content,
                self.table.c.metadata,
                rank.label("score"),
            )
            .where(tsvector.op("@@")(tsquery))
            .order_by(rank.desc())
            .limit(limit)
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

    def _rrf_merge(
        self,
        semantic: list[dict[str, Any]],
        keyword: list[dict[str, Any]],
        *,
        limit: int,
        rrf_k: int = 60,
    ) -> list[dict[str, Any]]:
        scored: dict[int, dict[str, Any]] = {}

        for rank, row in enumerate(semantic, start=1):
            item_id = int(row["id"])
            entry = scored.setdefault(item_id, {**row, "score": 0.0})
            entry["score"] += 1 / (rrf_k + rank)

        for rank, row in enumerate(keyword, start=1):
            item_id = int(row["id"])
            entry = scored.setdefault(item_id, {**row, "score": 0.0})
            entry["score"] += 1 / (rrf_k + rank)

        merged = sorted(scored.values(), key=lambda item: item["score"], reverse=True)
        return merged[:limit]

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        response = client.embeddings.create(model=self.embedding_model, input=texts)
        return [item.embedding for item in response.data]

    def _get_client(self) -> OpenAI:
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not set.")
            self._client = OpenAI(api_key=api_key)
        return self._client
