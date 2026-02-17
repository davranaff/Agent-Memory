"""Orchestration service — high-level orchestration operations."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.short_term import ShortTermMemory
from app.orchestration.models import OrchestrationRun, OrchestrationStep
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.registry import AgentRegistry
from app.orchestration.router import AgentRouter
from app.orchestration.workflows import get_workflow, list_workflows
from app.services.agent_service import AgentService

logger = logging.getLogger(__name__)


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
        if workflow_name is None:
            if auto_route:
                workflow_name = self._router.route_to_name(input_text)
                logger.info("Auto-routed to workflow: %s", workflow_name)
            else:
                workflow_name = "reasoning_workflow"

        # Validate workflow exists
        workflow = get_workflow(workflow_name)
        if workflow is None:
            raise ValueError(
                f"Workflow '{workflow_name}' not found. "
                f"Available: {[w['name'] for w in list_workflows()]}"
            )

        logger.info(
            "Starting orchestration | workflow=%s | agents=%s",
            workflow_name,
            workflow.agent_names,
        )

        result = await self._orchestrator.execute_workflow(
            workflow_name=workflow_name,
            input_text=input_text,
        )

        return result

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
