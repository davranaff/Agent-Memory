"""Graph storage backends for project dependency graphs.

This module provides an adapter layer so the project can use either an
in-memory graph store or Neo4j as a graph read-model backend.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass
from typing import Any

from app.dependencies.graph import DependencyEdge, DependencyGraph, DependencyNode

logger = logging.getLogger(__name__)


@dataclass
class ImpactResult:
    """Impact analysis result for a component in a project graph."""

    component_id: str
    component_name: str
    direct_impact: int
    indirect_impact: int
    total_impact: int
    affected_components: list[str]
    critical_paths: list[list[str]]
    is_critical: bool


class GraphStore(abc.ABC):
    """Abstract graph store backend."""

    @abc.abstractmethod
    async def sync_project_graph(self, project_id: str, graph: DependencyGraph) -> None:
        """Persist the full project graph as an idempotent replacement."""

    async def sync_project_graph_incremental(
        self,
        project_id: str,
        graph: DependencyGraph,
        changed_component_ids: set[str],
        changed_paths: list[str],
    ) -> None:
        """Persist an incremental graph update for changed project components."""
        raise NotImplementedError("Incremental graph sync is not supported by this backend")

    @abc.abstractmethod
    async def get_graph_statistics(self, project_id: str) -> dict[str, Any]:
        """Return aggregate graph statistics for a project."""

    @abc.abstractmethod
    async def analyze_impact(self, project_id: str, component_id: str) -> ImpactResult:
        """Analyze dependency impact for a specific component."""

    @abc.abstractmethod
    async def find_path(
        self,
        project_id: str,
        from_component_id: str,
        to_component_id: str,
        max_depth: int = 15,
    ) -> list[str] | None:
        """Find one path from component A to component B."""

    @abc.abstractmethod
    async def get_neighbors(
        self,
        project_id: str,
        component_id: str,
        depth: int = 1,
    ) -> dict[str, Any]:
        """Return neighbors around a component up to the given depth."""

    @abc.abstractmethod
    async def close(self) -> None:
        """Release backend resources."""


def _normalize_path(value: str | None) -> str:
    if not value:
        return ""
    normalized = str(value).replace("\\", "/").strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    while normalized.startswith("/"):
        normalized = normalized[1:]
    return normalized


def _path_matches_any(path_value: str | None, changed_paths: list[str]) -> bool:
    normalized = _normalize_path(path_value)
    if not normalized:
        return False

    for changed in changed_paths:
        changed_norm = _normalize_path(changed)
        if (
            normalized == changed_norm
            or normalized.endswith(f"/{changed_norm}")
            or changed_norm.endswith(f"/{normalized}")
        ):
            return True
    return False


class InMemoryGraphStore(GraphStore):
    """In-memory graph backend keyed by project_id."""

    def __init__(self) -> None:
        self._project_graphs: dict[str, DependencyGraph] = {}

    async def sync_project_graph(self, project_id: str, graph: DependencyGraph) -> None:
        self._project_graphs[project_id] = graph

    async def sync_project_graph_incremental(
        self,
        project_id: str,
        graph: DependencyGraph,
        changed_component_ids: set[str],
        changed_paths: list[str],
    ) -> None:
        existing = self._project_graphs.get(project_id)
        if existing is None:
            raise ValueError(
                f"Graph for project {project_id} not found. Run full dependencies sync first."
            )

        ids_to_remove = set(changed_component_ids)
        for node in list(existing.nodes.values()):
            if _path_matches_any(node.path, changed_paths):
                ids_to_remove.add(node.id)

        for node_id in ids_to_remove:
            existing.remove_node(node_id)

        for node in graph.nodes.values():
            existing.add_node(node)

        for edge in graph.edges.values():
            if edge.source_id in existing.nodes and edge.target_id in existing.nodes:
                existing.add_edge(edge)

    def _get_graph_or_raise(self, project_id: str) -> DependencyGraph:
        graph = self._project_graphs.get(project_id)
        if graph is None:
            raise ValueError(
                f"Graph for project {project_id} not found. Run dependencies sync first."
            )
        return graph

    async def get_graph_statistics(self, project_id: str) -> dict[str, Any]:
        graph = self._get_graph_or_raise(project_id)
        return graph.get_statistics()

    async def analyze_impact(self, project_id: str, component_id: str) -> ImpactResult:
        graph = self._get_graph_or_raise(project_id)
        node = graph.get_node(component_id)
        if node is None:
            raise ValueError(f"Component {component_id} not found in graph")

        dependents = graph.get_dependents(component_id)
        direct_impact = len(dependents)

        affected: set[str] = set()
        queue = [dep.id for dep in dependents]
        while queue:
            current = queue.pop(0)
            if current in affected:
                continue
            affected.add(current)
            queue.extend(dep.id for dep in graph.get_dependents(current))

        indirect_impact = max(len(affected) - direct_impact, 0)
        critical_paths: list[list[str]] = []
        for dep in dependents:
            path = graph.find_path(dep.id, component_id)
            if path:
                critical_paths.append(path)

        return ImpactResult(
            component_id=component_id,
            component_name=node.name,
            direct_impact=direct_impact,
            indirect_impact=indirect_impact,
            total_impact=len(affected),
            affected_components=sorted(affected),
            critical_paths=critical_paths[:20],
            is_critical=direct_impact > 5 or len(affected) > 20,
        )

    async def find_path(
        self,
        project_id: str,
        from_component_id: str,
        to_component_id: str,
        max_depth: int = 15,
    ) -> list[str] | None:
        graph = self._get_graph_or_raise(project_id)
        if max_depth < 1:
            max_depth = 1

        if from_component_id not in graph.nodes or to_component_id not in graph.nodes:
            return None

        from collections import deque

        queue = deque([(from_component_id, [from_component_id])])
        visited = {from_component_id}
        while queue:
            current, path = queue.popleft()
            if current == to_component_id:
                return path
            if len(path) > max_depth:
                continue
            for neighbor in graph._adjacency_list.get(current, set()):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append((neighbor, [*path, neighbor]))
        return None

    async def get_neighbors(
        self,
        project_id: str,
        component_id: str,
        depth: int = 1,
    ) -> dict[str, Any]:
        graph = self._get_graph_or_raise(project_id)
        node = graph.get_node(component_id)
        if node is None:
            raise ValueError(f"Component {component_id} not found in graph")

        if depth < 1:
            depth = 1
        if depth > 6:
            depth = 6

        visited = {component_id}
        frontier = {component_id}
        levels: list[dict[str, Any]] = []

        for level in range(1, depth + 1):
            next_frontier: set[str] = set()
            for nid in frontier:
                outgoing = graph._adjacency_list.get(nid, set())
                incoming = graph._reverse_adjacency_list.get(nid, set())
                for rel_id in outgoing | incoming:
                    if rel_id in visited:
                        continue
                    visited.add(rel_id)
                    next_frontier.add(rel_id)

            levels.append(
                {
                    "depth": level,
                    "component_ids": sorted(next_frontier),
                    "count": len(next_frontier),
                }
            )
            frontier = next_frontier
            if not frontier:
                break

        return {
            "component_id": component_id,
            "component_name": node.name,
            "depth": depth,
            "levels": levels,
            "total_neighbors": len(visited) - 1,
        }

    async def close(self) -> None:
        self._project_graphs.clear()


class Neo4jGraphStore(GraphStore):
    """Neo4j graph backend."""

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
    ) -> None:
        try:
            from neo4j import AsyncGraphDatabase
        except Exception as e:  # pragma: no cover - import environment specific
            raise RuntimeError(
                "neo4j package is not installed. Install it to use GRAPH_BACKEND=neo4j."
            ) from e

        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self._database = database

    async def _run_write(self, query: str, params: dict[str, Any] | None = None) -> None:
        async with self._driver.session(database=self._database) as session:
            await session.run(query, params or {})

    async def _run_read(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ):
        async with self._driver.session(database=self._database) as session:
            result = await session.run(query, params or {})
            return await result.data()

    async def verify_connectivity(self) -> None:
        await self._driver.verify_connectivity()

    async def sync_project_graph(self, project_id: str, graph: DependencyGraph) -> None:
        await self._run_write(
            """
            MERGE (p:Project {id: $project_id})
            SET p.updated_at = datetime()
            """,
            {"project_id": project_id},
        )

        # Replace project component subgraph idempotently.
        await self._run_write(
            """
            MATCH (p:Project {id: $project_id})-[:HAS_COMPONENT]->(c:Component)
            DETACH DELETE c
            """,
            {"project_id": project_id},
        )

        async with self._driver.session(database=self._database) as session:
            for node in graph.nodes.values():
                await session.run(
                    """
                    MATCH (p:Project {id: $project_id})
                    MERGE (c:Component {id: $component_id})
                    SET
                      c.name = $name,
                      c.type = $type,
                      c.path = $path,
                      c.language = $language,
                      c.metadata = $metadata,
                      c.lines_of_code = $lines_of_code,
                      c.complexity_score = $complexity_score,
                      c.is_entry_point = $is_entry_point,
                      c.is_utility = $is_utility,
                      c.is_test = $is_test,
                      c.is_generated = $is_generated
                    MERGE (p)-[:HAS_COMPONENT]->(c)
                    """,
                    {
                        "project_id": project_id,
                        "component_id": node.id,
                        "name": node.name,
                        "type": node.type.value,
                        "path": node.path,
                        "language": node.language,
                        "metadata": node.metadata,
                        "lines_of_code": node.lines_of_code,
                        "complexity_score": node.complexity_score,
                        "is_entry_point": node.is_entry_point,
                        "is_utility": node.is_utility,
                        "is_test": node.is_test,
                        "is_generated": node.is_generated,
                    },
                )

    async def sync_project_graph_incremental(
        self,
        project_id: str,
        graph: DependencyGraph,
        changed_component_ids: set[str],
        changed_paths: list[str],
    ) -> None:
        await self._run_write(
            """
            MERGE (p:Project {id: $project_id})
            SET p.updated_at = datetime()
            """,
            {"project_id": project_id},
        )

        await self._run_write(
            """
            MATCH (p:Project {id: $project_id})-[:HAS_COMPONENT]->(c:Component)
            WHERE c.id IN $changed_component_ids
               OR ANY(cp IN $changed_paths
                      WHERE c.path = cp
                         OR c.path ENDS WITH '/' + cp
                         OR cp ENDS WITH '/' + c.path)
            DETACH DELETE c
            """,
            {
                "project_id": project_id,
                "changed_component_ids": list(changed_component_ids),
                "changed_paths": [
                    normalized_path
                    for normalized_path in (_normalize_path(p) for p in changed_paths)
                    if normalized_path
                ],
            },
        )

        async with self._driver.session(database=self._database) as session:
            for node in graph.nodes.values():
                await session.run(
                    """
                    MATCH (p:Project {id: $project_id})
                    MERGE (c:Component {id: $component_id})
                    SET
                      c.name = $name,
                      c.type = $type,
                      c.path = $path,
                      c.language = $language,
                      c.metadata = $metadata,
                      c.lines_of_code = $lines_of_code,
                      c.complexity_score = $complexity_score,
                      c.is_entry_point = $is_entry_point,
                      c.is_utility = $is_utility,
                      c.is_test = $is_test,
                      c.is_generated = $is_generated
                    MERGE (p)-[:HAS_COMPONENT]->(c)
                    """,
                    {
                        "project_id": project_id,
                        "component_id": node.id,
                        "name": node.name,
                        "type": node.type.value,
                        "path": node.path,
                        "language": node.language,
                        "metadata": node.metadata,
                        "lines_of_code": node.lines_of_code,
                        "complexity_score": node.complexity_score,
                        "is_entry_point": node.is_entry_point,
                        "is_utility": node.is_utility,
                        "is_test": node.is_test,
                        "is_generated": node.is_generated,
                    },
                )

            for edge in graph.edges.values():
                await session.run(
                    """
                    MATCH (src:Component {id: $source_id})
                    MATCH (dst:Component {id: $target_id})
                    MERGE (src)-[r:DEPENDS_ON {project_id: $project_id, edge_type: $edge_type}]->(dst)
                    SET
                      r.weight = $weight,
                      r.metadata = $metadata,
                      r.updated_at = datetime()
                    """,
                    {
                        "project_id": project_id,
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "edge_type": edge.type.value,
                        "weight": edge.weight,
                        "metadata": edge.metadata,
                    },
                )

            for edge in graph.edges.values():
                await session.run(
                    """
                    MATCH (src:Component {id: $source_id})
                    MATCH (dst:Component {id: $target_id})
                    MERGE (src)-[r:DEPENDS_ON {project_id: $project_id, edge_type: $edge_type}]->(dst)
                    SET
                      r.weight = $weight,
                      r.metadata = $metadata,
                      r.updated_at = datetime()
                    """,
                    {
                        "project_id": project_id,
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "edge_type": edge.type.value,
                        "weight": edge.weight,
                        "metadata": edge.metadata,
                    },
                )

    async def get_graph_statistics(self, project_id: str) -> dict[str, Any]:
        rows = await self._run_read(
            """
            MATCH (p:Project {id: $project_id})-[:HAS_COMPONENT]->(c:Component)
            OPTIONAL MATCH (c)-[r:DEPENDS_ON {project_id: $project_id}]->()
            RETURN count(DISTINCT c) AS total_nodes, count(r) AS total_edges
            """,
            {"project_id": project_id},
        )
        if not rows:
            return {"total_nodes": 0, "total_edges": 0}
        return {
            "total_nodes": rows[0]["total_nodes"],
            "total_edges": rows[0]["total_edges"],
        }

    async def analyze_impact(self, project_id: str, component_id: str) -> ImpactResult:
        rows = await self._run_read(
            """
            MATCH (c:Component {id: $component_id})<-[:HAS_COMPONENT]-(:Project {id: $project_id})
            OPTIONAL MATCH (c)<-[:DEPENDS_ON {project_id: $project_id}]-(d:Component)
            WITH c, collect(DISTINCT d.id) AS direct_ids
            OPTIONAL MATCH p=(c)<-[:DEPENDS_ON*1..]-(a:Component)
            WHERE ALL(rel IN relationships(p) WHERE rel.project_id = $project_id)
            WITH c, direct_ids, collect(DISTINCT a.id) AS all_ids
            RETURN c.name AS component_name, direct_ids, all_ids
            """,
            {"project_id": project_id, "component_id": component_id},
        )
        if not rows:
            raise ValueError(f"Component {component_id} not found in graph")

        component_name = rows[0]["component_name"]
        direct_ids = sorted([i for i in rows[0]["direct_ids"] if i])
        all_ids = sorted([i for i in rows[0]["all_ids"] if i])

        direct_count = len(direct_ids)
        total_count = len(all_ids)

        return ImpactResult(
            component_id=component_id,
            component_name=component_name,
            direct_impact=direct_count,
            indirect_impact=max(total_count - direct_count, 0),
            total_impact=total_count,
            affected_components=all_ids,
            critical_paths=[],
            is_critical=direct_count > 5 or total_count > 20,
        )

    async def find_path(
        self,
        project_id: str,
        from_component_id: str,
        to_component_id: str,
        max_depth: int = 15,
    ) -> list[str] | None:
        if max_depth < 1:
            max_depth = 1
        if max_depth > 30:
            max_depth = 30

        rows = await self._run_read(
            """
            MATCH (src:Component {id: $from_component_id})<-[:HAS_COMPONENT]-(:Project {id: $project_id})
            MATCH (dst:Component {id: $to_component_id})<-[:HAS_COMPONENT]-(:Project {id: $project_id})
            MATCH p = shortestPath((src)-[:DEPENDS_ON*1..30]->(dst))
            WHERE length(p) <= $max_depth
              AND ALL(rel IN relationships(p) WHERE rel.project_id = $project_id)
            RETURN [n IN nodes(p) | n.id] AS path_ids
            LIMIT 1
            """,
            {
                "project_id": project_id,
                "from_component_id": from_component_id,
                "to_component_id": to_component_id,
                "max_depth": max_depth,
            },
        )
        if not rows:
            return None
        return rows[0]["path_ids"]

    async def get_neighbors(
        self,
        project_id: str,
        component_id: str,
        depth: int = 1,
    ) -> dict[str, Any]:
        if depth < 1:
            depth = 1
        if depth > 6:
            depth = 6

        rows = await self._run_read(
            """
            MATCH (c:Component {id: $component_id})<-[:HAS_COMPONENT]-(:Project {id: $project_id})
            OPTIONAL MATCH p=(c)-[:DEPENDS_ON*1..6]-(n:Component)
            WHERE ALL(rel IN relationships(p) WHERE rel.project_id = $project_id)
            WITH c, collect(DISTINCT n.id) AS ids
            RETURN c.name AS component_name, ids
            """,
            {
                "project_id": project_id,
                "component_id": component_id,
            },
        )
        if not rows:
            raise ValueError(f"Component {component_id} not found in graph")

        ids = sorted([i for i in rows[0]["ids"] if i and i != component_id])
        return {
            "component_id": component_id,
            "component_name": rows[0]["component_name"],
            "depth": depth,
            "levels": [],
            "neighbor_component_ids": ids,
            "total_neighbors": len(ids),
        }

    async def close(self) -> None:
        await self._driver.close()


class ResilientGraphStore(GraphStore):
    """Wrapper that falls back to in-memory backend when primary fails."""

    def __init__(
        self,
        primary: GraphStore,
        fallback: InMemoryGraphStore,
        fallback_enabled: bool = True,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._fallback_enabled = fallback_enabled

    async def sync_project_graph(self, project_id: str, graph: DependencyGraph) -> None:
        # Keep fallback warm for fast failover.
        await self._fallback.sync_project_graph(project_id, graph)
        try:
            await self._primary.sync_project_graph(project_id, graph)
        except Exception as e:
            if not self._fallback_enabled:
                raise
            logger.warning("Primary graph backend sync failed, using fallback: %s", e)

    async def sync_project_graph_incremental(
        self,
        project_id: str,
        graph: DependencyGraph,
        changed_component_ids: set[str],
        changed_paths: list[str],
    ) -> None:
        await self._fallback.sync_project_graph_incremental(
            project_id,
            graph,
            changed_component_ids,
            changed_paths,
        )
        try:
            await self._primary.sync_project_graph_incremental(
                project_id,
                graph,
                changed_component_ids,
                changed_paths,
            )
        except Exception as e:
            if not self._fallback_enabled:
                raise
            logger.warning("Primary incremental sync failed, using fallback: %s", e)

    async def get_graph_statistics(self, project_id: str) -> dict[str, Any]:
        try:
            return await self._primary.get_graph_statistics(project_id)
        except Exception as e:
            if not self._fallback_enabled:
                raise
            logger.warning("Primary graph backend stats failed, using fallback: %s", e)
            return await self._fallback.get_graph_statistics(project_id)

    async def analyze_impact(self, project_id: str, component_id: str) -> ImpactResult:
        try:
            return await self._primary.analyze_impact(project_id, component_id)
        except Exception as e:
            if not self._fallback_enabled:
                raise
            logger.warning("Primary graph backend impact failed, using fallback: %s", e)
            return await self._fallback.analyze_impact(project_id, component_id)

    async def find_path(
        self,
        project_id: str,
        from_component_id: str,
        to_component_id: str,
        max_depth: int = 15,
    ) -> list[str] | None:
        try:
            return await self._primary.find_path(
                project_id,
                from_component_id,
                to_component_id,
                max_depth=max_depth,
            )
        except Exception as e:
            if not self._fallback_enabled:
                raise
            logger.warning("Primary graph backend path failed, using fallback: %s", e)
            return await self._fallback.find_path(
                project_id,
                from_component_id,
                to_component_id,
                max_depth=max_depth,
            )

    async def get_neighbors(
        self,
        project_id: str,
        component_id: str,
        depth: int = 1,
    ) -> dict[str, Any]:
        try:
            return await self._primary.get_neighbors(project_id, component_id, depth=depth)
        except Exception as e:
            if not self._fallback_enabled:
                raise
            logger.warning("Primary graph backend neighbors failed, using fallback: %s", e)
            return await self._fallback.get_neighbors(project_id, component_id, depth=depth)

    async def close(self) -> None:
        try:
            await self._primary.close()
        finally:
            await self._fallback.close()
