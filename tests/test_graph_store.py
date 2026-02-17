from __future__ import annotations

import unittest

from app.dependencies.graph import (
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    DependencyType,
    NodeType,
)
from app.dependencies.store import GraphStore, InMemoryGraphStore, ResilientGraphStore


class _FailingStore(GraphStore):
    async def sync_project_graph(self, project_id: str, graph: DependencyGraph) -> None:
        raise RuntimeError("primary unavailable")

    async def get_graph_statistics(self, project_id: str):
        raise RuntimeError("primary unavailable")

    async def analyze_impact(self, project_id: str, component_id: str):
        raise RuntimeError("primary unavailable")

    async def find_path(self, project_id: str, from_component_id: str, to_component_id: str, max_depth: int = 15):
        raise RuntimeError("primary unavailable")

    async def get_neighbors(self, project_id: str, component_id: str, depth: int = 1):
        raise RuntimeError("primary unavailable")

    async def close(self) -> None:
        return None


class InMemoryGraphStoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.graph = DependencyGraph()
        self.graph.add_node(
            DependencyNode(id="a", name="A", type=NodeType.FILE, path="a.py", language="python")
        )
        self.graph.add_node(
            DependencyNode(id="b", name="B", type=NodeType.FILE, path="b.py", language="python")
        )
        self.graph.add_node(
            DependencyNode(id="c", name="C", type=NodeType.FILE, path="c.py", language="python")
        )

        self.graph.add_edge(
            DependencyEdge(source_id="a", target_id="b", type=DependencyType.IMPORT)
        )
        self.graph.add_edge(
            DependencyEdge(source_id="b", target_id="c", type=DependencyType.IMPORT)
        )

        self.store = InMemoryGraphStore()
        await self.store.sync_project_graph("p1", self.graph)

    async def test_statistics(self) -> None:
        stats = await self.store.get_graph_statistics("p1")
        self.assertEqual(stats["total_nodes"], 3)
        self.assertEqual(stats["total_edges"], 2)

    async def test_impact(self) -> None:
        impact = await self.store.analyze_impact("p1", "c")
        self.assertEqual(impact.direct_impact, 1)
        self.assertEqual(impact.total_impact, 2)
        self.assertIn("a", impact.affected_components)
        self.assertIn("b", impact.affected_components)

    async def test_path(self) -> None:
        path = await self.store.find_path("p1", "a", "c")
        self.assertEqual(path, ["a", "b", "c"])

    async def test_neighbors(self) -> None:
        neighbors = await self.store.get_neighbors("p1", "b", depth=2)
        self.assertEqual(neighbors["component_id"], "b")
        self.assertGreaterEqual(neighbors["total_neighbors"], 2)

    async def test_incremental_sync_replaces_changed_component_edges(self) -> None:
        incremental = DependencyGraph()
        incremental.add_node(
            DependencyNode(id="b", name="B2", type=NodeType.FILE, path="b.py", language="python")
        )
        incremental.add_edge(
            DependencyEdge(source_id="b", target_id="a", type=DependencyType.IMPORT)
        )

        await self.store.sync_project_graph_incremental(
            project_id="p1",
            graph=incremental,
            changed_component_ids={"b"},
            changed_paths=["b.py"],
        )

        stats = await self.store.get_graph_statistics("p1")
        self.assertEqual(stats["total_nodes"], 3)
        self.assertEqual(stats["total_edges"], 1)
        self.assertEqual((await self.store.find_path("p1", "b", "a")), ["b", "a"])
        self.assertIsNone(await self.store.find_path("p1", "a", "b"))
        self.assertIsNone(await self.store.find_path("p1", "b", "c"))

    async def test_incremental_sync_removes_deleted_file_node_by_path(self) -> None:
        incremental = DependencyGraph()
        await self.store.sync_project_graph_incremental(
            project_id="p1",
            graph=incremental,
            changed_component_ids=set(),
            changed_paths=["c.py"],
        )

        stats = await self.store.get_graph_statistics("p1")
        self.assertEqual(stats["total_nodes"], 2)
        self.assertEqual(stats["total_edges"], 1)
        self.assertIsNone(await self.store.find_path("p1", "a", "c"))


class ResilientStoreFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_fallback_to_inmemory(self) -> None:
        graph = DependencyGraph()
        graph.add_node(
            DependencyNode(id="x", name="X", type=NodeType.FILE, path="x.py", language="python")
        )
        graph.add_node(
            DependencyNode(id="y", name="Y", type=NodeType.FILE, path="y.py", language="python")
        )
        graph.add_edge(
            DependencyEdge(source_id="x", target_id="y", type=DependencyType.IMPORT)
        )

        fallback = InMemoryGraphStore()
        store = ResilientGraphStore(_FailingStore(), fallback, fallback_enabled=True)

        await store.sync_project_graph("p2", graph)
        stats = await store.get_graph_statistics("p2")

        self.assertEqual(stats["total_nodes"], 2)
        self.assertEqual(stats["total_edges"], 1)


if __name__ == "__main__":
    unittest.main()
