"""Background supervisor for autonomous project maintenance."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from sqlalchemy import select

from app.config.settings import get_settings
from app.core.models import Project
from app.db.session import _get_session_factory
from app.dependencies import GraphDependencyService
from app.indexing import ProjectIndexer
from app.memory.short_term import ShortTermMemory
from app.services.agent_service import AgentService
from app.services.memory_service import MemoryService
from app.services.project_memory import persist_project_memories

logger = logging.getLogger(__name__)

_MCP_CONTEXT_CACHE_KEY = "mcp:active:context"


class AutonomousProjectSupervisor:
    """Continuously maintains active project or rotates across known projects."""

    def __init__(self) -> None:
        settings = get_settings()
        self._interval_seconds = max(10, int(settings.autonomous_background_interval_seconds))
        self._project_limit = max(1, int(settings.autonomous_background_project_limit))
        self._project_cooldown_seconds = max(30, int(settings.autonomous_background_project_cooldown_seconds))
        self._task: asyncio.Task[Any] | None = None
        self._stop_event = asyncio.Event()
        self._last_processed_at: dict[str, float] = {}
        self._short_term = ShortTermMemory()

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._loop(), name="autonomous-project-supervisor")
        logger.info(
            "Autonomous supervisor started | interval=%ss | limit=%s | cooldown=%ss",
            self._interval_seconds,
            self._project_limit,
            self._project_cooldown_seconds,
        )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        await self._short_term.close()
        logger.info("Autonomous supervisor stopped")

    async def _loop(self) -> None:
        await asyncio.sleep(2)
        while not self._stop_event.is_set():
            started_at = time.monotonic()
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Autonomous supervisor tick failed")

            elapsed = max(0.0, time.monotonic() - started_at)
            sleep_seconds = max(1.0, self._interval_seconds - elapsed)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_seconds)
            except asyncio.TimeoutError:
                continue

    async def _tick(self) -> None:
        context = await self._short_term.cache_get(_MCP_CONTEXT_CACHE_KEY)
        active_project_id = None
        if isinstance(context, dict):
            raw_active = context.get("project_id")
            if raw_active is not None:
                active_project_id = str(raw_active).strip() or None

        if active_project_id:
            await self._process_project(active_project_id, source="active_context")
            return

        project_ids = await self._list_project_ids()
        for project_id in project_ids:
            await self._process_project(project_id, source="rotation")

    async def _list_project_ids(self) -> list[str]:
        factory = _get_session_factory()
        async with factory() as db:
            stmt = (
                select(Project.id)
                .where(Project.is_active.is_(True), Project.analysis_status == "completed")
                .order_by(Project.updated_at.desc())
                .limit(self._project_limit)
            )
            result = await db.execute(stmt)
            ids = result.scalars().all()
            return [str(project_id) for project_id in ids]

    async def _process_project(self, project_id: str, *, source: str) -> None:
        now = time.monotonic()
        last_seen = self._last_processed_at.get(project_id)
        if last_seen is not None and (now - last_seen) < self._project_cooldown_seconds:
            return

        factory = _get_session_factory()
        async with factory() as db:
            try:
                project_uuid = uuid.UUID(project_id)
            except (ValueError, TypeError):
                self._last_processed_at[project_id] = now
                return
            project = await db.get(Project, project_uuid)
            if project is None or not project.is_active:
                self._last_processed_at[project_id] = now
                return

            try:
                agent_service = AgentService(db, self._short_term)
                await agent_service.ensure_project_agents(
                    project_id=str(project.id),
                    project_name=project.name,
                )

                graph_service = GraphDependencyService(db)
                graph_result = await graph_service.sync_project_graph(str(project.id))

                indexer = ProjectIndexer(db)
                summary = await indexer.get_project_summary(str(project.id))
                memory_service = MemoryService(db, self._short_term)
                memory_result = await persist_project_memories(
                    memory_service,
                    summary,
                    project_id=str(project.id),
                    project_name=project.name,
                    project_path=project.path,
                )
                await db.commit()
                logger.info(
                    "Autonomous project maintenance complete | project=%s | source=%s | nodes=%s edges=%s | memory_created=%s",
                    project.id,
                    source,
                    graph_result.get("nodes"),
                    graph_result.get("edges"),
                    memory_result.get("created"),
                )
            except Exception as exc:
                await db.rollback()
                logger.warning(
                    "Autonomous project maintenance failed | project=%s | source=%s | error=%s",
                    project.id,
                    source,
                    exc,
                )
            finally:
                self._last_processed_at[project_id] = now
