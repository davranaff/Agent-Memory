from __future__ import annotations

import importlib
import sys
import types
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch


def _install_mcp_stubs_if_missing() -> None:
    """Install lightweight stubs for optional MCP deps used in unit tests."""
    try:
        import fastmcp  # noqa: F401
    except ModuleNotFoundError:
        fastmcp_mod = types.ModuleType("fastmcp")

        class _DummyMCPServer:
            async def run(self, *_args, **_kwargs):
                return None

            def create_initialization_options(self):
                return {}

        class FastMCP:  # pragma: no cover - exercised indirectly
            def __init__(self, *_args, **_kwargs) -> None:
                self._mcp_server = _DummyMCPServer()

            def tool(self, name: str | None = None):
                def _decorator(func):
                    return func

                return _decorator

        fastmcp_mod.FastMCP = FastMCP
        sys.modules["fastmcp"] = fastmcp_mod

    try:
        import mcp  # noqa: F401
    except ModuleNotFoundError:
        mcp_mod = types.ModuleType("mcp")
        mcp_types_mod = types.ModuleType("mcp.types")

        class JSONRPCRequest:
            def __init__(self, method: str = "") -> None:
                self.method = method

        class JSONRPCNotification:
            def __init__(self, jsonrpc: str = "2.0", method: str = "", params: dict | None = None):
                self.jsonrpc = jsonrpc
                self.method = method
                self.params = params or {}

        class JSONRPCMessage:
            def __init__(self, root=None) -> None:
                self.root = root

            @classmethod
            def model_validate(cls, payload):
                return cls(root=payload)

        mcp_types_mod.JSONRPCRequest = JSONRPCRequest
        mcp_types_mod.JSONRPCNotification = JSONRPCNotification
        mcp_types_mod.JSONRPCMessage = JSONRPCMessage
        mcp_mod.types = mcp_types_mod

        sys.modules["mcp"] = mcp_mod
        sys.modules["mcp.types"] = mcp_types_mod

    try:
        from pgvector.sqlalchemy import Vector  # noqa: F401
    except ModuleNotFoundError:
        pgvector_mod = types.ModuleType("pgvector")
        pgvector_sqlalchemy_mod = types.ModuleType("pgvector.sqlalchemy")
        from sqlalchemy.types import UserDefinedType

        class Vector(UserDefinedType):  # pragma: no cover - exercised indirectly
            def __init__(self, *_args, **_kwargs) -> None:
                super().__init__()

            def get_col_spec(self, **_kwargs) -> str:
                return "VECTOR"

        pgvector_sqlalchemy_mod.Vector = Vector
        pgvector_mod.sqlalchemy = pgvector_sqlalchemy_mod
        sys.modules["pgvector"] = pgvector_mod
        sys.modules["pgvector.sqlalchemy"] = pgvector_sqlalchemy_mod


_install_mcp_stubs_if_missing()
mcp_server = importlib.import_module("app.mcp.server")


class _FakeShortTerm:
    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}
        self.last_ttl: int | None = None

    async def cache_get(self, key: str):
        return self._cache.get(key)

    async def cache_set(self, key: str, value: dict, ttl: int):
        self._cache[key] = value
        self.last_ttl = ttl
        return True

    async def cache_delete(self, key: str):
        return self._cache.pop(key, None) is not None

    async def close(self):
        return None


class _FakeDBSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self):
        return None

    async def rollback(self):
        return None


class _FakeSessionFactory:
    def __call__(self):
        return _FakeDBSession()


class _FakeScalarResult:
    def __init__(self, value) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeDBSessionWithComponent(_FakeDBSession):
    def __init__(self, component_id: str | None) -> None:
        self.component_id = component_id

    async def execute(self, _stmt):
        return _FakeScalarResult(self.component_id)


class _FakeSessionFactoryWithComponent:
    def __init__(self, component_id: str | None) -> None:
        self.component_id = component_id

    def __call__(self):
        return _FakeDBSessionWithComponent(self.component_id)


class _FakeSQLResult:
    def __init__(self, columns: list[str], rows: list[tuple]) -> None:
        self._columns = columns
        self._rows = rows

    def fetchmany(self, limit: int):
        return self._rows[:limit]

    def keys(self):
        return self._columns


class _FakeDBSessionForQuery(_FakeDBSession):
    def __init__(self, columns: list[str], rows: list[tuple]) -> None:
        self._result = _FakeSQLResult(columns, rows)
        self.executed_sql: str | None = None

    async def execute(self, statement):
        self.executed_sql = str(statement)
        return self._result


class _FakeSessionFactoryForQuery:
    def __init__(self, db_session: _FakeDBSessionForQuery) -> None:
        self.db_session = db_session

    def __call__(self):
        return self.db_session


class _FakeProject:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.name = "Autonomous Project"
        self.path = "/host-projects/autonomous-project"
        self.analysis_status = "completed"
        self.last_analyzed = datetime.now(timezone.utc)
        self.total_files = 10
        self.total_lines = 500
        self.architecture_type = "layered"
        self.tech_stack = ["python"]
        self.frameworks = ["fastapi"]
        self.languages = ["python"]
        self.databases = ["postgresql"]
        self.build_tools = ["docker"]


class _FakeIndexer:
    last_index_kwargs: dict | None = None

    def __init__(self, _db) -> None:
        self.project = _FakeProject()

    async def index_project(self, project_path: str, project_name: str | None, force_reindex: bool):
        _FakeIndexer.last_index_kwargs = {
            "project_path": project_path,
            "project_name": project_name,
            "force_reindex": force_reindex,
        }
        return self.project

    async def get_project_summary(self, project_id: str):
        return {"project_id": project_id, "ok": True}


class _FakeGraphDependencyService:
    last_call: dict | None = None

    def __init__(self, _db) -> None:
        return None

    async def graph_neighbors(self, project_id: str, component_id: str, depth: int = 1):
        _FakeGraphDependencyService.last_call = {
            "project_id": project_id,
            "component_id": component_id,
            "depth": depth,
        }
        return {
            "project_id": project_id,
            "component_id": component_id,
            "depth": depth,
            "neighbors": [],
        }


class MCPToolsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.fake_short_term = _FakeShortTerm()
        mcp_server._shared_short_term = self.fake_short_term
        await mcp_server._clear_active_mcp_context()

    async def asyncTearDown(self) -> None:
        await mcp_server._clear_active_mcp_context()
        mcp_server._shared_short_term = None

    async def test_context_set_get_clear_roundtrip(self) -> None:
        agent_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        result = await mcp_server.context_set(
            agent_id=agent_id,
            project_id=project_id,
            project_path="/tmp/repo",
            session_id=session_id,
            ttl_seconds=1,  # should be clamped to >= 60 internally
        )

        self.assertEqual(result["context"]["agent_id"], agent_id)
        self.assertEqual(result["context"]["project_path"], "/tmp/repo")
        self.assertEqual(self.fake_short_term.last_ttl, 60)

        fetched = await mcp_server.context_get()
        self.assertEqual(fetched["context"]["project_id"], project_id)
        self.assertEqual(fetched["context"]["session_id"], session_id)

        cleared = await mcp_server.context_clear()
        self.assertTrue(cleared["cleared"])

    async def test_context_set_rejects_invalid_uuid(self) -> None:
        result = await mcp_server.context_set(agent_id="not-a-uuid")
        self.assertIn("error", result)
        self.assertIn("Invalid UUID", result["error"])

    async def test_project_analyze_uses_env_fallback_and_sets_context(self) -> None:
        mocked_brain_memory = {
            "stored": 4,
            "created": 4,
            "deduplicated": 0,
            "memory_ids": ["m1", "m2", "m3", "m4"],
        }
        with (
            patch("app.indexing.ProjectIndexer", _FakeIndexer),
            patch.object(mcp_server, "_get_session_factory", return_value=_FakeSessionFactory()),
            patch.object(mcp_server, "_auto_project_path_from_env", return_value="/tmp/ide-project"),
            patch("app.mcp.server.MemoryService", return_value=object()),
            patch("app.mcp.server.AgentService") as mock_agent_service,
            patch("app.mcp.server.persist_project_memories", new_callable=AsyncMock, return_value=mocked_brain_memory),
        ):
            mock_agent_service.return_value.ensure_project_agents = AsyncMock(
                return_value={
                    "planner": {"id": str(uuid.uuid4()), "name": "planner", "config": {"project_role": "planner"}},
                    "coder": {"id": str(uuid.uuid4()), "name": "coder", "config": {"project_role": "coder"}},
                }
            )
            result = await mcp_server.analyze_project(
                project_path=None,
                project_name="From IDE",
                force_reindex=True,
            )

        self.assertEqual(result["analysis_status"], "completed")
        self.assertEqual(_FakeIndexer.last_index_kwargs["project_path"], "/tmp/ide-project")
        self.assertEqual(_FakeIndexer.last_index_kwargs["project_name"], "From IDE")
        self.assertTrue(_FakeIndexer.last_index_kwargs["force_reindex"])

        context = await mcp_server.context_get()
        self.assertEqual(context["context"]["project_path"], "/host-projects/autonomous-project")
        self.assertEqual(context["context"]["project_path_source"], "env")
        self.assertEqual(context["context"]["project_id"], result["project_id"])
        self.assertTrue(context["context"].get("agent_id"))
        self.assertEqual(result["brain_memory"]["stored"], 4)

    async def test_project_analyze_without_path_returns_error(self) -> None:
        with patch.object(mcp_server, "_auto_project_path_from_env", return_value=None):
            result = await mcp_server.analyze_project(project_path=None)
        self.assertIn("error", result)
        self.assertIn("AUTONOMOUS_PROJECT_ENV_KEYS", result["error"])

    async def test_project_graph_neighbors_autoselects_component_when_missing(self) -> None:
        project_id = str(uuid.uuid4())
        with (
            patch.object(
                mcp_server,
                "_get_session_factory",
                return_value=_FakeSessionFactoryWithComponent("cmp-1"),
            ),
            patch("app.dependencies.GraphDependencyService", _FakeGraphDependencyService),
        ):
            result = await mcp_server.project_graph_neighbors(
                project_id=project_id,
                depth=2,
            )

        self.assertEqual(result["component_id"], "cmp-1")
        self.assertEqual(_FakeGraphDependencyService.last_call["project_id"], project_id)
        self.assertEqual(_FakeGraphDependencyService.last_call["component_id"], "cmp-1")
        self.assertEqual(_FakeGraphDependencyService.last_call["depth"], 2)

        context = await mcp_server.context_get()
        self.assertEqual(context["context"]["component_id"], "cmp-1")

    async def test_project_graph_neighbors_without_components_returns_error(self) -> None:
        project_id = str(uuid.uuid4())
        with patch.object(
            mcp_server,
            "_get_session_factory",
            return_value=_FakeSessionFactoryWithComponent(None),
        ):
            result = await mcp_server.project_graph_neighbors(project_id=project_id, depth=2)

        self.assertIn("error", result)
        self.assertIn("no indexed components", result["error"])

    async def test_db_query_allows_information_schema(self) -> None:
        fake_db = _FakeDBSessionForQuery(
            columns=["table_name", "column_name"],
            rows=[],
        )
        with patch.object(
            mcp_server,
            "_get_session_factory",
            return_value=_FakeSessionFactoryForQuery(fake_db),
        ):
            result = await mcp_server.query_db(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' ORDER BY table_name",
                max_rows=5,
            )

        self.assertEqual(result["columns"], ["table_name", "column_name"])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["max_rows"], 5)
        self.assertIn("information_schema.columns", result["table_refs"])

    async def test_db_query_rejects_disallowed_schema(self) -> None:
        result = await mcp_server.query_db("SELECT * FROM private.secret")
        self.assertIn("error", result)
        self.assertIn("Table not allowed: private.secret", result["error"])

    async def test_db_query_can_be_disabled_by_config(self) -> None:
        with patch.object(
            mcp_server,
            "get_settings",
            return_value=types.SimpleNamespace(mcp_db_query_enabled=False),
        ):
            result = await mcp_server.query_db("SELECT 1")
        self.assertIn("error", result)
        self.assertIn("disabled", result["error"])

    async def test_agent_run_status_returns_payload(self) -> None:
        run_id = str(uuid.uuid4())
        fake_status = {"run_id": run_id, "status": "completed", "result": {"output": "ok"}}
        with (
            patch.object(mcp_server, "_get_session_factory", return_value=_FakeSessionFactory()),
            patch("app.mcp.server.AgentService") as mock_agent_service,
        ):
            mock_agent_service.return_value.get_run_status = AsyncMock(return_value=fake_status)
            result = await mcp_server.get_agent_run_status(run_id=run_id)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["run_id"], run_id)

    async def test_agent_run_background_queues_run(self) -> None:
        agent_id = str(uuid.uuid4())
        queued = {"run_id": str(uuid.uuid4()), "status": "pending", "queued": True}
        with (
            patch.object(mcp_server, "_get_session_factory", return_value=_FakeSessionFactory()),
            patch("app.mcp.server.AgentService") as mock_agent_service,
        ):
            mock_agent_service.return_value.enqueue_run = AsyncMock(return_value=queued)
            result = await mcp_server.run_agent(
                input="test task",
                agent_id=agent_id,
                background=True,
            )

        self.assertEqual(result["status"], "pending")
        self.assertTrue(result["queued"])

    async def test_agent_run_autoselects_project_planner_when_agent_missing(self) -> None:
        project_id = str(uuid.uuid4())
        planner_id = str(uuid.uuid4())
        queued = {"run_id": str(uuid.uuid4()), "status": "pending", "queued": True}
        await mcp_server.context_set(project_id=project_id)

        with (
            patch.object(mcp_server, "_get_session_factory", return_value=_FakeSessionFactory()),
            patch.object(mcp_server, "_resolve_project_name", new_callable=AsyncMock, return_value="Project X"),
            patch("app.mcp.server.AgentService") as mock_agent_service,
        ):
            mock_agent_service.return_value.ensure_project_agents = AsyncMock(
                return_value={
                    "planner": {"id": planner_id, "name": "project:planner"},
                    "coder": {"id": str(uuid.uuid4()), "name": "project:coder"},
                }
            )
            mock_agent_service.return_value.enqueue_run = AsyncMock(return_value=queued)
            result = await mcp_server.run_agent(
                input="project task",
                background=True,
            )

        self.assertEqual(result["status"], "pending")
        self.assertTrue(result.get("auto_selected_agent"))
        self.assertEqual(result["project_agents"]["planner"], planner_id)


if __name__ == "__main__":
    unittest.main()
