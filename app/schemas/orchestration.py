"""Pydantic schemas for Orchestration endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────
class OrchestrationRunRequest(BaseModel):
    workflow: str | None = Field(
        default=None,
        description="Workflow name. If omitted with auto_route=True, auto-selects.",
    )
    input: str = Field(..., min_length=1)
    auto_route: bool = Field(
        default=False,
        description="Auto-route to best workflow based on input.",
    )


# ── Response ──────────────────────────────────────────────────────────
class OrchestrationStepResponse(BaseModel):
    id: str | None = None
    agent_name: str
    agent_id: str | None = None
    step_index: int
    status: str
    input: str | None = None
    output: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    created_at: str | None = None


class OrchestrationRunResponse(BaseModel):
    id: str
    workflow_name: str
    status: str
    input: str | None = None
    output: str | None = None
    agent_sequence: list[str] | None = None
    intermediate_results: list[dict[str, Any]] | None = None
    error_message: str | None = None
    retry_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None
    steps: list[OrchestrationStepResponse] = Field(default_factory=list)


class OrchestrationResultResponse(BaseModel):
    run_id: str
    workflow: str
    status: str
    result: str | None = None
    error: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowInfo(BaseModel):
    name: str
    description: str
    execution_mode: str
    agents: list[str]
