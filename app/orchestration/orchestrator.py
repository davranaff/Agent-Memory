"""Orchestrator — multi-agent workflow execution engine."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.orchestration.models import OrchestrationRun, OrchestrationStep
from app.orchestration.registry import AgentRegistry
from app.orchestration.workflows import (
    ExecutionMode,
    WorkflowDefinition,
    WorkflowStep,
    get_workflow,
)
from app.services.agent_service import AgentService

logger = logging.getLogger(__name__)


class Orchestrator:
    """Multi-agent workflow execution engine.

    Supports sequential, parallel, and mixed execution modes.
    Uses existing LangGraph agent graphs via AgentService.
    """

    def __init__(
        self,
        db: AsyncSession,
        agent_service: AgentService,
        registry: AgentRegistry,
        db_lock: asyncio.Lock | None = None,
    ) -> None:
        self._db = db
        self._db_lock = db_lock or asyncio.Lock()
        self._agent_service = agent_service
        self._registry = registry
        self._settings = get_settings()

    async def execute_workflow(
        self,
        workflow_name: str,
        input_text: str,
        run_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Execute a complete workflow.

        Args:
            workflow_name: Name of the workflow definition to execute.
            input_text: The task input to process.
            run_id: Optional pre-created run ID.

        Returns:
            Orchestration result dict with run_id, status, output.
        """
        workflow = get_workflow(workflow_name)
        if workflow is None:
            raise ValueError(f"Workflow '{workflow_name}' not found")

        # Create the orchestration run record
        run = OrchestrationRun(
            id=run_id or uuid.uuid4(),
            workflow_name=workflow_name,
            status="running",
            input=input_text,
            agent_sequence=workflow.agent_names,
        )
        if run_id:
            # Update existing
            existing = await self._db.get(OrchestrationRun, run_id)
            if existing:
                existing.status = "running"
                run = existing
            else:
                self._db.add(run)
        else:
            self._db.add(run)
        async with self._db_lock:
            await self._db.commit()
            await self._db.refresh(run)

        logger.info(
            "Starting orchestration run %s | workflow: %s | agents: %s",
            run.id,
            workflow_name,
            workflow.agent_names,
        )

        try:
            if workflow.execution_mode == ExecutionMode.SEQUENTIAL:
                result = await self._execute_sequential(run, workflow, input_text)
            elif workflow.execution_mode == ExecutionMode.PARALLEL:
                result = await self._execute_parallel(run, workflow, input_text)
            elif workflow.execution_mode == ExecutionMode.MIXED:
                result = await self._execute_mixed(run, workflow, input_text)
            else:
                raise ValueError(f"Unknown execution mode: {workflow.execution_mode}")

            # Finalize
            run.status = "completed"
            run.output = result
            async with self._db_lock:
                await self._db.flush()

            logger.info("Orchestration run %s completed", run.id)
            return {
                "run_id": str(run.id),
                "workflow": workflow_name,
                "status": "completed",
                "result": result,
                "steps": await self._get_step_summaries(run.id),
            }

        except Exception as e:
            logger.error("Orchestration run %s failed: %s", run.id, e)
            run.status = "failed"
            run.error_message = str(e)
            async with self._db_lock:
                await self._db.flush()

            return {
                "run_id": str(run.id),
                "workflow": workflow_name,
                "status": "failed",
                "error": str(e),
                "steps": await self._get_step_summaries(run.id),
            }

    async def _execute_sequential(
        self,
        run: OrchestrationRun,
        workflow: WorkflowDefinition,
        input_text: str,
    ) -> str:
        """Execute workflow steps sequentially, piping output → input."""
        current_input = input_text
        intermediate: list[dict[str, Any]] = []

        for i, step in enumerate(workflow.steps):
            result = await self._execute_step_with_retry(
                run=run,
                step=step,
                step_index=i,
                input_text=current_input,
                max_retries=workflow.max_retries,
            )
            intermediate.append(result)
            current_input = result.get("output", current_input)

        run.intermediate_results = intermediate
        async with self._db_lock:
            await self._db.flush()

        return current_input

    async def _execute_parallel(
        self,
        run: OrchestrationRun,
        workflow: WorkflowDefinition,
        input_text: str,
    ) -> str:
        """Execute all workflow steps in parallel."""
        max_concurrent = self._settings.orchestration_max_parallel_agents
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _bounded_step(step: WorkflowStep, idx: int) -> dict[str, Any]:
            async with semaphore:
                return await self._execute_step_with_retry(
                    run=run,
                    step=step,
                    step_index=idx,
                    input_text=input_text,
                    max_retries=workflow.max_retries,
                )

        tasks = [
            _bounded_step(step, i)
            for i, step in enumerate(workflow.steps)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        intermediate: list[dict[str, Any]] = []
        outputs: list[str] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                intermediate.append({
                    "agent": workflow.steps[i].agent_name,
                    "status": "failed",
                    "error": str(result),
                })
            else:
                intermediate.append(result)
                outputs.append(result.get("output", ""))

        run.intermediate_results = intermediate
        async with self._db_lock:
            await self._db.flush()

        # Combine parallel outputs
        return "\n\n---\n\n".join(outputs) if outputs else "All parallel steps failed"

    async def _execute_mixed(
        self,
        run: OrchestrationRun,
        workflow: WorkflowDefinition,
        input_text: str,
    ) -> str:
        """Execute mixed mode: sequential groups with parallel steps within.

        Steps with parallel_group=None run sequentially.
        Steps with the same parallel_group run in parallel.
        """
        current_input = input_text
        intermediate: list[dict[str, Any]] = []
        step_idx = 0

        # Build execution order: group steps by parallel_group, preserving order
        execution_groups: list[list[tuple[int, WorkflowStep]]] = []
        current_group: list[tuple[int, WorkflowStep]] = []
        last_group_id: int | None = -999  # sentinel

        for i, step in enumerate(workflow.steps):
            if step.parallel_group is None:
                # Sequential step — flush any pending parallel group
                if current_group:
                    execution_groups.append(current_group)
                    current_group = []
                execution_groups.append([(i, step)])
                last_group_id = -999
            elif step.parallel_group == last_group_id:
                current_group.append((i, step))
            else:
                if current_group:
                    execution_groups.append(current_group)
                current_group = [(i, step)]
                last_group_id = step.parallel_group

        if current_group:
            execution_groups.append(current_group)

        # Execute each group
        for group in execution_groups:
            if len(group) == 1:
                # Single step — sequential
                idx, step = group[0]
                result = await self._execute_step_with_retry(
                    run=run,
                    step=step,
                    step_index=idx,
                    input_text=current_input,
                    max_retries=workflow.max_retries,
                )
                intermediate.append(result)
                current_input = result.get("output", current_input)
            else:
                # Multiple steps — parallel
                max_concurrent = self._settings.orchestration_max_parallel_agents
                semaphore = asyncio.Semaphore(max_concurrent)

                async def _bounded(s: WorkflowStep, ix: int) -> dict[str, Any]:
                    async with semaphore:
                        return await self._execute_step_with_retry(
                            run=run,
                            step=s,
                            step_index=ix,
                            input_text=current_input,
                            max_retries=workflow.max_retries,
                        )

                tasks = [_bounded(step, idx) for idx, step in group]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                outputs = []
                for (idx, step), result in zip(group, results):
                    if isinstance(result, Exception):
                        intermediate.append({
                            "agent": step.agent_name,
                            "status": "failed",
                            "error": str(result),
                        })
                    else:
                        intermediate.append(result)
                        outputs.append(result.get("output", ""))

                if outputs:
                    current_input = "\n\n---\n\n".join(outputs)

        run.intermediate_results = intermediate
        async with self._db_lock:
            await self._db.flush()

        return current_input

    async def _execute_step_with_retry(
        self,
        run: OrchestrationRun,
        step: WorkflowStep,
        step_index: int,
        input_text: str,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Execute a single agent step with retry logic."""
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                return await self._execute_step(
                    run=run,
                    step=step,
                    step_index=step_index,
                    input_text=input_text,
                    attempt=attempt,
                )
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait_s = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        "Step '%s' attempt %d failed: %s — retrying in %ds",
                        step.agent_name,
                        attempt + 1,
                        e,
                        wait_s,
                    )
                    await asyncio.sleep(wait_s)

        # All retries exhausted
        raise RuntimeError(
            f"Step '{step.agent_name}' failed after {max_retries + 1} attempts: {last_error}"
        )

    async def _execute_step(
        self,
        run: OrchestrationRun,
        step: WorkflowStep,
        step_index: int,
        input_text: str,
        attempt: int = 0,
    ) -> dict[str, Any]:
        """Execute a single agent step."""
        agent_id = await self._registry.resolve(step.agent_name)
        if agent_id is None:
            raise ValueError(f"Agent '{step.agent_name}' not found in registry")

        # Create step record
        step_record = OrchestrationStep(
            run_id=run.id,
            agent_id=agent_id,
            agent_name=step.agent_name,
            step_index=step_index,
            status="running",
            input=input_text[:5000],  # Truncate for storage
        )

        async with self._db_lock:
            self._db.add(step_record)
            await self._db.flush()

        logger.info(
            "Executing step %d: agent='%s' | run=%s | attempt=%d",
            step_index,
            step.agent_name,
            run.id,
            attempt,
        )

        start_time = time.monotonic()
        try:
            result = await self._agent_service.run_agent(
                agent_id=agent_id,
                input_text=input_text,
            )
            duration_ms = int((time.monotonic() - start_time) * 1000)

            output = result.get("output", "")
            step_record.status = "completed"
            step_record.output = output[:5000]
            step_record.duration_ms = duration_ms
            async with self._db_lock:
                await self._db.flush()

            logger.info(
                "Step %d completed: agent='%s' | %dms",
                step_index,
                step.agent_name,
                duration_ms,
            )

            return {
                "agent": step.agent_name,
                "step_index": step_index,
                "status": "completed",
                "output": output,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            step_record.status = "failed"
            step_record.error_message = str(e)
            step_record.duration_ms = duration_ms
            async with self._db_lock:
                await self._db.flush()
            raise

    async def _get_step_summaries(self, run_id: uuid.UUID) -> list[dict[str, Any]]:
        """Get step summaries for a run."""
        from sqlalchemy import select

        result = await self._db.execute(
            select(OrchestrationStep)
            .where(OrchestrationStep.run_id == run_id)
            .order_by(OrchestrationStep.step_index)
        )
        steps = result.scalars().all()
        return [
            {
                "agent": s.agent_name,
                "step_index": s.step_index,
                "status": s.status,
                "duration_ms": s.duration_ms,
                "error": s.error_message,
            }
            for s in steps
        ]
