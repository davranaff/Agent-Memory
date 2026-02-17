"""Agent router — selects appropriate workflow based on task input."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.orchestration.workflows import (
    WorkflowDefinition,
    get_workflow,
    list_workflows,
)

logger = logging.getLogger(__name__)


class AgentRouter:
    """Routes tasks to appropriate workflows.

    Supports rule-based routing with extensible pattern matching.
    Designed for future LLM-based routing integration.
    """

    def __init__(self) -> None:
        self._rules: list[tuple[re.Pattern[str], str]] = []
        self._default_workflow: str = "reasoning_workflow"
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """Register built-in routing rules."""
        self.add_rule(
            r"(?i)(remember|store|save|memorize|note|record)",
            "memory_workflow",
        )
        self.add_rule(
            r"(?i)(recall|retrieve|search|find|look\s*up|what\s+do\s+you\s+know)",
            "memory_workflow",
        )
        self.add_rule(
            r"(?i)(use\s+tool|execute|run\s+command|call\s+function|api)",
            "tool_workflow",
        )
        self.add_rule(
            r"(?i)(analyze|compare|evaluate|assess|review|comprehensive)",
            "full_pipeline",
        )
        self.add_rule(
            r"(?i)(parallel|multiple\s+perspectives|diverse|all\s+agents)",
            "parallel_analysis",
        )

    def add_rule(self, pattern: str, workflow_name: str) -> None:
        """Add a routing rule: regex pattern → workflow name."""
        self._rules.append((re.compile(pattern), workflow_name))
        logger.debug("Added routing rule: %s -> %s", pattern, workflow_name)

    def set_default_workflow(self, workflow_name: str) -> None:
        """Set the fallback workflow for unmatched inputs."""
        self._default_workflow = workflow_name

    def route(self, input_text: str) -> WorkflowDefinition:
        """Route an input to the appropriate workflow.

        Checks rules in order, returns first match. Falls back to default.
        """
        for pattern, workflow_name in self._rules:
            if pattern.search(input_text):
                workflow = get_workflow(workflow_name)
                if workflow:
                    logger.info(
                        "Routed input to '%s' (matched: %s)",
                        workflow_name,
                        pattern.pattern[:40],
                    )
                    return workflow

        # Default
        workflow = get_workflow(self._default_workflow)
        if workflow is None:
            raise ValueError(f"Default workflow '{self._default_workflow}' not found")
        logger.info("Routed input to default workflow '%s'", self._default_workflow)
        return workflow

    def route_to_name(self, input_text: str) -> str:
        """Route and return just the workflow name."""
        return self.route(input_text).name

    def explain_routing(self, input_text: str) -> dict[str, Any]:
        """Explain why a particular workflow was chosen."""
        for pattern, workflow_name in self._rules:
            match = pattern.search(input_text)
            if match and get_workflow(workflow_name):
                return {
                    "workflow": workflow_name,
                    "matched_rule": pattern.pattern,
                    "matched_text": match.group(),
                    "method": "rule_based",
                }

        return {
            "workflow": self._default_workflow,
            "matched_rule": None,
            "matched_text": None,
            "method": "default_fallback",
        }
