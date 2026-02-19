"""MCP Server — exposes brain tools via Model Context Protocol."""

from __future__ import annotations

import logging
import uuid
import asyncio
import re
from typing import Any

import anyio
from fastmcp import FastMCP
from fastapi import FastAPI, Request
from mcp import types as mcp_types
from pydantic import ValidationError
from starlette.responses import Response

from app.config.settings import get_settings
from app.db.session import _get_session_factory
from app.memory.embeddings import get_embedding_provider
from app.memory.short_term import ShortTermMemory
from app.paths import (
    extract_project_paths_from_mcp_params,
    project_path_candidates_from_env,
)
from app.services.agent_service import AgentService
from app.services.memory_service import MemoryService
from app.services.project_memory import persist_project_memories

logger = logging.getLogger(__name__)

# Shared Redis client — avoids creating new connections per request (#3 fix)
_shared_short_term: ShortTermMemory | None = None
_MCP_CONTEXT_CACHE_KEY = "mcp:active:context"
_MCP_CONTEXT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


def _get_short_term() -> ShortTermMemory:
    """Return the shared ShortTermMemory singleton."""
    global _shared_short_term
    if _shared_short_term is None:
        _shared_short_term = ShortTermMemory()
    return _shared_short_term


async def close_shared_short_term() -> None:
    """Shutdown hook: close the shared Redis client."""
    global _shared_short_term
    if _shared_short_term is not None:
        await _shared_short_term.close()
        _shared_short_term = None


async def _get_active_mcp_context() -> dict[str, Any]:
    """Read active MCP context from Redis cache."""
    short_term = _get_short_term()
    ctx = await short_term.cache_get(_MCP_CONTEXT_CACHE_KEY)
    if isinstance(ctx, dict):
        return ctx
    return {}


async def _set_active_mcp_context(context: dict[str, Any], ttl: int = _MCP_CONTEXT_TTL_SECONDS) -> dict[str, Any]:
    """Persist active MCP context to Redis cache."""
    short_term = _get_short_term()
    cleaned = {
        key: value
        for key, value in context.items()
        if value is not None and value != ""
    }
    if ttl < 60:
        ttl = 60
    await short_term.cache_set(_MCP_CONTEXT_CACHE_KEY, cleaned, ttl=ttl)
    return cleaned


async def _clear_active_mcp_context() -> bool:
    """Clear active MCP context from Redis cache."""
    short_term = _get_short_term()
    return await short_term.cache_delete(_MCP_CONTEXT_CACHE_KEY)


async def _capture_project_path_in_context(candidate_path: str, source: str) -> None:
    """Store auto-detected project path in active MCP context."""
    cleaned = (candidate_path or "").strip()
    if not cleaned:
        return
    context = await _get_active_mcp_context()
    context["project_path"] = cleaned
    context["project_path_source"] = source
    await _set_active_mcp_context(context)


def _auto_project_path_from_env() -> str | None:
    """Detect project path from configured environment variables."""
    settings = get_settings()
    candidates = project_path_candidates_from_env(
        raw_env_keys=settings.autonomous_project_env_keys,
        fallback_path=settings.autonomous_project_fallback_path,
    )
    return candidates[0] if candidates else None


async def _resolve_default_component_id(db: Any, project_id: str) -> str | None:
    """Pick a stable default component for graph-neighbors fallback."""
    from sqlalchemy import case, select
    from app.core.models import Component

    stmt = (
        select(Component.id)
        .where(Component.project_id == project_id)
        .order_by(
            case(
                (Component.type == "file", 0),
                (Component.type == "class", 1),
                (Component.type == "function", 2),
                (Component.type == "async_function", 3),
                else_=9,
            ),
            Component.relative_path.asc(),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    component_id = result.scalar_one_or_none()
    return str(component_id) if component_id is not None else None


async def _resolve_project_name(db: Any, project_id: str) -> str | None:
    from sqlalchemy import select
    from app.core.models import Project

    try:
        project_uuid = uuid.UUID(str(project_id))
    except (ValueError, TypeError):
        return None
    stmt = select(Project.name).where(Project.id == project_uuid).limit(1)
    result = await db.execute(stmt)
    value = result.scalar_one_or_none()
    return str(value) if value is not None else None


# Whitelist of public tables allowed in db_query
_ALLOWED_PUBLIC_TABLES = frozenset({
    "agents", "sessions", "messages", "memories",
    "tools", "tool_calls", "orchestration_runs", "orchestration_steps",
})
_ALLOWED_METADATA_SCHEMAS = frozenset({"information_schema", "pg_catalog"})
_MAX_QUERY_LENGTH = 2000
_MAX_RESULT_ROWS = 100
_MAX_RESULT_ROWS_HARD = 1000

_DISCONNECT_EXCEPTIONS = (
    anyio.BrokenResourceError,
    anyio.EndOfStream,
    anyio.ClosedResourceError,
    asyncio.CancelledError,
)


def _iter_leaf_exceptions(exc: BaseException):
    """Yield non-group exceptions from nested exception groups."""
    if isinstance(exc, BaseExceptionGroup):
        for inner in exc.exceptions:
            yield from _iter_leaf_exceptions(inner)
        return
    yield exc


def _is_expected_disconnect(exc: BaseException) -> bool:
    """True when all leaf exceptions represent client disconnect/cancel events."""
    leaves = tuple(_iter_leaf_exceptions(exc))
    return bool(leaves) and all(isinstance(leaf, _DISCONNECT_EXCEPTIONS) for leaf in leaves)


def _normalize_sql_identifier(identifier: str) -> str:
    """Normalize SQL identifier for allowlist matching."""
    ident = identifier.strip().strip('"').strip()
    return ident.lower()


def _extract_table_refs(sql: str) -> list[tuple[str, str]]:
    """Extract FROM/JOIN references as (schema, table)."""
    # Supports:
    # - table
    # - schema.table
    # - "schema"."table"
    pattern = re.compile(
        r'(?:FROM|JOIN)\s+((?:"?[a-zA-Z_][a-zA-Z0-9_$]*"?)(?:\.(?:"?[a-zA-Z_][a-zA-Z0-9_$]*"?))?)',
        re.IGNORECASE,
    )
    refs: list[tuple[str, str]] = []
    for raw_ref in pattern.findall(sql):
        parts = [_normalize_sql_identifier(part) for part in raw_ref.split(".")]
        if len(parts) == 1:
            refs.append(("public", parts[0]))
        elif len(parts) == 2:
            refs.append((parts[0], parts[1]))
    return refs

# Create the MCP server instance using FastMCP
mcp = FastMCP("agent-brain")


@mcp.tool(name="context_set")
async def context_set(
    agent_id: str | None = None,
    project_id: str | None = None,
    project_path: str | None = None,
    session_id: str | None = None,
    ttl_seconds: int = _MCP_CONTEXT_TTL_SECONDS,
) -> Any:
    """When to use:
    Set or update default IDs for the current MCP workflow.

    Inputs:
    - agent_id: Optional UUID for agent-scoped tools.
    - project_id: Optional project UUID for project/graph tools.
    - project_path: Optional project filesystem path for autonomous analysis.
    - session_id: Optional UUID for conversation continuity.
    - ttl_seconds: Context TTL in seconds.

    Returns:
    - context: Stored context dictionary.
    - ttl_seconds: Effective TTL.

    Common mistakes:
    - Passing invalid UUID strings for agent_id/project_id/session_id.
    """
    try:
        if agent_id:
            uuid.UUID(agent_id)
        if project_id:
            uuid.UUID(project_id)
        if session_id:
            uuid.UUID(session_id)
    except ValueError as e:
        return {
            "error": (
                f"Invalid UUID in context: {e}. "
                "Expected UUID format for agent_id/project_id/session_id."
            )
        }

    current = await _get_active_mcp_context()
    current.update(
        {
            "agent_id": agent_id,
            "project_id": project_id,
            "project_path": project_path,
            "session_id": session_id,
        }
    )
    context = await _set_active_mcp_context(current, ttl=ttl_seconds)
    return {"context": context, "ttl_seconds": ttl_seconds}


@mcp.tool(name="context_get")
async def context_get() -> Any:
    """When to use:
    Inspect current auto-context before tool calls.

    Inputs:
    - None.

    Returns:
    - context: Current context dictionary.

    Common mistakes:
    - Assuming context exists without checking.
    """
    context = await _get_active_mcp_context()
    return {"context": context}


@mcp.tool(name="context_clear")
async def context_clear() -> Any:
    """When to use:
    Reset context when switching to another agent/project.

    Inputs:
    - None.

    Returns:
    - cleared: True if context key was removed.

    Common mistakes:
    - Forgetting to clear context before unrelated tasks.
    """
    deleted = await _clear_active_mcp_context()
    return {"cleared": bool(deleted)}


@mcp.tool(name="memory_store")
async def store_memory(
    content: str,
    memory_type: str = "general",
    agent_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    importance: int = 5,
) -> Any:
    """When to use:
    Save durable facts, decisions, constraints, and outcomes.

    Inputs:
    - content: Memory text to persist.
    - memory_type: Memory category.
    - agent_id: Optional; auto-filled from context if missing.
    - metadata: Optional extra fields; project_id/session_id auto-injected from context.
    - importance: 1..10 priority.

    Returns:
    - Memory record fields including id and created_at.
    - deduplicated/created flags from memory service.

    Common mistakes:
    - Storing low-signal or duplicate noise instead of concise facts.
    - Omitting context and expecting project/session scoping automatically.
    """
    context = await _get_active_mcp_context()
    effective_agent_id = agent_id or context.get("agent_id")
    effective_metadata = dict(metadata or {})
    if "project_id" not in effective_metadata and context.get("project_id"):
        effective_metadata["project_id"] = context["project_id"]
    if "session_id" not in effective_metadata and context.get("session_id"):
        effective_metadata["session_id"] = context["session_id"]

    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        svc = MemoryService(db, short_term)
        try:
            parsed_agent_id = uuid.UUID(effective_agent_id) if effective_agent_id else None
        except ValueError as e:
            return {"error": f"Invalid agent_id: {e}"}
        result = await svc.store(
            content=content,
            memory_type=memory_type,
            agent_id=parsed_agent_id,
            metadata=effective_metadata,
            importance=importance,
        )
        await db.commit()
        return result


@mcp.tool(name="memory_search")
async def search_memory(
    query: str,
    agent_id: str | None = None,
    memory_type: str | None = None,
    metadata_filters: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    top_k: int = 10,
    min_similarity: float = 0.0,
) -> Any:
    """When to use:
    Retrieve prior memory context before planning or execution.

    Inputs:
    - query: Search text.
    - agent_id: Optional; auto-filled from context.
    - memory_type: Optional filter.
    - metadata_filters/metadata: Optional scope filters.
    - top_k: Max results.
    - min_similarity: Similarity threshold.

    Returns:
    - List of memory hits ordered by relevance.

    Common mistakes:
    - Skipping this call on stateful tasks and losing continuity.
    - Forgetting scope filters for project-specific retrieval.
    """
    context = await _get_active_mcp_context()
    effective_agent_id = agent_id or context.get("agent_id")

    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        svc = MemoryService(db, short_term)
        scope_filters = dict(metadata_filters or metadata or {})
        if "project_id" not in scope_filters and context.get("project_id"):
            scope_filters["project_id"] = context["project_id"]
        try:
            parsed_agent_id = uuid.UUID(effective_agent_id) if effective_agent_id else None
        except ValueError as e:
            return {"error": f"Invalid agent_id: {e}"}
        return await svc.search(
            query=query,
            agent_id=parsed_agent_id,
            memory_type=memory_type,
            metadata_filters=scope_filters or None,
            top_k=top_k,
            min_similarity=min_similarity,
        )


@mcp.tool(name="memory_get")
async def get_memory(memory_id: str) -> Any:
    """When to use:
    Fetch exact memory content by known ID.

    Inputs:
    - memory_id: Memory UUID.

    Returns:
    - Full memory record or error if not found.

    Common mistakes:
    - Using approximate recall when exact memory text is required.
    """
    factory = _get_session_factory()
    async with factory() as db:
        svc = MemoryService(db)
        result = await svc.get(uuid.UUID(memory_id))
        if result is None:
            return {"error": "Memory not found"}
        return result


@mcp.tool(name="memory_delete")
async def delete_memory(memory_id: str) -> Any:
    """When to use:
    Remove stale, incorrect, or unsafe memory from active use.

    Inputs:
    - memory_id: Memory UUID.

    Returns:
    - deleted: Boolean result.

    Common mistakes:
    - Keeping known-bad memory active after confirming it is wrong.
    """
    factory = _get_session_factory()
    async with factory() as db:
        svc = MemoryService(db)
        deleted = await svc.delete(uuid.UUID(memory_id))
        await db.commit()
        return {"deleted": deleted}


@mcp.tool(name="memory_reindex")
async def reindex_memory(
    limit: int = 100,
    agent_id: str | None = None,
    memory_type: str | None = None,
    metadata_filters: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> Any:
    """When to use:
    Regenerate missing embeddings after outages or degraded search quality.

    Inputs:
    - limit: Max rows to process.
    - agent_id: Optional scope; auto-filled from context.
    - memory_type: Optional scope.
    - metadata_filters: Optional scope; project_id auto-filled from context.
    - dry_run: If true, report candidates without writing.

    Returns:
    - Reindex report with scanned/reindexed/failed counts.

    Common mistakes:
    - Running large writes without dry_run first.
    """
    context = await _get_active_mcp_context()
    effective_agent_id = agent_id or context.get("agent_id")
    effective_filters = dict(metadata_filters or {})
    if "project_id" not in effective_filters and context.get("project_id"):
        effective_filters["project_id"] = context["project_id"]

    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        svc = MemoryService(db, short_term)
        try:
            parsed_agent_id = uuid.UUID(effective_agent_id) if effective_agent_id else None
        except ValueError as e:
            return {"error": f"Invalid agent_id: {e}"}
        result = await svc.reindex_embeddings(
            limit=limit,
            agent_id=parsed_agent_id,
            memory_type=memory_type,
            metadata_filters=effective_filters or None,
            dry_run=dry_run,
        )
        await db.commit()
        return result


@mcp.tool(name="agent_run")
async def run_agent(
    input: str,
    agent_id: str | None = None,
    session_id: str | None = None,
    background: bool = True,
) -> Any:
    """When to use:
    Execute a real task through the configured agent runtime.

    Inputs:
    - input: User/task instruction.
    - agent_id: Optional; auto-filled from context.
    - session_id: Optional; auto-filled from context.
    - background: Run asynchronously in background and return run_id immediately.

    Returns:
    - Agent output, message trace, tool calls, and effective session identifiers.

    Common mistakes:
    - Calling without agent_id and without project/agent context.
    - Treating this as simulation instead of state-mutating execution.
    """
    context = await _get_active_mcp_context()
    effective_agent_id = agent_id or context.get("agent_id")
    effective_project_id = context.get("project_id")
    project_agents: dict[str, dict[str, Any]] = {}
    auto_selected_project_agent = False
    if not effective_agent_id:
        if not effective_project_id:
            return {
                "error": (
                    "agent_id is required (pass explicitly or set via context_set). "
                    "Or set project_id in context to auto-select a project-scoped planner agent."
                )
            }
    effective_session_id = session_id or context.get("session_id")

    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        svc = AgentService(db, short_term)
        if not effective_agent_id:
            project_name = await _resolve_project_name(db, effective_project_id)
            project_agents = await svc.ensure_project_agents(
                project_id=str(effective_project_id),
                project_name=project_name,
            )
            planner = project_agents.get("planner")
            if not planner:
                return {"error": "Failed to resolve project-scoped planner agent"}
            effective_agent_id = str(planner["id"])
            auto_selected_project_agent = True

        try:
            parsed_agent_id = uuid.UUID(effective_agent_id)
            parsed_session_id = (
                uuid.UUID(effective_session_id) if effective_session_id else None
            )
        except ValueError as e:
            return {"error": f"Invalid UUID: {e}"}
        if background:
            result = await svc.enqueue_run(
                agent_id=parsed_agent_id,
                input_text=input,
                session_id=parsed_session_id,
                context={"project_id": str(effective_project_id)} if effective_project_id else None,
            )
            next_context = await _get_active_mcp_context()
            next_context["agent_id"] = effective_agent_id
            if effective_project_id:
                next_context["project_id"] = str(effective_project_id)
            await _set_active_mcp_context(next_context)
            await db.commit()
            if auto_selected_project_agent:
                result["auto_selected_agent"] = True
                result["project_agents"] = {
                    role: info.get("id") for role, info in project_agents.items()
                }
            return result

        result = await svc.run_agent(
            agent_id=parsed_agent_id,
            input_text=input,
            session_id=parsed_session_id,
            context={"project_id": str(effective_project_id)} if effective_project_id else None,
        )
        next_context = await _get_active_mcp_context()
        next_context["agent_id"] = result.get("agent_id")
        next_context["session_id"] = result.get("session_id")
        if effective_project_id:
            next_context["project_id"] = str(effective_project_id)
        await _set_active_mcp_context(next_context)
        await db.commit()
        if auto_selected_project_agent:
            result["auto_selected_agent"] = True
            result["project_agents"] = {
                role: info.get("id") for role, info in project_agents.items()
            }
        return result


@mcp.tool(name="agent_get_state")
async def get_agent_state(agent_id: str | None = None) -> Any:
    """When to use:
    Read latest agent state before resume, debug, or delegation.

    Inputs:
    - agent_id: Optional; auto-filled from context.

    Returns:
    - Agent state dictionary or not-found error.

    Common mistakes:
    - Assuming last state without reading it first.
    """
    context = await _get_active_mcp_context()
    effective_agent_id = agent_id or context.get("agent_id")
    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        svc = AgentService(db, short_term)
        if not effective_agent_id and context.get("project_id"):
            project_name = await _resolve_project_name(db, str(context["project_id"]))
            project_agents = await svc.ensure_project_agents(
                project_id=str(context["project_id"]),
                project_name=project_name,
            )
            planner = project_agents.get("planner")
            if planner:
                effective_agent_id = str(planner["id"])
                context["agent_id"] = effective_agent_id
                await _set_active_mcp_context(context)

        if not effective_agent_id:
            return {
                "error": (
                    "agent_id is required (pass explicitly or set via context_set). "
                    "Or set project_id in context to auto-select a project-scoped planner agent."
                )
            }
        try:
            parsed_agent_id = uuid.UUID(effective_agent_id)
        except ValueError as e:
            return {"error": f"Invalid agent_id: {e}"}
        state = await svc.get_agent_state(parsed_agent_id)
        return state or {"error": "Agent not found"}


@mcp.tool(name="agent_run_status")
async def get_agent_run_status(run_id: str) -> Any:
    """When to use:
    Poll asynchronous agent run status after calling agent_run(background=true).

    Inputs:
    - run_id: Async run UUID returned by agent_run.

    Returns:
    - pending/running/completed/failed payload with result or error.

    Common mistakes:
    - Expecting immediate output from background runs without polling status.
    """
    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        svc = AgentService(db, short_term)
        try:
            parsed_run_id = uuid.UUID(run_id)
        except ValueError as e:
            return {"error": f"Invalid run_id: {e}"}
        status = await svc.get_run_status(parsed_run_id)
        if status is None:
            return {"error": "Agent run not found"}
        return status


@mcp.tool(name="db_query")
async def query_db(sql: str, max_rows: int = _MAX_RESULT_ROWS) -> Any:
    """When to use:
    Verify facts directly from database truth.

    Inputs:
    - sql: Read-only SELECT statement.
    - max_rows: Row limit for response payload (1..1000).

    Returns:
    - columns/rows/count/truncated payload.

    Common mistakes:
    - Sending non-SELECT SQL or querying non-whitelisted tables.
    - Including multiple statements or blocked clauses.
    """
    settings = get_settings()
    if not settings.mcp_db_query_enabled:
        return {
            "error": (
                "db_query is disabled by configuration. "
                "Set MCP_DB_QUERY_ENABLED=true to enable it."
            )
        }

    if max_rows < 1 or max_rows > _MAX_RESULT_ROWS_HARD:
        return {"error": f"max_rows must be between 1 and {_MAX_RESULT_ROWS_HARD}"}

    sql = sql.strip()
    if len(sql) > _MAX_QUERY_LENGTH:
        return {"error": f"Query too long (max {_MAX_QUERY_LENGTH} chars)"}

    # Allow optional trailing semicolon(s), but disallow internal statement separators.
    sql = re.sub(r";+\s*$", "", sql).strip()
    if not sql:
        return {"error": "Empty SQL query"}
    if ";" in sql:
        return {
            "error": (
                "Multiple statements are not allowed. "
                "Send exactly one SELECT statement."
            )
        }

    sql_upper = sql.upper()
    if not sql_upper.startswith("SELECT"):
        return {
            "error": (
                "Only SELECT queries are allowed in db_query. "
                "For write/update operations use dedicated API tools."
            )
        }

    # Block dangerous keywords using word boundaries
    dangerous = [
        "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE",
        "TRUNCATE", "EXEC", "GRANT", "REVOKE", "COPY",
    ]
    for kw in dangerous:
        if re.search(rf"\b{kw}\b", sql_upper):
            return {
                "error": (
                    f"Forbidden keyword: {kw}. "
                    "db_query supports read-only SELECT checks only."
                )
            }

    # Block subqueries, unions, CTEs.
    for blocked in ["UNION", "INTO", "RETURNING", "WITH"]:
        if re.search(rf"\b{blocked}\b", sql_upper):
            return {
                "error": (
                    f"Forbidden clause: {blocked}. "
                    "Use a simple single-table SELECT or dedicated MCP tools."
                )
            }

    # Table/schema allowlist: project tables in `public` + metadata schemas
    table_refs = _extract_table_refs(sql)
    for schema, table in table_refs:
        if schema in _ALLOWED_METADATA_SCHEMAS:
            continue
        if schema == "public" and table in _ALLOWED_PUBLIC_TABLES:
            continue
        table_name = f"{schema}.{table}"
        allowed_public = ", ".join(sorted(_ALLOWED_PUBLIC_TABLES))
        allowed_meta = ", ".join(sorted(_ALLOWED_METADATA_SCHEMAS))
        return {
            "error": (
                f"Table not allowed: {table_name}. "
                f"Allowed public tables: {allowed_public}. "
                f"Allowed metadata schemas: {allowed_meta}."
            )
        }

    factory = _get_session_factory()
    async with factory() as db:
        from sqlalchemy import text
        result = await db.execute(text(sql))
        columns = list(result.keys())
        rows = result.fetchmany(max_rows)
        payload_rows: list[dict[str, Any]] = []
        for row in rows:
            if hasattr(row, "_mapping"):
                payload_rows.append(dict(row._mapping))
            else:
                payload_rows.append(dict(zip(columns, row)))
        return {
            "columns": columns,
            "rows": payload_rows,
            "count": len(rows),
            "truncated": len(rows) == max_rows,
            "max_rows": max_rows,
            "table_refs": [f"{schema}.{table}" for schema, table in table_refs],
        }


@mcp.tool(name="embeddings_create")
async def create_embeddings(text: str) -> Any:
    """When to use:
    Build semantic vectors for custom matching and ranking workflows.

    Inputs:
    - text: Raw text to embed.

    Returns:
    - embedding vector, dimension, provider.

    Common mistakes:
    - Comparing semantic similarity without vectorizing both sides.
    """
    provider = get_embedding_provider()
    embedding = await provider.embed(text)
    return {
        "embedding": embedding,
        "dimension": len(embedding),
        "provider": get_settings().embedding_provider,
    }


@mcp.tool(name="orchestration_run")
async def run_orchestration(
    input: str,
    workflow: str | None = None,
    auto_route: bool = False,
    background: bool = True,
    project_id: str | None = None,
) -> Any:
    """When to use:
    Run multi-step workflows with routing, retries, and coordination.

    Inputs:
    - input: Workflow task description.
    - workflow: Optional workflow name.
    - auto_route: Let system pick workflow automatically.
    - background: Run asynchronously in background and return pending status.

    Returns:
    - run_id, status, and workflow result.

    Common mistakes:
    - Manually simulating orchestration in a single agent call.
    """
    from app.orchestration.service import OrchestrationService
    context = await _get_active_mcp_context()
    effective_project_id = project_id or context.get("project_id")
    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        orch_svc = OrchestrationService(db, short_term)
        if background:
            result = await orch_svc.enqueue_run(
                workflow_name=workflow,
                input_text=input,
                auto_route=auto_route,
                project_id=effective_project_id,
            )
        else:
            result = await orch_svc.start_run(
                workflow_name=workflow,
                input_text=input,
                auto_route=auto_route,
                project_id=effective_project_id,
            )
        await db.commit()
        if effective_project_id:
            context["project_id"] = str(effective_project_id)
            await _set_active_mcp_context(context)
        return {
            "run_id": result.get("run_id"),
            "workflow": result.get("workflow"),
            "status": result.get("status"),
            "result": result.get("result"),
            "queued": result.get("queued", False),
            "project_id": str(effective_project_id) if effective_project_id else None,
        }


@mcp.tool(name="project_analyze")
async def analyze_project(
    project_path: str | None = None,
    project_name: str | None = None,
    force_reindex: bool = False,
) -> Any:
    """When to use:
    Ingest or refresh project structure in Postgres.

    Inputs:
    - project_path: Optional filesystem path to project root. If omitted,
      tool tries MCP context and configured env candidates.
    - project_name: Optional display name.
    - force_reindex: Rebuild existing project records.

    Returns:
    - project_id, analysis status/timestamp, summary, metadata.

    Common mistakes:
    - Skipping analysis and expecting graph tools to work on an unknown project.
    """
    from app.indexing import ProjectIndexer

    context = await _get_active_mcp_context()
    effective_project_path = (project_path or context.get("project_path") or "").strip()
    detected_from = "input_or_context"
    if not effective_project_path:
        env_path = _auto_project_path_from_env()
        if env_path:
            effective_project_path = env_path
            detected_from = "env"

    if not effective_project_path:
        settings = get_settings()
        return {
            "error": (
                "project_path is required. Pass it explicitly, call context_set with project_path, "
                "or configure autonomous env vars via "
                f"AUTONOMOUS_PROJECT_ENV_KEYS ({settings.autonomous_project_env_keys}) "
                "and AUTONOMOUS_PROJECT_FALLBACK_PATH."
            )
        }

    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        indexer = ProjectIndexer(db)
        project = await indexer.index_project(
            project_path=effective_project_path,
            project_name=project_name,
            force_reindex=force_reindex,
        )
        agent_service = AgentService(db, short_term)
        project_agents = await agent_service.ensure_project_agents(
            project_id=str(project.id),
            project_name=project.name,
        )
        await db.commit()
        planner_agent_id = project_agents.get("planner", {}).get("id")
        context["project_id"] = str(project.id)
        context["project_path"] = project.path
        context["project_path_source"] = detected_from
        if planner_agent_id:
            context["agent_id"] = planner_agent_id
        await _set_active_mcp_context(context)
        summary = await indexer.get_project_summary(str(project.id))
        brain_memory = {"stored": 0, "created": 0, "deduplicated": 0, "memory_ids": []}
        try:
            memory_service = MemoryService(db, short_term)
            brain_memory = await persist_project_memories(
                memory_service,
                summary,
                project_id=str(project.id),
                project_name=project.name,
                project_path=project.path,
            )
            await db.commit()
        except Exception as memory_error:
            logger.warning(
                "Failed to persist project memories for project %s: %s",
                project.id,
                memory_error,
            )
            if hasattr(db, "rollback"):
                await db.rollback()
        return {
            "project_id": str(project.id),
            "project_name": project.name,
            "analysis_status": project.analysis_status,
            "analysis_timestamp": project.last_analyzed.isoformat()
            if project.last_analyzed
            else "",
            "summary": summary,
            "metadata": {
                "total_files": project.total_files,
                "total_lines": project.total_lines,
                "architecture_type": project.architecture_type,
                "tech_stack": project.tech_stack,
                "frameworks": project.frameworks,
                "languages": project.languages,
                "databases": project.databases,
                "build_tools": project.build_tools,
            },
            "brain_memory": brain_memory,
            "project_agents": {
                role: {
                    "id": info.get("id"),
                    "name": info.get("name"),
                    "project_role": (
                        info.get("config", {}).get("project_role")
                        if isinstance(info.get("config"), dict)
                        else None
                    ),
                }
                for role, info in project_agents.items()
            },
            "default_agent_id": planner_agent_id,
        }


@mcp.tool(name="project_list")
async def list_projects(
    limit: int = 50,
    offset: int = 0,
) -> Any:
    """When to use:
    Discover available projects and obtain project_id values.

    Inputs:
    - limit: Max rows.
    - offset: Pagination offset.

    Returns:
    - List of project records.

    Common mistakes:
    - Hardcoding project_id instead of resolving it first.
    """
    from sqlalchemy import select
    from app.core.models import Project

    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200
    if offset < 0:
        offset = 0

    factory = _get_session_factory()
    async with factory() as db:
        stmt = (
            select(Project)
            .order_by(Project.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        projects = result.scalars().all()
        return [
            {
                "id": str(project.id),
                "name": project.name,
                "path": project.path,
                "analysis_status": project.analysis_status,
                "last_analyzed": project.last_analyzed.isoformat()
                if project.last_analyzed
                else None,
                "total_files": project.total_files,
                "total_lines": project.total_lines,
                "architecture_type": project.architecture_type,
                "languages": project.languages,
            }
            for project in projects
        ]


@mcp.tool(name="project_agents_bootstrap")
async def bootstrap_project_agents(
    project_id: str | None = None,
    project_name: str | None = None,
    set_active_planner: bool = True,
) -> Any:
    """When to use:
    Ensure role-based agents exist for one project (planner/coder/reviewer/memory).

    Inputs:
    - project_id: Optional; auto-filled from context.
    - project_name: Optional display name for agent metadata.
    - set_active_planner: If true, context.agent_id will point to planner role.

    Returns:
    - project_id and role->agent mapping.
    """
    context = await _get_active_mcp_context()
    effective_project_id = project_id or context.get("project_id")
    if not effective_project_id:
        return {"error": "project_id is required (pass explicitly or set via context_set/project_analyze)"}

    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        if not project_name:
            project_name = await _resolve_project_name(db, str(effective_project_id))
        svc = AgentService(db, short_term)
        agents = await svc.ensure_project_agents(
            project_id=str(effective_project_id),
            project_name=project_name,
        )
        await db.commit()

    planner_id = str(agents.get("planner", {}).get("id")) if agents.get("planner") else None
    if set_active_planner and planner_id:
        context["project_id"] = str(effective_project_id)
        context["agent_id"] = planner_id
        await _set_active_mcp_context(context)

    return {
        "project_id": str(effective_project_id),
        "project_name": project_name,
        "default_agent_id": planner_id,
        "agents": {
            role: {
                "id": info.get("id"),
                "name": info.get("name"),
                "project_role": (
                    info.get("config", {}).get("project_role")
                    if isinstance(info.get("config"), dict)
                    else None
                ),
            }
            for role, info in agents.items()
        },
    }


@mcp.tool(name="project_components")
async def list_project_components(
    project_id: str | None = None,
    query: str = "",
    component_type: str | None = None,
    language: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Any:
    """When to use:
    Resolve component IDs for graph impact/path/neighbors calls.

    Inputs:
    - project_id: Optional; auto-filled from context.
    - query: Name/path search text.
    - component_type/language: Optional filters.
    - limit/offset: Pagination.

    Returns:
    - List of component records with IDs and metrics.

    Common mistakes:
    - Running graph queries with unknown component IDs.
    """
    from app.indexing import ProjectIndexer

    context = await _get_active_mcp_context()
    effective_project_id = project_id or context.get("project_id")
    if not effective_project_id:
        return {"error": "project_id is required (pass explicitly or set via context_set/project_analyze)"}

    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500
    if offset < 0:
        offset = 0

    factory = _get_session_factory()
    async with factory() as db:
        indexer = ProjectIndexer(db)
        components = await indexer.search_components(
            project_id=effective_project_id,
            query=query,
            component_type=component_type,
            language=language,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "id": str(comp.id),
                "name": comp.name,
                "type": comp.type,
                "path": comp.relative_path,
                "language": comp.language,
                "line_count": comp.line_count,
                "complexity_score": comp.complexity_score,
                "dependencies": comp.dependencies,
                "exports": comp.exports,
            }
            for comp in components
        ]


@mcp.tool(name="project_dependencies_analyze")
async def analyze_project_dependencies(
    project_id: str | None = None,
    include_impact_analysis: bool = True,
    component_id: str | None = None,
) -> Any:
    """When to use:
    Run structural dependency diagnostics for a project.

    Inputs:
    - project_id: Optional; auto-filled from context.
    - include_impact_analysis: Include component impact section.
    - component_id: Target component for impact.

    Returns:
    - Dependency statistics, layers, SCC/cycle signals, optional impact.

    Common mistakes:
    - Expecting component impact without passing component_id.
    """
    from app.dependencies import GraphDependencyService

    context = await _get_active_mcp_context()
    effective_project_id = project_id or context.get("project_id")
    if not effective_project_id:
        return {"error": "project_id is required (pass explicitly or set via context_set/project_analyze)"}

    factory = _get_session_factory()
    async with factory() as db:
        svc = GraphDependencyService(db)
        return await svc.dependencies_analyze_compat(
            project_id=effective_project_id,
            include_impact_analysis=include_impact_analysis,
            component_id=component_id,
        )


@mcp.tool(name="project_graph_sync")
async def sync_project_graph(
    project_id: str | None = None,
    changed_files: list[str] | None = None,
) -> Any:
    """When to use:
    Refresh graph read-model from Postgres source-of-truth.

    Inputs:
    - project_id: Optional; auto-filled from context.
    - changed_files: Optional list for incremental sync.

    Returns:
    - Sync report: mode, nodes/edges, timestamps, backend.

    Common mistakes:
    - Querying graph endpoints before first sync.
    """
    from app.dependencies import GraphDependencyService

    context = await _get_active_mcp_context()
    effective_project_id = project_id or context.get("project_id")
    if not effective_project_id:
        return {"error": "project_id is required (pass explicitly or set via context_set/project_analyze)"}

    factory = _get_session_factory()
    async with factory() as db:
        svc = GraphDependencyService(db)
        result = await svc.sync_project_graph(
            project_id=effective_project_id,
            changed_files=changed_files or [],
        )
        await db.commit()
        context["project_id"] = effective_project_id
        await _set_active_mcp_context(context)
        return result


@mcp.tool(name="project_graph_impact")
async def project_graph_impact(
    component_id: str,
    project_id: str | None = None,
) -> Any:
    """When to use:
    Estimate blast radius of changing one component.

    Inputs:
    - component_id: Target component.
    - project_id: Optional; auto-filled from context.

    Returns:
    - Direct/indirect impact counts and affected components.

    Common mistakes:
    - Running before sync or with unresolved component_id.
    """
    from app.dependencies import GraphDependencyService

    context = await _get_active_mcp_context()
    effective_project_id = project_id or context.get("project_id")
    if not effective_project_id:
        return {"error": "project_id is required (pass explicitly or set via context_set/project_analyze)"}

    factory = _get_session_factory()
    async with factory() as db:
        svc = GraphDependencyService(db)
        return await svc.graph_impact(project_id=effective_project_id, component_id=component_id)


@mcp.tool(name="project_graph_path")
async def project_graph_path(
    from_component_id: str,
    to_component_id: str,
    max_depth: int = 15,
    project_id: str | None = None,
) -> Any:
    """When to use:
    Explain why two components are connected.

    Inputs:
    - from_component_id: Source component.
    - to_component_id: Destination component.
    - max_depth: Path depth bound.
    - project_id: Optional; auto-filled from context.

    Returns:
    - Path payload and found/not-found flags.

    Common mistakes:
    - Using too small max_depth for distant dependencies.
    """
    from app.dependencies import GraphDependencyService

    context = await _get_active_mcp_context()
    effective_project_id = project_id or context.get("project_id")
    if not effective_project_id:
        return {"error": "project_id is required (pass explicitly or set via context_set/project_analyze)"}

    factory = _get_session_factory()
    async with factory() as db:
        svc = GraphDependencyService(db)
        return await svc.graph_path(
            project_id=effective_project_id,
            from_component_id=from_component_id,
            to_component_id=to_component_id,
            max_depth=max_depth,
        )


@mcp.tool(name="project_graph_neighbors")
async def project_graph_neighbors(
    component_id: str | None = None,
    project_id: str | None = None,
    depth: int = 1,
) -> Any:
    """When to use:
    Explore local dependency neighborhood around a component.

    Inputs:
    - component_id: Optional target component. If omitted, tool picks a default project component.
    - project_id: Optional; auto-filled from context.
    - depth: Traversal radius.

    Returns:
    - Neighbor summary at requested depth.

    Common mistakes:
    - Using large depth by default and overfetching.
    """
    from app.dependencies import GraphDependencyService

    context = await _get_active_mcp_context()
    effective_project_id = project_id or context.get("project_id")
    if not effective_project_id:
        return {"error": "project_id is required (pass explicitly or set via context_set/project_analyze)"}

    factory = _get_session_factory()
    async with factory() as db:
        effective_component_id = component_id or context.get("component_id")
        if not effective_component_id:
            effective_component_id = await _resolve_default_component_id(db, effective_project_id)
        if not effective_component_id:
            return {
                "error": (
                    "component_id is required because project has no indexed components. "
                    "Run project_analyze first."
                )
            }

        context["component_id"] = effective_component_id
        await _set_active_mcp_context(context)
        svc = GraphDependencyService(db)
        return await svc.graph_neighbors(
            project_id=effective_project_id,
            component_id=effective_component_id,
            depth=depth,
        )


def configure_mcp(app: FastAPI) -> None:
    """Register MCP routes directly on the FastAPI application with robust handlers."""
    from mcp.server.sse import SseServerTransport
    from starlette.responses import Response

    # Initialize transport with the advertised message path
    sse_transport = SseServerTransport("/mcp/messages")
    # Per-session guard to preserve request ordering semantics for clients
    # that pipeline requests over multiple concurrent HTTP POSTs.
    _session_send_locks: dict[uuid.UUID, anyio.Lock] = {}
    _session_initialized: set[uuid.UUID] = set()

    async def mcp_sse_handler(scope, receive, send):
        """Handle GET /mcp/sse — starts the SSE stream."""
        try:
            async with sse_transport.connect_sse(scope, receive, send) as streams:
                await mcp._mcp_server.run(
                    streams[0],
                    streams[1],
                    mcp._mcp_server.create_initialization_options(),
                )
        except _DISCONNECT_EXCEPTIONS:
            logger.debug("MCP SSE connection closed gracefully")
        except Exception as e:
            if _is_expected_disconnect(e):
                logger.debug("MCP SSE connection closed gracefully (grouped)")
                return
            logger.error(f"MCP SSE unexpected error: {e}", exc_info=True)

    async def mcp_messages_handler(scope, receive, send):
        """Handle POST /mcp/messages — receives client messages for a session."""
        try:
            request = Request(scope, receive)
            session_id_param = request.query_params.get("session_id")
            if session_id_param is None:
                logger.warning("Received request without session_id")
                response = Response("session_id is required", status_code=400)
                await response(scope, receive, send)
                return

            try:
                session_id = uuid.UUID(hex=session_id_param)
            except ValueError:
                logger.warning("Received invalid session_id: %s", session_id_param)
                response = Response("Invalid session ID", status_code=400)
                await response(scope, receive, send)
                return

            writer = sse_transport._read_stream_writers.get(session_id)
            if writer is None:
                logger.warning("Could not find session for ID: %s", session_id)
                response = Response("Could not find session", status_code=404)
                await response(scope, receive, send)
                return

            payload = await request.json()
            try:
                message = mcp_types.JSONRPCMessage.model_validate(payload)
            except ValidationError as err:
                logger.error("Failed to parse MCP message: %s", err)
                response = Response("Could not parse message", status_code=400)
                await response(scope, receive, send)
                await writer.send(err)
                return

            lock = _session_send_locks.setdefault(session_id, anyio.Lock())
            async with lock:
                # Enforce initialization ordering to avoid session task-group
                # failures when clients issue concurrent pipelined requests.
                if isinstance(message.root, mcp_types.JSONRPCRequest):
                    if message.root.method == "initialize":
                        _session_initialized.discard(session_id)
                        try:
                            params = payload.get("params") if isinstance(payload, dict) else {}
                            candidates = extract_project_paths_from_mcp_params(params)
                            if candidates:
                                await _capture_project_path_in_context(
                                    candidates[0],
                                    source="mcp_initialize",
                                )
                                logger.info(
                                    "Captured project_path from MCP initialize: %s",
                                    candidates[0],
                                )
                        except Exception as capture_error:
                            logger.debug(
                                "Failed to capture project_path from initialize payload: %s",
                                capture_error,
                            )
                    elif session_id not in _session_initialized:
                        logger.warning(
                            "Rejected pre-initialize MCP request: method=%s session_id=%s",
                            message.root.method,
                            session_id.hex,
                        )
                        response = Response("Initialize required", status_code=409)
                        await response(scope, receive, send)
                        return

                # Keep HTTP-level compatibility for clients that do not accept 202.
                response = Response("Accepted", status_code=200)
                await response(scope, receive, send)
                await writer.send(message)

                # Compatibility shim: synthesize initialized notification right
                # after initialize, before any queued follow-up request.
                if (
                    isinstance(message.root, mcp_types.JSONRPCRequest)
                    and message.root.method == "initialize"
                ):
                    await writer.send(
                        mcp_types.JSONRPCMessage(
                            root=mcp_types.JSONRPCNotification(
                                jsonrpc="2.0",
                                method="notifications/initialized",
                                params={},
                            )
                        )
                    )
                    _session_initialized.add(session_id)
                elif (
                    isinstance(message.root, mcp_types.JSONRPCNotification)
                    and message.root.method == "notifications/initialized"
                ):
                    _session_initialized.add(session_id)
        except _DISCONNECT_EXCEPTIONS:
            logger.debug("MCP message connection closed gracefully")
        except Exception as e:
            if _is_expected_disconnect(e):
                logger.debug("MCP message connection closed gracefully (grouped)")
                return
            logger.error(f"MCP Message handler error: {e}", exc_info=True)

    async def mcp_options_handler(scope, receive, send):
        """Handle OPTIONS for MCP endpoints (CORS)."""
        resp = Response(status_code=204)
        await resp(scope, receive, send)

    class ASGIMCPHandler:
        """Wrapper to force Starlette to treat the handler as a raw ASGI app."""
        def __init__(self, handler):
            self.handler = handler
        async def __call__(self, scope, receive, send):
            await self.handler(scope, receive, send)

    # Register using explicit Starlette Routes with the ASGI wrapper
    # This avoids TypeError (introspection) and 307 (redirects)
    # We allow POST on BOTH paths to accommodate various client behaviors
    app.router.add_route("/mcp/sse", ASGIMCPHandler(mcp_sse_handler), methods=["GET"])
    app.router.add_route("/mcp/sse", ASGIMCPHandler(mcp_messages_handler), methods=["POST"])
    app.router.add_route("/mcp/messages", ASGIMCPHandler(mcp_messages_handler), methods=["POST"])
    
    # Global OPTIONS and even DELETE (seen in logs) handlers
    app.router.add_route("/mcp/sse", ASGIMCPHandler(mcp_options_handler), methods=["OPTIONS", "DELETE"])
    app.router.add_route("/mcp/messages", ASGIMCPHandler(mcp_options_handler), methods=["OPTIONS", "DELETE"])


def create_mcp_app() -> Any:
    """
    Deprecated: MCP is now mounted directly via configure_mcp.
    Kept for backward compatibility during migration.
    """
    # Return a dummy Starlette app that just warns
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    return Starlette(routes=[], on_startup=[lambda: logger.warning("create_mcp_app is deprecated, use configure_mcp")])
