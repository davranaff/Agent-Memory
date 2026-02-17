"""Dependency graph service backed by configurable graph store."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.dependencies.builder import DependencyGraphBuilder
from app.dependencies.runtime import get_graph_store
from app.dependencies.store import ImpactResult

logger = logging.getLogger(__name__)


class GraphDependencyService:
    """High-level graph operations for dependency analysis endpoints."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._builder = DependencyGraphBuilder(db)

    async def sync_project_graph(
        self,
        project_id: str,
        changed_files: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build and persist project graph into configured graph backend."""
        store = await get_graph_store()
        changed_files = changed_files or []

        mode = "full"
        graph = await self._builder.build_graph(project_id)

        if changed_files:
            mode = "incremental"
            inc_graph, changed_component_ids, normalized_paths = (
                await self._builder.build_incremental_graph(project_id, changed_files)
            )
            graph = inc_graph
            try:
                await store.sync_project_graph_incremental(
                    project_id=project_id,
                    graph=inc_graph,
                    changed_component_ids=changed_component_ids,
                    changed_paths=normalized_paths,
                )
            except (NotImplementedError, ValueError) as e:
                logger.info("Incremental sync fallback to full sync for project %s: %s", project_id, e)
                mode = "full_fallback"
                graph = await self._builder.build_graph(project_id)
                await store.sync_project_graph(project_id, graph)
            except Exception:
                # For backend errors we still attempt a full replacement to keep state consistent.
                logger.exception(
                    "Incremental sync failed unexpectedly for project %s. Falling back to full sync.",
                    project_id,
                )
                mode = "full_fallback"
                graph = await self._builder.build_graph(project_id)
                await store.sync_project_graph(project_id, graph)
        else:
            await store.sync_project_graph(project_id, graph)

        return {
            "project_id": project_id,
            "backend": get_settings().graph_backend,
            "mode": mode,
            "changed_files_count": len(changed_files),
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    async def dependencies_analyze_compat(
        self,
        project_id: str,
        include_impact_analysis: bool,
        component_id: str | None,
    ) -> dict[str, Any]:
        """Compatibility output for existing /dependencies/analyze endpoint."""
        graph = await self._builder.build_graph(project_id)
        stats = graph.get_statistics()

        result: dict[str, Any] = {
            "graph_statistics": stats,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "cycles_detected": len(stats.get("cycles", [])),
            "strongly_connected_components": stats.get(
                "strongly_connected_components_count", 0
            ),
        }

        if include_impact_analysis and component_id:
            result["impact_analysis"] = await self._builder.analyze_impact(
                project_id, component_id
            )

        _, layers = await self._builder.build_layered_graph(project_id)
        result["layers"] = {
            "count": len(layers),
            "layer_assignments": layers,
        }

        # Keep graph backend warm for downstream graph endpoints.
        try:
            store = await get_graph_store()
            await store.sync_project_graph(project_id, graph)
        except Exception as e:
            logger.warning("Failed to sync graph backend from analyze endpoint: %s", e)

        return result

    async def graph_impact(self, project_id: str, component_id: str) -> dict[str, Any]:
        store = await get_graph_store()
        impact: ImpactResult = await store.analyze_impact(project_id, component_id)
        return {
            "component_id": impact.component_id,
            "component_name": impact.component_name,
            "direct_impact": impact.direct_impact,
            "indirect_impact": impact.indirect_impact,
            "total_impact": impact.total_impact,
            "affected_components": impact.affected_components,
            "critical_paths": impact.critical_paths,
            "is_critical": impact.is_critical,
        }

    async def graph_path(
        self,
        project_id: str,
        from_component_id: str,
        to_component_id: str,
        max_depth: int = 15,
    ) -> dict[str, Any]:
        store = await get_graph_store()
        path = await store.find_path(
            project_id,
            from_component_id,
            to_component_id,
            max_depth=max_depth,
        )
        return {
            "project_id": project_id,
            "from_component_id": from_component_id,
            "to_component_id": to_component_id,
            "max_depth": max_depth,
            "path": path,
            "path_found": path is not None,
            "path_length": len(path) if path else 0,
        }

    async def graph_neighbors(
        self,
        project_id: str,
        component_id: str,
        depth: int = 1,
    ) -> dict[str, Any]:
        store = await get_graph_store()
        return await store.get_neighbors(project_id, component_id, depth=depth)
