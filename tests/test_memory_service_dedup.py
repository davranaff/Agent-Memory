from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone

from app.services.memory_service import MemoryService


class _DummyEmbedder:
    async def embed(self, text: str):
        return [0.0]


class _FakeShortTerm:
    def __init__(self) -> None:
        self.bump_calls = 0

    async def bump_memory_search_epoch(self) -> None:
        self.bump_calls += 1


class _Mem:
    def __init__(
        self,
        content: str,
        memory_type: str = "general",
        importance: int = 5,
        metadata: dict | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        self.id = uuid.uuid4()
        self.content = content
        self.memory_type = memory_type
        self.importance = importance
        self.metadata_ = metadata or {}
        self.created_at = now
        self.updated_at = now


class _FakeStructured:
    def __init__(self, existing: _Mem | None = None) -> None:
        self.existing = existing
        self.update_calls = 0

    async def find_active_memory_by_fingerprint(
        self,
        fingerprint: str,
        agent_id=None,
        memory_type=None,
        metadata_scope=None,
    ):
        return self.existing

    async def update_memory(self, memory_id, **kwargs):
        self.update_calls += 1
        if self.existing is None:
            return None
        if "importance" in kwargs:
            self.existing.importance = kwargs["importance"]
        if "metadata_" in kwargs:
            self.existing.metadata_ = kwargs["metadata_"]
        self.existing.updated_at = datetime.now(timezone.utc)
        return self.existing

    async def create_memory(self, **kwargs):
        return _Mem(
            content=kwargs["content"],
            memory_type=kwargs["memory_type"],
            importance=kwargs["importance"],
            metadata=kwargs.get("metadata"),
        )


class _FakeVector:
    def __init__(self, created: _Mem) -> None:
        self.created = created
        self.store_calls = 0

    async def store_embedding(self, **kwargs):
        self.store_calls += 1
        return self.created


class MemoryServiceDedupTests(unittest.IsolatedAsyncioTestCase):
    async def test_store_creates_when_no_duplicate(self) -> None:
        short = _FakeShortTerm()
        created = _Mem(content="fact", metadata={})
        svc = MemoryService(db=None, short_term=short, embedding_provider=_DummyEmbedder())
        svc._structured = _FakeStructured(existing=None)
        svc._vector = _FakeVector(created)

        result = await svc.store(
            content="fact",
            memory_type="general",
            metadata={"project_id": "p1"},
            importance=4,
        )

        self.assertFalse(result["deduplicated"])
        self.assertTrue(result["created"])
        self.assertEqual(svc._vector.store_calls, 1)
        self.assertEqual(short.bump_calls, 1)

    async def test_store_deduplicates_existing_memory(self) -> None:
        short = _FakeShortTerm()
        existing = _Mem(content="same fact", importance=3, metadata={"project_id": "p1"})
        svc = MemoryService(db=None, short_term=short, embedding_provider=_DummyEmbedder())
        structured = _FakeStructured(existing=existing)
        svc._structured = structured
        svc._vector = _FakeVector(_Mem(content="unused"))

        result = await svc.store(
            content="same fact",
            memory_type="general",
            metadata={"project_id": "p1"},
            importance=7,
        )

        self.assertTrue(result["deduplicated"])
        self.assertFalse(result["created"])
        self.assertEqual(result["id"], str(existing.id))
        self.assertEqual(existing.importance, 7)
        self.assertEqual(structured.update_calls, 1)
        self.assertEqual(svc._vector.store_calls, 0)
        self.assertEqual(short.bump_calls, 1)


if __name__ == "__main__":
    unittest.main()
