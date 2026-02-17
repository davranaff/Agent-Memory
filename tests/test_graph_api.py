from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.projects import router as projects_router
from app.api.projects import _get_graph_dependency_service


class _FakeGraphService:
    async def dependencies_analyze_compat(self, project_id: str, include_impact_analysis: bool, component_id: str | None):
        return {
            "graph_statistics": {"total_nodes": 1, "total_edges": 0},
            "nodes": 1,
            "edges": 0,
            "cycles_detected": 0,
            "strongly_connected_components": 1,
            "layers": {"count": 1, "layer_assignments": {}},
        }

    async def sync_project_graph(self, project_id: str, changed_files: list[str] | None = None):
        mode = "incremental" if changed_files else "full"
        return {
            "project_id": project_id,
            "backend": "inmemory",
            "mode": mode,
            "changed_files_count": len(changed_files or []),
            "nodes": 1,
            "edges": 0,
        }

    async def graph_impact(self, project_id: str, component_id: str):
        return {
            "component_id": component_id,
            "component_name": "Comp",
            "direct_impact": 1,
            "indirect_impact": 0,
            "total_impact": 1,
            "affected_components": ["x"],
            "critical_paths": [],
            "is_critical": False,
        }

    async def graph_path(self, project_id: str, from_component_id: str, to_component_id: str, max_depth: int = 15):
        return {
            "project_id": project_id,
            "from_component_id": from_component_id,
            "to_component_id": to_component_id,
            "max_depth": max_depth,
            "path": [from_component_id, to_component_id],
            "path_found": True,
            "path_length": 2,
        }

    async def graph_neighbors(self, project_id: str, component_id: str, depth: int = 1):
        return {
            "component_id": component_id,
            "component_name": "Comp",
            "depth": depth,
            "levels": [{"depth": 1, "component_ids": ["n1"], "count": 1}],
            "total_neighbors": 1,
        }


class GraphApiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(projects_router)
        app.dependency_overrides[_get_graph_dependency_service] = lambda: _FakeGraphService()
        self.client = TestClient(app)

    def test_dependencies_analyze(self) -> None:
        resp = self.client.post(
            "/projects/dependencies/analyze",
            json={"project_id": "p1", "include_impact_analysis": False},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("graph_statistics", data)

    def test_dependencies_sync(self) -> None:
        resp = self.client.post("/projects/dependencies/sync", json={"project_id": "p1"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["project_id"], "p1")

    def test_dependencies_sync_incremental(self) -> None:
        resp = self.client.post(
            "/projects/dependencies/sync",
            json={"project_id": "p1", "changed_files": ["app/main.py"]},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["mode"], "incremental")
        self.assertEqual(resp.json()["changed_files_count"], 1)

    def test_graph_impact(self) -> None:
        resp = self.client.get("/projects/p1/graph/impact", params={"component_id": "c1"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["component_id"], "c1")

    def test_graph_path(self) -> None:
        resp = self.client.get(
            "/projects/p1/graph/path",
            params={"from_component_id": "a", "to_component_id": "b"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["path_found"])

    def test_graph_neighbors(self) -> None:
        resp = self.client.get(
            "/projects/p1/graph/neighbors",
            params={"component_id": "c1", "depth": 2},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["depth"], 2)


if __name__ == "__main__":
    unittest.main()
