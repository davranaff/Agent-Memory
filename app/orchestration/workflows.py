"""Workflow definitions — DAGs and sequences of agent steps."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ExecutionMode(str, Enum):
    """How steps within a workflow are executed."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    MIXED = "mixed"  # Uses parallel_group for grouping


@dataclass(frozen=True)
class WorkflowStep:
    """A single step in a workflow."""

    agent_name: str
    description: str = ""
    parallel_group: int | None = None  # Steps with same group run in parallel


@dataclass(frozen=True)
class WorkflowDefinition:
    """A complete workflow definition."""

    name: str
    description: str = ""
    steps: tuple[WorkflowStep, ...] = ()
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    max_retries: int = 3

    @property
    def agent_names(self) -> list[str]:
        """Return ordered list of agent names in this workflow."""
        return [s.agent_name for s in self.steps]

    def parallel_groups(self) -> dict[int | None, list[WorkflowStep]]:
        """Group steps by their parallel_group."""
        groups: dict[int | None, list[WorkflowStep]] = {}
        for step in self.steps:
            groups.setdefault(step.parallel_group, []).append(step)
        return groups


# ── Predefined Workflows ──────────────────────────────────────────────

MEMORY_WORKFLOW = WorkflowDefinition(
    name="memory_workflow",
    description="Retrieve relevant context, reason about it, then store insights.",
    steps=(
        WorkflowStep(agent_name="retrieval_agent", description="Search long-term memory"),
        WorkflowStep(agent_name="reasoning_agent", description="Analyze retrieved context"),
        WorkflowStep(agent_name="memory_agent", description="Store new insights"),
    ),
    execution_mode=ExecutionMode.SEQUENTIAL,
)

REASONING_WORKFLOW = WorkflowDefinition(
    name="reasoning_workflow",
    description="Single-agent deep reasoning.",
    steps=(
        WorkflowStep(agent_name="reasoning_agent", description="Full reasoning pass"),
    ),
    execution_mode=ExecutionMode.SEQUENTIAL,
)

TOOL_WORKFLOW = WorkflowDefinition(
    name="tool_workflow",
    description="Execute a tool-heavy task then synthesize results.",
    steps=(
        WorkflowStep(agent_name="tool_agent", description="Execute tool operations"),
        WorkflowStep(agent_name="reasoning_agent", description="Synthesize tool results"),
    ),
    execution_mode=ExecutionMode.SEQUENTIAL,
)

FULL_PIPELINE = WorkflowDefinition(
    name="full_pipeline",
    description="Complete pipeline: retrieve → parallel analysis → synthesis → store.",
    steps=(
        WorkflowStep(agent_name="retrieval_agent", description="Retrieve context", parallel_group=None),
        WorkflowStep(agent_name="reasoning_agent", description="Analyze", parallel_group=1),
        WorkflowStep(agent_name="tool_agent", description="Augment with tools", parallel_group=1),
        WorkflowStep(agent_name="memory_agent", description="Store results", parallel_group=None),
    ),
    execution_mode=ExecutionMode.MIXED,
)

PARALLEL_ANALYSIS = WorkflowDefinition(
    name="parallel_analysis",
    description="Run multiple agents in parallel for diverse analysis.",
    steps=(
        WorkflowStep(agent_name="reasoning_agent", description="Analytical reasoning", parallel_group=0),
        WorkflowStep(agent_name="retrieval_agent", description="Memory-guided analysis", parallel_group=0),
        WorkflowStep(agent_name="tool_agent", description="Tool-augmented analysis", parallel_group=0),
    ),
    execution_mode=ExecutionMode.PARALLEL,
)


# ── Registry of all workflows ────────────────────────────────────────

_WORKFLOWS: dict[str, WorkflowDefinition] = {
    w.name: w
    for w in [
        MEMORY_WORKFLOW,
        REASONING_WORKFLOW,
        TOOL_WORKFLOW,
        FULL_PIPELINE,
        PARALLEL_ANALYSIS,
    ]
}


def get_workflow(name: str) -> WorkflowDefinition | None:
    """Get a workflow definition by name."""
    return _WORKFLOWS.get(name)


def list_workflows() -> list[dict[str, str]]:
    """List all available workflow definitions."""
    return [
        {
            "name": w.name,
            "description": w.description,
            "execution_mode": w.execution_mode.value,
            "agents": w.agent_names,
        }
        for w in _WORKFLOWS.values()
    ]


def register_workflow(workflow: WorkflowDefinition) -> None:
    """Register a custom workflow definition."""
    _WORKFLOWS[workflow.name] = workflow
