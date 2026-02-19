from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.projects as projects_api
from app.api.projects import router as projects_router


class _FakeDB:
    async def commit(self):
        return None

    async def rollback(self):
        return None


class _FakeProject:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.name = "API Project"
        self.path = "/tmp/api-project"
        self.analysis_status = "completed"
        self.last_analyzed = datetime.now(timezone.utc)
        self.total_files = 3
        self.total_lines = 100
        self.architecture_type = "layered"
        self.tech_stack = ["python"]
        self.frameworks = ["fastapi"]
        self.languages = ["python"]
        self.databases = ["postgresql"]
        self.build_tools = ["docker"]


class _FakeComponent:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.name = "paths"
        self.type = "file"
        self.relative_path = "app/paths.py"
        self.language = "python"
        self.line_count = 42
        self.complexity_score = 2
        self.dependencies = ["pathlib"]
        self.exports = []


class _FakeIndexer:
    last_index_args: dict | None = None
    last_search_args: dict | None = None

    def __init__(self, _db) -> None:
        self._project = _FakeProject()

    async def index_project(self, project_path: str, project_name: str | None, force_reindex: bool):
        _FakeIndexer.last_index_args = {
            "project_path": project_path,
            "project_name": project_name,
            "force_reindex": force_reindex,
        }
        return self._project

    async def get_project_summary(self, project_id: str):
        return {"project_id": project_id, "ok": True}

    async def search_components(
        self,
        project_id: str,
        query: str,
        component_type: str | None = None,
        language: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        _FakeIndexer.last_search_args = {
            "project_id": project_id,
            "query": query,
            "component_type": component_type,
            "language": language,
            "limit": limit,
            "offset": offset,
        }
        return [_FakeComponent()]


class ProjectsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(projects_router)
        app.dependency_overrides[projects_api.get_db] = lambda: _FakeDB()
        self.client = TestClient(app)

    def test_analyze_project_endpoint(self) -> None:
        mocked_brain_memory = {
            "stored": 4,
            "created": 4,
            "deduplicated": 0,
            "memory_ids": ["m1", "m2", "m3", "m4"],
        }
        with (
            patch("app.api.projects.ProjectIndexer", _FakeIndexer),
            patch("app.api.projects.MemoryService", return_value=object()),
            patch("app.api.projects.persist_project_memories", new_callable=AsyncMock, return_value=mocked_brain_memory),
        ):
            response = self.client.post(
                "/projects/analyze",
                json={
                    "project_path": "/tmp/repo",
                    "project_name": "Repo",
                    "force_reindex": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["project_name"], "API Project")
        self.assertEqual(data["analysis_status"], "completed")
        self.assertTrue(_FakeIndexer.last_index_args["force_reindex"])
        self.assertEqual(_FakeIndexer.last_index_args["project_path"], "/tmp/repo")
        self.assertEqual(data["metadata"]["brain_memory"]["stored"], 4)

    def test_get_project_components_default_query(self) -> None:
        with patch("app.api.projects.ProjectIndexer", _FakeIndexer):
            response = self.client.get("/projects/p1/components?limit=1&offset=0")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(_FakeIndexer.last_search_args["project_id"], "p1")
        self.assertEqual(_FakeIndexer.last_search_args["query"], "")
        self.assertEqual(_FakeIndexer.last_search_args["limit"], 1)

    def test_get_project_components_query_passthrough(self) -> None:
        with patch("app.api.projects.ProjectIndexer", _FakeIndexer):
            response = self.client.get(
                "/projects/p1/components?query=paths&component_type=file&language=python&limit=5&offset=2"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(_FakeIndexer.last_search_args["query"], "paths")
        self.assertEqual(_FakeIndexer.last_search_args["component_type"], "file")
        self.assertEqual(_FakeIndexer.last_search_args["language"], "python")
        self.assertEqual(_FakeIndexer.last_search_args["limit"], 5)
        self.assertEqual(_FakeIndexer.last_search_args["offset"], 2)


if __name__ == "__main__":
    unittest.main()
