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

from app.orchestration.service import OrchestrationService
from app.orchestration.workflows import ExecutionMode, WorkflowDefinition, WorkflowStep


class _FakeDB:
    def __init__(self) -> None:
        self.added = []
        self.refreshed = []
        self.commits = 0

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj) -> None:
        self.refreshed.append(obj)


class _DummyTask:
    def add_done_callback(self, _callback):
        return None


class OrchestrationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_ensure_workflow_agents_autocreates_missing(self) -> None:
        db = _FakeDB()
        svc = OrchestrationService(db)

        workflow = WorkflowDefinition(
            name="wf",
            execution_mode=ExecutionMode.SEQUENTIAL,
            steps=(WorkflowStep(agent_name="reasoning_agent"),),
        )

        resolve_map: dict[str, uuid.UUID] = {}

        async def _resolve(name: str):
            return resolve_map.get(name)

        async def _create_agent(name: str, **_kwargs):
            resolve_map[name] = uuid.uuid4()
            return {"id": str(resolve_map[name]), "name": name}

        svc._settings = types.SimpleNamespace(orchestration_autocreate_agents=True)
        svc._registry = types.SimpleNamespace(resolve=AsyncMock(side_effect=_resolve))
        svc._agent_service = types.SimpleNamespace(create_agent=AsyncMock(side_effect=_create_agent))

        await svc._ensure_workflow_agents(workflow)
        self.assertIn("reasoning_agent", resolve_map)
        self.assertEqual(svc._agent_service.create_agent.await_count, 1)

    async def test_ensure_workflow_agents_raises_when_disabled(self) -> None:
        db = _FakeDB()
        svc = OrchestrationService(db)

        workflow = WorkflowDefinition(
            name="wf",
            execution_mode=ExecutionMode.SEQUENTIAL,
            steps=(WorkflowStep(agent_name="reasoning_agent"),),
        )

        svc._settings = types.SimpleNamespace(orchestration_autocreate_agents=False)
        svc._registry = types.SimpleNamespace(resolve=AsyncMock(return_value=None))
        svc._agent_service = types.SimpleNamespace(create_agent=AsyncMock())

        with self.assertRaises(ValueError):
            await svc._ensure_workflow_agents(workflow)

    async def test_ensure_workflow_agents_project_scoped(self) -> None:
        db = _FakeDB()
        svc = OrchestrationService(db)

        workflow = WorkflowDefinition(
            name="wf",
            execution_mode=ExecutionMode.SEQUENTIAL,
            steps=(WorkflowStep(agent_name="planner"), WorkflowStep(agent_name="coder")),
        )
        planner_id = uuid.uuid4()
        coder_id = uuid.uuid4()
        svc._agent_service = types.SimpleNamespace(
            ensure_project_agents=AsyncMock(
                return_value={
                    "planner": {"id": str(planner_id)},
                    "coder": {"id": str(coder_id)},
                }
            )
        )

        mapping = await svc._ensure_workflow_agents(
            workflow,
            project_id="11111111-1111-1111-1111-111111111111",
        )

        self.assertEqual(mapping["planner"], planner_id)
        self.assertEqual(mapping["coder"], coder_id)

    async def test_start_run_passes_run_id_to_orchestrator(self) -> None:
        db = _FakeDB()
        svc = OrchestrationService(db)
        run_id = uuid.uuid4()

        workflow = WorkflowDefinition(
            name="reasoning_workflow",
            execution_mode=ExecutionMode.SEQUENTIAL,
            steps=(WorkflowStep(agent_name="reasoning_agent"),),
        )
        execute_mock = AsyncMock(
            return_value={"run_id": str(run_id), "workflow": workflow.name, "status": "completed", "result": "ok"}
        )
        svc._orchestrator = types.SimpleNamespace(execute_workflow=execute_mock)
        svc._ensure_workflow_agents = AsyncMock(return_value={})

        with patch("app.orchestration.service.get_workflow", return_value=workflow):
            result = await svc.start_run(
                workflow_name=workflow.name,
                input_text="analyze",
                auto_route=False,
                run_id=run_id,
            )

        self.assertEqual(result["status"], "completed")
        execute_mock.assert_awaited_once_with(
            workflow_name=workflow.name,
            input_text="analyze",
            run_id=run_id,
            project_id=None,
            agent_overrides={},
        )

    async def test_enqueue_run_returns_pending(self) -> None:
        db = _FakeDB()
        svc = OrchestrationService(db)

        workflow = WorkflowDefinition(
            name="reasoning_workflow",
            execution_mode=ExecutionMode.SEQUENTIAL,
            steps=(WorkflowStep(agent_name="reasoning_agent"),),
        )
        svc._ensure_workflow_agents = AsyncMock(return_value={})

        def _fake_create_task(coro):
            coro.close()
            return _DummyTask()

        with (
            patch("app.orchestration.service.get_workflow", return_value=workflow),
            patch("app.orchestration.service.asyncio.create_task", side_effect=_fake_create_task),
        ):
            result = await svc.enqueue_run(
                workflow_name=workflow.name,
                input_text="analyze",
                auto_route=False,
            )

        self.assertEqual(result["status"], "pending")
        self.assertTrue(result["queued"])
        self.assertEqual(db.commits, 1)


if __name__ == "__main__":
    unittest.main()
