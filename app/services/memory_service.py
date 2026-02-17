"""Memory service — orchestrates structured, vector, and short-term memory."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.embeddings import EmbeddingProvider, get_embedding_provider
from app.memory.short_term import ShortTermMemory
from app.memory.structured import StructuredMemoryStore
from app.memory.vector import VectorMemoryStore

logger = logging.getLogger(__name__)


class MemoryService:
    """High-level memory operations spanning all three memory layers."""

    def __init__(
        self,
        db: AsyncSession,
        short_term: ShortTermMemory | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        db_lock: asyncio.Lock | None = None,
    ) -> None:
        self._db = db
        self._db_lock = db_lock or asyncio.Lock()
        self._embedding_provider = embedding_provider or get_embedding_provider()
        self._structured = StructuredMemoryStore(db)
        self._vector = VectorMemoryStore(db, self._embedding_provider)
        self._short_term = short_term or ShortTermMemory()

    # ── Store ─────────────────────────────────────────────────────────
    async def store(
        self,
        content: str,
        memory_type: str = "general",
        agent_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
        importance: int = 5,
    ) -> dict[str, Any]:
        """Store memory with embedding in both structured and vector stores."""
        normalized_content = content.strip()
        metadata_payload = dict(metadata or {})
        fingerprint = hashlib.sha256(
            f"{memory_type}|{normalized_content}".encode("utf-8")
        ).hexdigest()
        metadata_payload["__fingerprint"] = fingerprint

        metadata_scope = {
            key: metadata_payload[key]
            for key in ("project_id", "session_id", "component_id")
            if key in metadata_payload and metadata_payload[key] is not None
        }
        existing = await self._structured.find_active_memory_by_fingerprint(
            fingerprint=fingerprint,
            agent_id=agent_id,
            memory_type=memory_type,
            metadata_scope=metadata_scope or None,
        )
        if existing is not None:
            merged_metadata = dict(existing.metadata_ or {})
            changed = False
            for key, value in metadata_payload.items():
                if key not in merged_metadata and value is not None:
                    merged_metadata[key] = value
                    changed = True

            new_importance = max(int(existing.importance or 0), int(importance))
            if new_importance != existing.importance:
                changed = True

            if changed:
                updated = await self._structured.update_memory(
                    existing.id,
                    importance=new_importance,
                    metadata_=merged_metadata,
                )
                if updated is not None:
                    existing = updated
                try:
                    await self._short_term.bump_memory_search_epoch()
                except Exception:
                    pass

            return {
                "id": str(existing.id),
                "content": existing.content,
                "memory_type": existing.memory_type,
                "importance": existing.importance,
                "created_at": str(existing.created_at),
                "deduplicated": True,
                "created": False,
            }

        try:
            mem = await self._vector.store_embedding(
                content=normalized_content,
                memory_type=memory_type,
                agent_id=agent_id,
                metadata=metadata_payload,
                importance=importance,
            )
            logger.info("Stored memory %s with embedding", mem.id)
            try:
                await self._short_term.bump_memory_search_epoch()
            except Exception:
                pass
            return {
                "id": str(mem.id),
                "content": mem.content,
                "memory_type": mem.memory_type,
                "importance": mem.importance,
                "created_at": str(mem.created_at),
                "deduplicated": False,
                "created": True,
            }
        except Exception as e:
            logger.warning("Embedding failed, storing without vector: %s", e)
            # Fallback: store without embedding
            mem = await self._structured.create_memory(
                content=normalized_content,
                memory_type=memory_type,
                agent_id=agent_id,
                metadata=metadata_payload,
                importance=importance,
            )
            try:
                await self._short_term.bump_memory_search_epoch()
            except Exception:
                pass
            return {
                "id": str(mem.id),
                "content": mem.content,
                "memory_type": mem.memory_type,
                "importance": mem.importance,
                "created_at": str(mem.created_at),
                "deduplicated": False,
                "created": True,
            }

    # ── Search ────────────────────────────────────────────────────────
    async def search(
        self,
        query: str,
        agent_id: uuid.UUID | None = None,
        memory_type: str | None = None,
        metadata_filters: dict[str, Any] | None = None,
        top_k: int = 10,
        min_similarity: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Semantic search with caching."""
        # Skip vector search for empty queries
        if not query or not query.strip():
            logger.debug("Empty query, skipping vector search")
            return []

        # Check cache (epoch-based key prevents stale results after writes/deletes)
        try:
            cache_epoch = await self._short_term.get_memory_search_epoch()
        except Exception:
            cache_epoch = 0
        metadata_key = (
            json.dumps(metadata_filters, sort_keys=True, ensure_ascii=True)
            if metadata_filters
            else "{}"
        )
        cache_hash = hashlib.md5(
            f"{query}:{agent_id}:{memory_type}:{metadata_key}:{top_k}:{min_similarity}:{cache_epoch}".encode()
        ).hexdigest()

        cached = await self._short_term.get_cached_search_results(cache_hash)
        if cached is not None:
            logger.debug("Cache hit for search: %s", query[:50])
            return cached

        # Perform vector search
        vector_results: list[dict[str, Any]] = []
        try:
            # Use nested transaction (SAVEPOINT) so that if this query fails,
            # it doesn't abort the entire transaction or expire session objects.
            # We use a lock because only one nested transaction can be active per session.
            async with self._db_lock:
                async with self._db.begin_nested():
                    vector_results = await self._vector.search_similar(
                        query=query,
                        top_k=top_k,
                        agent_id=agent_id,
                        memory_type=memory_type,
                        metadata_filters=metadata_filters,
                        min_similarity=min_similarity,
                    )
        except Exception as e:
            logger.warning("Vector search failed, using lexical fallback: %s", e)
            vector_results = []

        # Lexical fallback:
        # 1) always when vector is empty
        # 2) also as supplement for large corpora / sparse semantic matches
        lexical_results: list[dict[str, Any]] = []
        if len(vector_results) < top_k:
            memories = await self._structured.search_memories_text(
                query=query,
                agent_id=agent_id,
                memory_type=memory_type,
                metadata_filters=metadata_filters,
                limit=top_k * 3,
            )
            lexical_results = [
                {
                    "id": str(m.id),
                    "content": m.content,
                    "memory_type": m.memory_type,
                    "agent_id": str(m.agent_id) if m.agent_id else None,
                    "metadata": m.metadata_,
                    "importance": m.importance,
                    "similarity": 0.0,
                    "created_at": str(m.created_at),
                    "updated_at": str(m.updated_at),
                }
                for m in memories
            ]

        # Merge unique results, prefer vector-ranked rows first.
        results: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for result_set in (vector_results, lexical_results):
            for row in result_set:
                rid = str(row.get("id"))
                if rid in seen_ids:
                    continue
                normalized = dict(row)
                normalized["id"] = rid
                normalized["agent_id"] = (
                    str(normalized["agent_id"])
                    if normalized.get("agent_id") is not None
                    else None
                )
                results.append(normalized)
                seen_ids.add(rid)
                if len(results) >= top_k:
                    break
            if len(results) >= top_k:
                break

        # Cache results
        try:
            await self._short_term.cache_search_results(cache_hash, results)
        except Exception:
            pass  # Caching is optional

        return results

    # ── Get ───────────────────────────────────────────────────────────
    async def get(self, memory_id: uuid.UUID) -> dict[str, Any] | None:
        """Get a specific memory by ID."""
        mem = await self._structured.get_memory(memory_id)
        if mem is None:
            return None
        return {
            "id": str(mem.id),
            "content": mem.content,
            "memory_type": mem.memory_type,
            "agent_id": str(mem.agent_id) if mem.agent_id else None,
            "metadata": mem.metadata_,
            "importance": mem.importance,
            "is_active": mem.is_active,
            "created_at": str(mem.created_at),
            "updated_at": str(mem.updated_at),
        }

    # ── Delete ────────────────────────────────────────────────────────
    async def delete(self, memory_id: uuid.UUID) -> bool:
        """Soft-delete a memory."""
        deleted = await self._vector.delete_embedding(memory_id)
        if deleted:
            try:
                await self._short_term.bump_memory_search_epoch()
            except Exception:
                pass
        return deleted

    async def reindex_embeddings(
        self,
        limit: int = 100,
        agent_id: uuid.UUID | None = None,
        memory_type: str | None = None,
        metadata_filters: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Backfill embeddings for memories that are missing vectors."""
        if limit < 1:
            limit = 1
        if limit > 1000:
            limit = 1000

        async with self._db_lock:
            async with self._db.begin_nested():
                missing = await self._vector.list_missing_embeddings(
                    limit=limit,
                    agent_id=agent_id,
                    memory_type=memory_type,
                    metadata_filters=metadata_filters,
                )

        if dry_run:
            return {
                "dry_run": True,
                "scanned": len(missing),
                "candidate_ids": [str(m.id) for m in missing],
                "reindexed": 0,
                "failed": 0,
                "failures": [],
            }

        if not missing:
            return {
                "dry_run": False,
                "scanned": 0,
                "reindexed": 0,
                "failed": 0,
                "failures": [],
            }

        updated, failures = await self._vector.backfill_embeddings(missing)
        if updated:
            try:
                await self._short_term.bump_memory_search_epoch()
            except Exception:
                pass

        return {
            "dry_run": False,
            "scanned": len(missing),
            "reindexed": updated,
            "failed": len(failures),
            "failures": failures,
        }

    # ── Shorthand accessors ───────────────────────────────────────────
    @property
    def structured(self) -> StructuredMemoryStore:
        return self._structured

    @property
    def short_term(self) -> ShortTermMemory:
        return self._short_term
