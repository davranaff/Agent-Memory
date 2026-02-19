from __future__ import annotations

import types
import unittest
import uuid
from unittest.mock import AsyncMock, patch


def _install_pgvector_stub_if_missing() -> None:
    try:
        from pgvector.sqlalchemy import Vector  # noqa: F401
    except ModuleNotFoundError:
        import sys
        from sqlalchemy.types import UserDefinedType

        pgvector_mod = types.ModuleType("pgvector")
        pgvector_sqlalchemy_mod = types.ModuleType("pgvector.sqlalchemy")

        class Vector(UserDefinedType):  # pragma: no cover - exercised indirectly
            def __init__(self, *_args, **_kwargs) -> None:
                super().__init__()

            def get_col_spec(self, **_kwargs) -> str:
                return "VECTOR"

        pgvector_sqlalchemy_mod.Vector = Vector
        pgvector_mod.sqlalchemy = pgvector_sqlalchemy_mod
        sys.modules["pgvector"] = pgvector_mod
        sys.modules["pgvector.sqlalchemy"] = pgvector_sqlalchemy_mod


_install_pgvector_stub_if_missing()

from app.services.agent_service import AgentService


class _FakeShortTerm:
    def __init__(self) -> None:
        self.cache: dict[str, dict] = {}

    async def cache_set(self, key: str, value: dict, ttl: int = 3600):
        self.cache[key] = value
        return None

    async def cache_get(self, key: str):
        return self.cache.get(key)

    async def close(self):
        return None


class _DummyTask:
    def add_done_callback(self, _callback):
        return None


class AgentServiceBackgroundTests(unittest.IsolatedAsyncioTestCase):
    async def test_enqueue_run_returns_pending_and_stores_state(self) -> None:
        short_term = _FakeShortTerm()
        svc = AgentService(db=object(), short_term=short_term)
        agent_id = uuid.uuid4()
        svc.get_agent = AsyncMock(return_value={"id": str(agent_id)})

        def _fake_create_task(coro):
            coro.close()
            return _DummyTask()

        with patch(
            "app.services.agent_service.asyncio.create_task",
            side_effect=_fake_create_task,
        ):
            result = await svc.enqueue_run(agent_id=agent_id, input_text="hello")

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["agent_id"], str(agent_id))
        self.assertIn("run_id", result)
        cached = await svc.get_run_status(uuid.UUID(result["run_id"]))
        self.assertIsNotNone(cached)
        self.assertEqual(cached["status"], "pending")

    async def test_enqueue_run_raises_when_agent_missing(self) -> None:
        short_term = _FakeShortTerm()
        svc = AgentService(db=object(), short_term=short_term)
        svc.get_agent = AsyncMock(return_value=None)
        with self.assertRaises(ValueError):
            await svc.enqueue_run(agent_id=uuid.uuid4(), input_text="hello")

    async def test_enqueue_run_rejects_mismatched_project_scope(self) -> None:
        short_term = _FakeShortTerm()
        svc = AgentService(db=object(), short_term=short_term)
        agent_id = uuid.uuid4()
        svc.get_agent = AsyncMock(
            return_value={
                "id": str(agent_id),
                "config": {
                    "project_scoped": True,
                    "project_id": "11111111-1111-1111-1111-111111111111",
                },
            }
        )
        with self.assertRaises(ValueError):
            await svc.enqueue_run(
                agent_id=agent_id,
                input_text="hello",
                context={"project_id": "22222222-2222-2222-2222-222222222222"},
            )

    async def test_get_run_status_returns_none_for_unknown_run(self) -> None:
        short_term = _FakeShortTerm()
        svc = AgentService(db=object(), short_term=short_term)
        result = await svc.get_run_status(uuid.uuid4())
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
