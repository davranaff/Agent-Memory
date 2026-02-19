"""Orchestration service — high-level orchestration operations."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.prompts import get_default_system_prompt
from app.config.settings import get_settings
from app.db.session import _get_session_factory
from app.memory.short_term import ShortTermMemory
from app.orchestration.models import OrchestrationRun, OrchestrationStep
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.registry import AgentRegistry
from app.orchestration.router import AgentRouter
from app.orchestration.workflows import get_workflow, list_workflows
from app.services.agent_service import AgentService

logger = logging.getLogger(__name__)
_BACKGROUND_RUN_TASKS: dict[str, asyncio.Task[Any]] = {}


def _track_background_task(run_id: uuid.UUID, task: asyncio.Task[Any]) -> None:
    """Track background tasks to avoid accidental garbage collection."""
    key = str(run_id)
    _BACKGROUND_RUN_TASKS[key] = task

    def _cleanup(_task: asyncio.Task[Any]) -> None:
        _BACKGROUND_RUN_TASKS.pop(key, None)

    task.add_done_callback(_cleanup)


async def _execute_background_run(
    run_id: uuid.UUID,
    workflow_name: str,
    input_text: str,
    project_id: str | None = None,
) -> None:
    """Execute orchestration with a fresh DB session in background."""
    factory = _get_session_factory()
    short_term = ShortTermMemory()
    try:
        async with factory() as db:
            svc = OrchestrationService(db, short_term)
            try:
                await svc.start_run(
                    workflow_name=workflow_name,
                    input_text=input_text,
                    auto_route=False,
                    run_id=run_id,
                    project_id=project_id,
                )
                await db.commit()
            except Exception as e:
                logger.error("Background orchestration failed for %s: %s", run_id, e, exc_info=True)
                existing = await db.get(OrchestrationRun, run_id)
                if existing is not None:
                    existing.status = "failed"
                    existing.error_message = str(e)
                    await db.commit()
                else:
                    await db.rollback()
    finally:
        await short_term.close()


class OrchestrationService:
    """High-level orchestration operations.

    Follows the same patterns as AgentService and MemoryService.
    """

    def __init__(
        self,
        db: AsyncSession,
        short_term: ShortTermMemory | None = None,
    ) -> None:
        import asyncio
        self._db = db
        self._db_lock = asyncio.Lock()
        self._settings = get_settings()
        self._agent_service = AgentService(db, short_term, db_lock=self._db_lock)
        self._registry = AgentRegistry(db)
        self._router = AgentRouter()
        self._orchestrator = Orchestrator(
            db=db,
            agent_service=self._agent_service,
            registry=self._registry,
            db_lock=self._db_lock,
        )

    async def start_run(
        self,
        workflow_name: str | None = None,
        input_text: str = "",
        auto_route: bool = False,
        run_id: uuid.UUID | None = None,
        project_id: uuid.UUID | str | None = None,
    ) -> dict[str, Any]:
        """Start an orchestration run.

        Args:
            workflow_name: Explicit workflow to run. If None and auto_route=True,
                          the router selects the workflow.
            input_text: Task input text.
            auto_route: If True and workflow_name is None, auto-route based on input.

        Returns:
            Orchestration result dict.
        """
        workflow_name = self._resolve_workflow_name(
            workflow_name=workflow_name,
            input_text=input_text,
            auto_route=auto_route,
        )
        workflow = get_workflow(workflow_name)
        if workflow is None:
            raise ValueError(
                f"Workflow '{workflow_name}' not found. "
                f"Available: {[w['name'] for w in list_workflows()]}"
            )
        normalized_project_id = str(project_id) if project_id else None
        agent_overrides = await self._ensure_workflow_agents(
            workflow,
            project_id=normalized_project_id,
        )

        logger.info(
            "Starting orchestration | workflow=%s | agents=%s",
            workflow_name,
            workflow.agent_names,
        )

        result = await self._orchestrator.execute_workflow(
            workflow_name=workflow_name,
            input_text=input_text,
            run_id=run_id,
            project_id=normalized_project_id,
            agent_overrides=agent_overrides,
        )

        return result

    async def enqueue_run(
        self,
        workflow_name: str | None = None,
        input_text: str = "",
        auto_route: bool = False,
        project_id: uuid.UUID | str | None = None,
    ) -> dict[str, Any]:
        """Queue orchestration run to execute in background."""
        workflow_name = self._resolve_workflow_name(
            workflow_name=workflow_name,
            input_text=input_text,
            auto_route=auto_route,
        )
        workflow = get_workflow(workflow_name)
        if workflow is None:
            raise ValueError(
                f"Workflow '{workflow_name}' not found. "
                f"Available: {[w['name'] for w in list_workflows()]}"
            )
        normalized_project_id = str(project_id) if project_id else None
        await self._ensure_workflow_agents(
            workflow,
            project_id=normalized_project_id,
        )

        run = OrchestrationRun(
            id=uuid.uuid4(),
            workflow_name=workflow_name,
            status="pending",
            input=input_text,
            agent_sequence=workflow.agent_names,
        )
        self._db.add(run)
        async with self._db_lock:
            await self._db.commit()
            await self._db.refresh(run)

        task = asyncio.create_task(
            _execute_background_run(
                run_id=run.id,
                workflow_name=workflow_name,
                input_text=input_text,
                project_id=normalized_project_id,
            )
        )
        _track_background_task(run.id, task)

        return {
            "run_id": str(run.id),
            "workflow": workflow_name,
            "status": "pending",
            "result": None,
            "queued": True,
        }

    async def get_run(self, run_id: uuid.UUID) -> dict[str, Any] | None:
        """Get orchestration run by ID."""
        run = await self._db.get(OrchestrationRun, run_id)
        if run is None:
            return None

        steps_result = await self._db.execute(
            select(OrchestrationStep)
            .where(OrchestrationStep.run_id == run_id)
            .order_by(OrchestrationStep.step_index)
        )
        steps = steps_result.scalars().all()

        return {
            "id": str(run.id),
            "workflow_name": run.workflow_name,
            "status": run.status,
            "input": run.input,
            "output": run.output,
            "agent_sequence": run.agent_sequence,
            "intermediate_results": run.intermediate_results,
            "error_message": run.error_message,
            "retry_count": run.retry_count,
            "created_at": str(run.created_at),
            "updated_at": str(run.updated_at),
            "steps": [
                {
                    "id": str(s.id),
                    "agent_name": s.agent_name,
                    "agent_id": str(s.agent_id) if s.agent_id else None,
                    "step_index": s.step_index,
                    "status": s.status,
                    "input": s.input,
                    "output": s.output,
                    "error_message": s.error_message,
                    "duration_ms": s.duration_ms,
                    "created_at": str(s.created_at),
                }
                for s in steps
            ],
        }

    async def list_runs(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List orchestration runs."""
        q = select(OrchestrationRun)
        if status:
            q = q.where(OrchestrationRun.status == status)
        q = q.order_by(OrchestrationRun.created_at.desc()).limit(limit)

        result = await self._db.execute(q)
        runs = result.scalars().all()

        return [
            {
                "id": str(r.id),
                "workflow_name": r.workflow_name,
                "status": r.status,
                "input": r.input[:200] if r.input else None,
                "created_at": str(r.created_at),
            }
            for r in runs
        ]

    def get_available_workflows(self) -> list[dict[str, str]]:
        """List all available workflow definitions."""
        return list_workflows()

    def explain_routing(self, input_text: str) -> dict[str, Any]:
        """Explain which workflow would be chosen for given input."""
        return self._router.explain_routing(input_text)

    def _resolve_workflow_name(
        self,
        workflow_name: str | None,
        input_text: str,
        auto_route: bool,
    ) -> str:
        """Resolve workflow name with optional auto-routing."""
        if workflow_name is None:
            if auto_route:
                workflow_name = self._router.route_to_name(input_text)
                logger.info("Auto-routed to workflow: %s", workflow_name)
            else:
                workflow_name = "reasoning_workflow"
        return workflow_name

    async def _ensure_workflow_agents(
        self,
        workflow: WorkflowDefinition,
        *,
        project_id: str | None = None,
    ) -> dict[str, uuid.UUID]:
        """Ensure all workflow agents exist, returning workflow role->agent_id."""
        missing_after_create: list[str] = []
        created: list[str] = []
        resolved_map: dict[str, uuid.UUID] = {}

        if project_id:
            project_agents = await self._agent_service.ensure_project_agents(project_id=project_id)
            for step in workflow.steps:
                info = project_agents.get(step.agent_name)
                if not info:
                    missing_after_create.append(step.agent_name)
                    continue
                try:
                    resolved_map[step.agent_name] = uuid.UUID(str(info["id"]))
                except Exception:
                    missing_after_create.append(step.agent_name)

            if missing_after_create:
                raise ValueError(
                    "Project-scoped workflow agents not found: "
                    + ", ".join(sorted(set(missing_after_create)))
                )
            return resolved_map

        for step in workflow.steps:
            agent_name = step.agent_name
            existing = await self._registry.resolve(agent_name)
            if existing is not None:
                resolved_map[agent_name] = existing
                continue

            if not self._settings.orchestration_autocreate_agents:
                missing_after_create.append(agent_name)
                continue

            await self._agent_service.create_agent(
                name=agent_name,
                system_prompt=get_default_system_prompt(agent_name),
                description=step.description or f"Auto-created orchestration agent: {agent_name}",
                config={
                    "autocreated": True,
                    "source": "orchestration",
                    "role_agent": True,
                },
            )
            created.append(agent_name)

            resolved = await self._registry.resolve(agent_name)
            if resolved is None:
                missing_after_create.append(agent_name)
            else:
                resolved_map[agent_name] = resolved

        if created:
            logger.info("Auto-created orchestration agents: %s", created)

        if missing_after_create:
            raise ValueError(
                "Agents not found for workflow: "
                + ", ".join(sorted(set(missing_after_create)))
            )
        return resolved_map
