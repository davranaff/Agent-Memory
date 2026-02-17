"""Vector memory store — pgvector similarity search."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Memory
from app.memory.embeddings import EmbeddingProvider


class VectorMemoryStore:
    """Embedding storage and semantic similarity search using pgvector."""

    def __init__(self, db: AsyncSession, embedding_provider: EmbeddingProvider) -> None:
        self._db = db
        self._embedder = embedding_provider

    async def store_embedding(
        self,
        content: str,
        memory_type: str = "general",
        agent_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
        importance: int = 5,
    ) -> Memory:
        """Embed content and store with its vector."""
        embedding = await self._embedder.embed(content)
        mem = Memory(
            content=content,
            memory_type=memory_type,
            agent_id=agent_id,
            metadata_=metadata or {},
            embedding=embedding,
            importance=importance,
        )
        self._db.add(mem)
        await self._db.flush()
        await self._db.refresh(mem)
        return mem

    async def search_similar(
        self,
        query: str,
        top_k: int = 10,
        agent_id: uuid.UUID | None = None,
        memory_type: str | None = None,
        metadata_filters: dict[str, Any] | None = None,
        min_similarity: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Semantic similarity search using cosine distance."""
        query_embedding = await self._embedder.embed(query)

        # Build the raw SQL for pgvector cosine similarity
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        filters = ["m.is_active = true", "m.embedding IS NOT NULL"]
        params: dict[str, Any] = {"embedding": embedding_str, "top_k": top_k}

        if agent_id:
            filters.append("m.agent_id = :agent_id")
            params["agent_id"] = str(agent_id)

        if memory_type:
            filters.append("m.memory_type = :memory_type")
            params["memory_type"] = memory_type
        if metadata_filters:
            filters.append("m.metadata @> CAST(:metadata_filter AS jsonb)")
            params["metadata_filter"] = json.dumps(metadata_filters, ensure_ascii=True)

        where_clause = " AND ".join(filters)

        sql = text(f"""
            SELECT
                m.id, m.content, m.memory_type, m.agent_id,
                m.metadata, m.importance, m.is_active,
                m.created_at, m.updated_at,
                1 - (m.embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM memories m
            WHERE {where_clause}
            ORDER BY m.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)

        result = await self._db.execute(sql, params)
        rows = result.fetchall()

        results = []
        for row in rows:
            sim = float(row.similarity)
            if sim < min_similarity:
                continue
            results.append({
                "id": row.id,
                "content": row.content,
                "memory_type": row.memory_type,
                "agent_id": row.agent_id,
                "metadata": row.metadata,
                "importance": row.importance,
                "is_active": row.is_active,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "similarity": sim,
            })

        return results

    async def delete_embedding(self, memory_id: uuid.UUID) -> bool:
        """Soft-delete a memory and its embedding."""
        result = await self._db.execute(
            update(Memory)
            .where(Memory.id == memory_id)
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        await self._db.flush()
        return result.rowcount > 0

    async def update_embedding(
        self,
        memory_id: uuid.UUID,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Memory | None:
        """Update memory content and re-embed if content changed."""
        mem = await self._db.get(Memory, memory_id)
        if mem is None:
            return None

        updates: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}

        if content is not None and content != mem.content:
            updates["content"] = content
            updates["embedding"] = await self._embedder.embed(content)

        if metadata is not None:
            updates["metadata_"] = metadata

        if updates:
            for k, v in updates.items():
                setattr(mem, k, v)
            await self._db.flush()
            await self._db.refresh(mem)

        return mem

    async def list_missing_embeddings(
        self,
        limit: int = 100,
        agent_id: uuid.UUID | None = None,
        memory_type: str | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[Memory]:
        """List active memories that currently have no embedding vector."""
        q = select(Memory).where(
            Memory.is_active.is_(True),
            Memory.embedding.is_(None),
        )
        if agent_id:
            q = q.where(Memory.agent_id == agent_id)
        if memory_type:
            q = q.where(Memory.memory_type == memory_type)
        if metadata_filters:
            q = q.where(Memory.metadata_.contains(metadata_filters))

        result = await self._db.execute(
            q.order_by(Memory.created_at.asc()).limit(limit)
        )
        return list(result.scalars().all())

    async def backfill_embeddings(
        self,
        memories: list[Memory],
    ) -> tuple[int, list[dict[str, str]]]:
        """Generate and write embeddings for provided memory rows."""
        updated = 0
        failures: list[dict[str, str]] = []

        for mem in memories:
            try:
                emb = await self._embedder.embed(mem.content)
                mem.embedding = emb
                mem.updated_at = datetime.now(timezone.utc)
                updated += 1
            except Exception as e:
                failures.append({
                    "id": str(mem.id),
                    "error": str(e),
                })

        if updated:
            await self._db.flush()

        return updated, failures
