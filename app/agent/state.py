"""Agent state definition for LangGraph."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """State passed through the LangGraph agent."""

    # Input
    input: str
    agent_id: str
    session_id: str

    # Context
    memories: list[dict[str, Any]]
    history: list[dict[str, str]]
    context: dict[str, Any]

    # Processing
    messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]

    # Output
    output: str
