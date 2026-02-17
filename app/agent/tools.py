"""Built-in tools available to the LangGraph agent."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool


@tool
async def memory_store(content: str, memory_type: str = "general", importance: int = 5) -> str:
    """Use this tool to persist durable facts and decisions.

    You MUST call this tool after key conclusions, user preferences, constraints,
    and final outcomes. NEVER finish a meaningful task without storing critical context.
    This tool preserves cross-turn continuity.
    """
    # This tool is bound at runtime with the actual memory service
    return f"Stored memory: {content[:100]}"


@tool
async def memory_search(query: str, top_k: int = 5) -> str:
    """Use this tool first to recover prior context before reasoning.

    You MUST call this tool at the start of every non-trivial task.
    NEVER assume history, IDs, or user preferences without searching memory.
    This tool reduces hallucinations and repeated mistakes.
    """
    return f"Searching memory for: {query}"


@tool
async def memory_get(memory_id: str) -> str:
    """Use this tool for exact memory lookup by known ID.

    You SHOULD call this when memory_search returns candidate IDs and precision matters.
    NEVER rely on approximate memory text when exact content is required.
    This tool ensures deterministic recall.
    """
    return f"Getting memory: {memory_id}"


def get_builtin_tools() -> list[Any]:
    """Return the list of built-in tools."""
    return [memory_store, memory_search, memory_get]
