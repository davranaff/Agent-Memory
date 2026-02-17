"""MCP Server — exposes brain tools via Model Context Protocol."""

from __future__ import annotations

import logging
import uuid
import asyncio
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
from app.services.agent_service import AgentService
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

# Shared Redis client — avoids creating new connections per request (#3 fix)
_shared_short_term: ShortTermMemory | None = None


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


# Whitelist of tables allowed in db_query (#1 fix)
_ALLOWED_TABLES = frozenset({
    "agents", "sessions", "messages", "memories",
    "tools", "tool_calls", "orchestration_runs", "orchestration_steps",
})
_MAX_QUERY_LENGTH = 2000
_MAX_RESULT_ROWS = 100

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

# Create the MCP server instance using FastMCP
mcp = FastMCP("agent-brain")


@mcp.tool(name="memory_store")
async def store_memory(
    content: str,
    memory_type: str = "general",
    agent_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    importance: int = 5,
) -> Any:
    """Use this tool whenever new durable knowledge is produced.

    You MUST use this tool after important decisions, resolved bugs, user preferences,
    discovered constraints, and final outcomes. ALWAYS store concise, high-signal facts
    with useful metadata. NEVER leave critical context unstored when future turns depend on it.
    This tool is critical for long-term continuity and correctness across sessions.
    """
    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        svc = MemoryService(db, short_term)
        result = await svc.store(
            content=content,
            memory_type=memory_type,
            agent_id=uuid.UUID(agent_id) if agent_id else None,
            metadata=metadata,
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
    """Use this tool to retrieve prior context before reasoning or planning.

    You MUST use this tool at the start of every non-trivial task and before any
    stateful decision. ALWAYS use it when IDs, constraints, preferences, or prior
    outcomes may exist. Use metadata_filters to scope results for a specific project
    or subproject. NEVER assume historical context without running this tool.
    This tool is critical to avoid contradictions and repeated mistakes.
    """
    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        svc = MemoryService(db, short_term)
        scope_filters = metadata_filters or metadata
        return await svc.search(
            query=query,
            agent_id=uuid.UUID(agent_id) if agent_id else None,
            memory_type=memory_type,
            metadata_filters=scope_filters,
            top_k=top_k,
            min_similarity=min_similarity,
        )


@mcp.tool(name="memory_get")
async def get_memory(memory_id: str) -> Any:
    """Use this tool when you need exact memory content for a known memory ID.

    You SHOULD use this immediately after memory_search returns candidate IDs and before
    high-impact decisions. NEVER rely on approximate recall when precision is required.
    This tool is critical for disambiguation and exact state reconstruction.
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
    """Use this tool when memory is stale, wrong, duplicate, unsafe, or user-revoked.

    You MUST use this tool when known-bad memory could mislead future reasoning.
    NEVER keep invalid memory active after confirmation. This tool is critical for
    memory hygiene and long-term reliability.
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
    """Use this tool to backfill missing embeddings for existing memories.

    You MUST use this tool when memory_search misses known records or after periods
    of embedding-provider failures. Use metadata_filters to target a project/subproject
    safely. Run with dry_run=true first on large datasets. This tool is critical for
    search quality and recall in multi-project memory stores.
    """
    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        svc = MemoryService(db, short_term)
        result = await svc.reindex_embeddings(
            limit=limit,
            agent_id=uuid.UUID(agent_id) if agent_id else None,
            memory_type=memory_type,
            metadata_filters=metadata_filters,
            dry_run=dry_run,
        )
        await db.commit()
        return result


@mcp.tool(name="agent_run")
async def run_agent(
    agent_id: str,
    input: str,
    session_id: str | None = None,
) -> Any:
    """Use this tool to execute a concrete agent task with real runtime state.

    You MUST use this tool when work requires actual agent execution, not simulation.
    ALWAYS provide the correct agent_id and pass session_id when continuing context.
    This tool is critical because it performs real work and updates live state.
    """
    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        svc = AgentService(db, short_term)
        result = await svc.run_agent(
            agent_id=uuid.UUID(agent_id),
            input_text=input,
            session_id=uuid.UUID(session_id) if session_id else None,
        )
        await db.commit()
        return result


@mcp.tool(name="agent_get_state")
async def get_agent_state(agent_id: str) -> Any:
    """Use this tool to read the current state of a specific agent.

    You MUST use this before planning, resuming, debugging, or delegating agent work.
    NEVER assume agent state from prior turns without checking. This tool is critical
    for safe coordination and correct next actions.
    """
    factory = _get_session_factory()
    async with factory() as db:
        svc = AgentService(db)
        state = await svc.get_agent_state(uuid.UUID(agent_id))
        return state or {"error": "Agent not found"}


@mcp.tool(name="db_query")
async def query_db(sql: str) -> Any:
    """Use this tool whenever an answer depends on database truth.

    You MUST use this tool for facts about records, counts, timestamps, status, and
    relationships. NEVER guess database content. ALWAYS send a safe read-only SELECT.
    This tool is critical because database evidence overrides speculation.
    """
    sql = sql.strip()
    if len(sql) > _MAX_QUERY_LENGTH:
        return {"error": f"Query too long (max {_MAX_QUERY_LENGTH} chars)"}

    sql_upper = sql.upper()
    if not sql_upper.startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed"}

    # Block dangerous keywords using word boundaries
    import re
    dangerous = [
        "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE",
        "TRUNCATE", "EXEC", "GRANT", "REVOKE", "COPY",
    ]
    for kw in dangerous:
        if re.search(rf"\b{kw}\b", sql_upper):
            return {"error": f"Forbidden keyword: {kw}"}

    # Block subqueries, unions, CTEs, and multiple statements
    if ";" in sql:
        return {"error": "Multiple statements are not allowed"}
    for blocked in ["UNION", "INTO", "RETURNING", "WITH"]:
        if re.search(rf"\b{blocked}\b", sql_upper):
            return {"error": f"Forbidden clause: {blocked}"}

    # Table whitelist: extract FROM/JOIN targets
    import re
    table_refs = re.findall(
        r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE
    )
    for table in table_refs:
        if table.lower() not in _ALLOWED_TABLES:
            return {"error": f"Table not allowed: {table}"}

    factory = _get_session_factory()
    async with factory() as db:
        from sqlalchemy import text
        result = await db.execute(text(sql))
        rows = result.fetchmany(_MAX_RESULT_ROWS)
        columns = list(result.keys()) if rows else []
        return {
            "columns": columns,
            "rows": [dict(zip(columns, row)) for row in rows],
            "count": len(rows),
            "truncated": len(rows) == _MAX_RESULT_ROWS,
        }


@mcp.tool(name="embeddings_create")
async def create_embeddings(text: str) -> Any:
    """Use this tool for semantic matching, clustering, and relevance ranking.

    You SHOULD use this whenever meaning-based comparison is required beyond keywords.
    NEVER approximate semantic distance without embeddings when retrieval quality matters.
    This tool is critical for robust semantic reasoning.
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
) -> Any:
    """Use this tool for multi-step, multi-agent, or parallel execution.

    You MUST use this tool when the task needs workflow routing, retries, or coordinated
    execution across multiple agents. NEVER emulate orchestration manually in one answer.
    This tool is critical for reliable large-task completion.
    """
    from app.orchestration.service import OrchestrationService
    factory = _get_session_factory()
    short_term = _get_short_term()
    async with factory() as db:
        orch_svc = OrchestrationService(db, short_term)
        result = await orch_svc.start_run(
            workflow_name=workflow,
            input_text=input,
            auto_route=auto_route,
        )
        await db.commit()
        return {
            "run_id": result.get("run_id"),
            "status": result.get("status"),
            "result": result.get("result"),
        }


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
