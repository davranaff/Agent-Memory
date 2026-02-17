"""LangGraph agent graph — multi-step reasoning with tool calling and memory."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from app.agent.prompts import DEFAULT_AGENT_SYSTEM_PROMPT
from app.agent.state import AgentState
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


def _get_llm():
    """Create the appropriate LLM based on settings."""
    settings = get_settings()

    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.llm_model,
            temperature=0.7,
        )
    elif settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        kwargs: dict[str, Any] = {
            "model": settings.llm_model,
            "temperature": 0.7,
            "api_key": settings.openai_api_key,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def _build_system_message(
    system_prompt: str,
    memories: list[dict[str, Any]],
    context: dict[str, Any],
) -> str:
    """Build the full system message with memory injection."""
    parts = [system_prompt]

    if memories:
        parts.append("\n\n## Relevant Memories")
        for i, mem in enumerate(memories, 1):
            sim = mem.get("similarity", 0)
            parts.append(f"{i}. [{mem.get('memory_type', 'general')}] (relevance: {sim:.2f}) {mem['content']}")

    if context:
        parts.append(f"\n\n## Additional Context\n{context}")

    return "\n".join(parts)


async def _retrieve_memory_node(state: AgentState) -> AgentState:
    """Node: Retrieve relevant memories for context enrichment."""
    # Memories are pre-loaded by the agent service, this node can enhance them
    logger.debug(
        "Memory node: %d memories available", len(state.get("memories", []))
    )
    return state


async def _reason_node(state: AgentState) -> AgentState:
    """Node: LLM reasoning with memory-enhanced prompt."""
    try:
        llm = _get_llm()
    except Exception as e:
        logger.error("Failed to initialize LLM: %s", e)
        return {
            **state,
            "output": f"LLM unavailable ({e}). The brain backend is operational — "
                      f"use memory and MCP tools directly.",
            "messages": state.get("messages", []),
        }

    system_msg = _build_system_message(
        system_prompt=state.get("context", {}).get(
            "system_prompt", DEFAULT_AGENT_SYSTEM_PROMPT
        ),
        memories=state.get("memories", []),
        context=state.get("context", {}),
    )

    # Build message list
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

    messages = [SystemMessage(content=system_msg)]

    # Add conversation history
    for msg in state.get("history", []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    # Add current input
    messages.append(HumanMessage(content=state["input"]))

    # Add internal graph messages (contains previous steps in this run)
    from langchain_core.messages import ToolMessage
    for msg in state.get("messages", []):
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            # Handle assistant messages that might have tool calls
            tcs = msg.get("tool_calls")
            if tcs:
                messages.append(AIMessage(content=content, tool_calls=tcs))
            else:
                messages.append(AIMessage(content=content))
        elif role == "tool":
            # For tool messages, we need the tool_call_id
            # This is a bit complex if not stored, but let's try to match by name or pass as simple msg
            # Better: use the list of tool results properly
            if isinstance(msg.get("raw_results"), list):
                for res in msg["raw_results"]:
                    messages.append(ToolMessage(
                        tool_call_id=res.get("id", "unknown"),
                        content=str(res.get("result", "")),
                    ))
            else:
                messages.append(HumanMessage(content=f"Tool result: {content}"))

    try:
        # Bind tools for function calling
        from app.agent.tools import get_builtin_tools

        tools = get_builtin_tools()
        llm_with_tools = llm.bind_tools(tools)

        logger.debug("Calling LLM with %d messages", len(messages))
        response = await llm_with_tools.ainvoke(messages)
        logger.debug("LLM Response: %s", response)

        output = response.content if hasattr(response, "content") else str(response)
        tool_calls = []

        new_internal_msg: dict[str, Any] = {"role": "assistant", "content": output}

        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls.append({
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                    "id": tc.get("id", ""),
                })
            new_internal_msg["tool_calls"] = response.tool_calls

        return {
            **state,
            "output": output,
            "tool_calls": tool_calls,
            "messages": [
                *state.get("messages", []),
                new_internal_msg,
            ],
        }
    except Exception as e:
        logger.error("LLM invocation failed: %r", e, exc_info=True)
        return {
            **state,
            "output": f"Error during reasoning: {e}",
            "messages": state.get("messages", []),
        }


async def _tool_execution_node(state: AgentState) -> AgentState:
    """Node: Execute any tool calls from the reasoning step."""
    tool_calls = state.get("tool_calls", [])
    if not tool_calls:
        return state

    from app.agent.tools import get_builtin_tools

    tools_map = {t.name: t for t in get_builtin_tools()}
    results = []

    for tc in tool_calls:
        tool_name = tc.get("name", "")
        tool_args = tc.get("args", {})

        if tool_name in tools_map:
            try:
                result = await tools_map[tool_name].ainvoke(tool_args)
                results.append({
                    "tool": tool_name,
                    "result": str(result),
                    "status": "success",
                })
            except Exception as e:
                results.append({
                    "tool": tool_name,
                    "result": str(e),
                    "status": "error",
                })
        else:
            results.append({
                "tool": tool_name,
                "result": f"Unknown tool: {tool_name}",
                "status": "error",
            })

    return {
        **state,
        "tool_calls": [], # Clear pending calls
        "messages": [
            *state.get("messages", []),
            {"role": "tool", "content": str(results), "raw_results": results},
        ],
    }


async def _store_memory_node(state: AgentState) -> AgentState:
    """Node: Store important information from the conversation."""
    # The agent service handles memory storage externally
    logger.debug("Store memory node: conversation processed")
    return state


def _should_use_tools(state: AgentState) -> str:
    """Edge: Decide whether to execute tools or finish."""
    if state.get("tool_calls"):
        return "execute_tools"
    return "finish"


def create_agent_graph(
    system_prompt: str = DEFAULT_AGENT_SYSTEM_PROMPT,
    memory_service: Any = None,
) -> StateGraph:
    """Build and compile the LangGraph agent."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("retrieve_memory", _retrieve_memory_node)
    graph.add_node("reason", _reason_node)
    graph.add_node("execute_tools", _tool_execution_node)
    graph.add_node("store_memory", _store_memory_node)

    # Define edges
    graph.set_entry_point("retrieve_memory")
    graph.add_edge("retrieve_memory", "reason")
    graph.add_conditional_edges(
        "reason",
        _should_use_tools,
        {
            "execute_tools": "execute_tools",
            "finish": "store_memory",
        },
    )
    graph.add_edge("execute_tools", "reason")
    graph.add_edge("store_memory", END)

    return graph.compile()
