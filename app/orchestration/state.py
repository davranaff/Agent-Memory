"""Orchestration state definitions."""

from __future__ import annotations

from typing import Any, TypedDict


class OrchestrationState(TypedDict, total=False):
    """State tracked through an orchestration run."""

    run_id: str
    workflow_name: str
    agent_sequence: list[str]
    current_agent: str
    current_step_index: int
    intermediate_results: list[dict[str, Any]]
    final_result: str
    status: str  # pending | running | completed | failed | partial
    input: str
    error: str | None
