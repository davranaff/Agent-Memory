"""Agent service — CRUD and run delegation to LangGraph agent."""

from __future__ import annotations

import logging
import uuid
from typing import Any
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.prompts import get_default_system_prompt
from app.core.models import Agent, Project
from app.db.session import _get_session_factory
from app.memory.short_term import ShortTermMemory
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)
_AGENT_RUN_TTL_SECONDS = 60 * 60 * 24
_BACKGROUND_AGENT_TASKS: dict[str, asyncio.Task[Any]] = {}

PROJECT_AGENT_ROLES: dict[str, dict[str, str]] = {
    "planner": {
        "description": "Plans and decomposes tasks within project boundaries.",
        "system_prompt": (
            "You are a project planner agent. Work strictly within the active project context. "
            "Break down requests into actionable project tasks and constraints."
        ),
    },
    "coder": {
        "description": "Implements changes and proposes code-level solutions for the active project.",
        "system_prompt": (
            "You are a coding agent focused on the active project only. "
            "Generate concrete implementation steps and code-oriented guidance for this project."
        ),
    },
    "reviewer": {
        "description": "Reviews architecture and code quality for the active project.",
        "system_prompt": (
            "You are a review agent scoped to the active project. "
            "Find defects, regressions, and improvement opportunities using only project-local context."
        ),
    },
    "memory": {
        "description": "Maintains durable project memory and summaries for the active project.",
        "system_prompt": (
            "You are a project memory curator. "
            "Store concise, high-signal project facts and keep memory scoped to the active project."
        ),
    },
    "retrieval_agent": {
        "description": "Retrieves project-relevant memory and context.",
        "system_prompt": (
            "You are a retrieval agent scoped to one project. "
            "Find and return only context relevant to this project."
        ),
    },
    "reasoning_agent": {
        "description": "Performs deep reasoning for project tasks.",
        "system_prompt": (
            "You are a reasoning agent for a single project. "
            "Analyze tasks using only project-scoped facts and context."
        ),
    },
    "tool_agent": {
        "description": "Executes tool-centric operations for project diagnostics.",
        "system_prompt": (
            "You are a tool execution agent restricted to one project. "
            "Use tools to inspect and improve this project's quality."
        ),
    },
    "memory_agent": {
        "description": "Stores project conclusions and updates durable knowledge.",
        "system_prompt": (
            "You are a memory persistence agent for one project. "
            "Convert outcomes into durable, project-scoped memory entries."
        ),
    },
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _agent_run_cache_key(run_id: uuid.UUID) -> str:
    return f"agent_run:{run_id}"


def _normalize_project_id(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _normalize_project_path(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _project_scope_from_config(config: dict[str, Any] | None) -> str | None:
    if not isinstance(config, dict):
        return None
    return _normalize_project_id(config.get("project_id"))


def _effective_project_scope(
    *,
    agent_project_id: str | None,
    context: dict[str, Any] | None,
) -> str | None:
    context_project_id = _normalize_project_id((context or {}).get("project_id"))
    if agent_project_id and context_project_id and agent_project_id != context_project_id:
        raise ValueError(
            f"Agent project scope mismatch: agent is bound to {agent_project_id}, "
            f"but context requested {context_project_id}"
        )
    return context_project_id or agent_project_id


def _project_agent_name(project_id: str, role: str) -> str:
    return f"project:{project_id[:8]}:{role}"


def _track_background_task(run_id: uuid.UUID, task: asyncio.Task[Any]) -> None:
    """Track background tasks to avoid accidental garbage collection."""
    key = str(run_id)
    _BACKGROUND_AGENT_TASKS[key] = task

    def _cleanup(_task: asyncio.Task[Any]) -> None:
        _BACKGROUND_AGENT_TASKS.pop(key, None)

    task.add_done_callback(_cleanup)


async def _execute_background_agent_run(
    run_id: uuid.UUID,
    agent_id: uuid.UUID,
    input_text: str,
    session_id: uuid.UUID | None,
    context: dict[str, Any] | None,
    ttl_seconds: int,
) -> None:
    """Execute agent run asynchronously with a fresh DB session."""
    factory = _get_session_factory()
    short_term = ShortTermMemory()
    run_key = _agent_run_cache_key(run_id)
    started_at = _utcnow_iso()
    try:
        await short_term.cache_set(
            run_key,
            {
                "run_id": str(run_id),
                "agent_id": str(agent_id),
                "session_id": str(session_id) if session_id else None,
                "status": "running",
                "started_at": started_at,
                "created_at": started_at,
            },
            ttl=ttl_seconds,
        )

        async with factory() as db:
            svc = AgentService(db, short_term)
            result = await svc.run_agent(
                agent_id=agent_id,
                input_text=input_text,
                session_id=session_id,
                context=context,
            )
            await db.commit()

        await short_term.cache_set(
            run_key,
            {
                "run_id": str(run_id),
                "agent_id": str(agent_id),
                "session_id": result.get("session_id"),
                "status": "completed",
                "created_at": started_at,
                "started_at": started_at,
                "completed_at": _utcnow_iso(),
                "result": result,
            },
            ttl=ttl_seconds,
        )
    except Exception as e:
        logger.error("Background agent run failed for %s: %s", run_id, e, exc_info=True)
        await short_term.cache_set(
            run_key,
            {
                "run_id": str(run_id),
                "agent_id": str(agent_id),
                "session_id": str(session_id) if session_id else None,
                "status": "failed",
                "created_at": started_at,
                "started_at": started_at,
                "completed_at": _utcnow_iso(),
                "error": str(e),
            },
            ttl=ttl_seconds,
        )
    finally:
        await short_term.close()


class AgentService:
    """High-level agent operations."""

    def __init__(
        self,
        db: AsyncSession,
        short_term: ShortTermMemory | None = None,
        db_lock: asyncio.Lock | None = None,
    ) -> None:
        self._db = db
        self._db_lock = db_lock or asyncio.Lock()
        self._memory_service = MemoryService(db, short_term, db_lock=self._db_lock)
        self._short_term = short_term or ShortTermMemory()

    async def create_agent(
        self,
        name: str,
        system_prompt: str | None = None,
        description: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new agent."""
        resolved_prompt = system_prompt or get_default_system_prompt(name)
        agent = await self._memory_service.structured.create_agent(
            name=name,
            system_prompt=resolved_prompt,
            description=description,
            config=config,
        )
        return {
            "id": str(agent.id),
            "name": agent.name,
            "system_prompt": agent.system_prompt,
            "description": agent.description,
            "config": agent.config,
            "is_active": agent.is_active,
            "created_at": str(agent.created_at),
            "updated_at": str(agent.updated_at),
        }

    async def _find_project_role_agent(
        self,
        *,
        project_id: str,
        role: str,
    ) -> Agent | None:
        stmt = (
            select(Agent)
            .where(
                Agent.is_active.is_(True),
                Agent.config.contains(
                    {
                        "project_scoped": True,
                        "project_id": project_id,
                        "project_role": role,
                    }
                ),
            )
            .order_by(Agent.updated_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def _resolve_project_path(self, project_id: str | None) -> str | None:
        normalized_project_id = _normalize_project_id(project_id)
        if not normalized_project_id:
            return None
        try:
            project_uuid = uuid.UUID(normalized_project_id)
        except (ValueError, TypeError):
            return None

        stmt = select(Project.path).where(Project.id == project_uuid).limit(1)
        result = await self._db.execute(stmt)
        return _normalize_project_path(result.scalar_one_or_none())

    async def ensure_project_agents(
        self,
        *,
        project_id: str,
        project_name: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Ensure one role agent exists per predefined project role."""
        normalized_project_id = _normalize_project_id(project_id)
        if not normalized_project_id:
            raise ValueError("project_id is required")

        role_map: dict[str, dict[str, Any]] = {}
        for role, template in PROJECT_AGENT_ROLES.items():
            existing = await self._find_project_role_agent(
                project_id=normalized_project_id,
                role=role,
            )
            if existing is not None:
                role_map[role] = {
                    "id": str(existing.id),
                    "name": existing.name,
                    "description": existing.description,
                    "config": existing.config,
                    "is_active": existing.is_active,
                    "created_at": str(existing.created_at),
                    "updated_at": str(existing.updated_at),
                }
                continue

            created = await self.create_agent(
                name=_project_agent_name(normalized_project_id, role),
                system_prompt=template["system_prompt"],
                description=(
                    f"{template['description']} "
                    f"[project={project_name or normalized_project_id}]"
                ),
                config={
                    "project_scoped": True,
                    "project_id": normalized_project_id,
                    "project_name": project_name,
                    "project_role": role,
                    "autocreated": True,
                    "source": "project_scope",
                },
            )
            role_map[role] = created
        return role_map

    async def get_agent(self, agent_id: uuid.UUID) -> dict[str, Any] | None:
        """Get agent by ID."""
        agent = await self._memory_service.structured.get_agent(agent_id)
        if agent is None:
            return None
        return {
            "id": str(agent.id),
            "name": agent.name,
            "system_prompt": agent.system_prompt,
            "description": agent.description,
            "config": agent.config,
            "is_active": agent.is_active,
            "created_at": str(agent.created_at),
            "updated_at": str(agent.updated_at),
        }

    async def get_agent_state(self, agent_id: uuid.UUID) -> dict[str, Any] | None:
        """Get the current in-memory state of an agent."""
        state = await self._short_term.get_agent_state(str(agent_id))
        if state:
            return state
        # Fall back to DB agent data
        return await self.get_agent(agent_id)

    async def get_run_status(self, run_id: uuid.UUID) -> dict[str, Any] | None:
        """Get status/result for an asynchronous agent run."""
        return await self._short_term.cache_get(_agent_run_cache_key(run_id))

    async def enqueue_run(
        self,
        agent_id: uuid.UUID,
        input_text: str,
        session_id: uuid.UUID | None = None,
        context: dict[str, Any] | None = None,
        ttl_seconds: int = _AGENT_RUN_TTL_SECONDS,
    ) -> dict[str, Any]:
        """Queue an agent run and return immediately."""
        agent = await self.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        _effective_project_scope(
            agent_project_id=_project_scope_from_config(agent.get("config")),
            context=context,
        )

        run_id = uuid.uuid4()
        created_at = _utcnow_iso()
        await self._short_term.cache_set(
            _agent_run_cache_key(run_id),
            {
                "run_id": str(run_id),
                "agent_id": str(agent_id),
                "session_id": str(session_id) if session_id else None,
                "status": "pending",
                "created_at": created_at,
            },
            ttl=ttl_seconds,
        )

        task = asyncio.create_task(
            _execute_background_agent_run(
                run_id=run_id,
                agent_id=agent_id,
                input_text=input_text,
                session_id=session_id,
                context=context,
                ttl_seconds=ttl_seconds,
            )
        )
        _track_background_task(run_id, task)

        return {
            "run_id": str(run_id),
            "agent_id": str(agent_id),
            "status": "pending",
            "queued": True,
            "created_at": created_at,
        }

    async def create_session(
        self,
        agent_id: uuid.UUID,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new session for an agent."""
        session = await self._memory_service.structured.create_session(
            agent_id=agent_id,
            title=title,
            metadata=metadata,
        )
        return {
            "id": str(session.id),
            "agent_id": str(session.agent_id),
            "title": session.title,
            "metadata": session.metadata_,
            "is_active": session.is_active,
            "created_at": str(session.created_at),
            "updated_at": str(session.updated_at),
        }

    async def get_session(self, session_id: uuid.UUID) -> dict[str, Any] | None:
        """Get session by ID."""
        session = await self._memory_service.structured.get_session(session_id)
        if session is None:
            return None
        messages = await self._memory_service.structured.get_messages(session_id)
        return {
            "id": str(session.id),
            "agent_id": str(session.agent_id),
            "title": session.title,
            "metadata": session.metadata_,
            "is_active": session.is_active,
            "created_at": str(session.created_at),
            "updated_at": str(session.updated_at),
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "created_at": str(m.created_at),
                }
                for m in messages
            ],
        }

    async def run_agent(
        self,
        agent_id: uuid.UUID,
        input_text: str,
        session_id: uuid.UUID | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the agent with LangGraph."""
        from app.agent.graph import create_agent_graph

        agent = await self._memory_service.structured.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        effective_project_id = _effective_project_scope(
            agent_project_id=_project_scope_from_config(agent.config),
            context=context,
        )
        effective_context: dict[str, Any] = dict(context or {})
        if effective_project_id:
            effective_context["project_id"] = effective_project_id
        effective_project_path = _normalize_project_path(effective_context.get("project_path"))
        db_project_path = await self._resolve_project_path(effective_project_id)
        if effective_project_id and db_project_path:
            if effective_project_path:
                normalized_requested = str(
                    Path(effective_project_path).expanduser().resolve(strict=False)
                )
                normalized_db = str(Path(db_project_path).expanduser().resolve(strict=False))
                if normalized_requested != normalized_db:
                    raise ValueError(
                        f"Project path mismatch for project {effective_project_id}: "
                        f"context has {normalized_requested}, expected {normalized_db}"
                    )
            effective_project_path = db_project_path
        if effective_project_path:
            effective_context["project_path"] = effective_project_path

        # Reuse last active session when session_id is omitted.
        if session_id is None:
            state = await self._short_term.get_agent_state(str(agent_id))
            candidate_session_id: uuid.UUID | None = None
            if isinstance(state, dict) and state.get("last_session_id"):
                try:
                    candidate_session_id = uuid.UUID(str(state["last_session_id"]))
                except (ValueError, TypeError):
                    candidate_session_id = None

            if candidate_session_id is not None:
                existing = await self._memory_service.structured.get_session(candidate_session_id)
                if existing is not None and existing.is_active and existing.agent_id == agent_id:
                    session = existing
                    session_id = existing.id
                else:
                    session = await self._memory_service.structured.create_session(
                        agent_id=agent_id,
                        title=f"Auto-session for: {input_text[:50]}",
                        metadata={
                            "project_id": effective_project_id,
                            "project_path": effective_project_path,
                        } if effective_project_id else None,
                    )
                    session_id = session.id
            else:
                sessions = await self._memory_service.structured.list_sessions(agent_id)
                if sessions:
                    session = sessions[0]
                    session_id = session.id
                else:
                    session = await self._memory_service.structured.create_session(
                        agent_id=agent_id,
                        title=f"Auto-session for: {input_text[:50]}",
                        metadata={
                            "project_id": effective_project_id,
                            "project_path": effective_project_path,
                        } if effective_project_id else None,
                    )
                    session_id = session.id
        else:
            session = await self._memory_service.structured.get_session(session_id)
            if session is None:
                raise ValueError(f"Session {session_id} not found")
            if session.agent_id != agent_id:
                raise ValueError(f"Session {session_id} does not belong to agent {agent_id}")
            if effective_project_id:
                session_project_id = _normalize_project_id((session.metadata_ or {}).get("project_id"))
                if session_project_id and session_project_id != effective_project_id:
                    raise ValueError(
                        f"Session {session_id} belongs to project {session_project_id}, "
                        f"requested project is {effective_project_id}"
                    )
                session_project_path = _normalize_project_path((session.metadata_ or {}).get("project_path"))
                if (
                    session_project_path
                    and effective_project_path
                    and str(Path(session_project_path).expanduser().resolve(strict=False))
                    != str(Path(effective_project_path).expanduser().resolve(strict=False))
                ):
                    raise ValueError(
                        f"Session {session_id} belongs to project path {session_project_path}, "
                        f"requested path is {effective_project_path}"
                    )

        # Store user message
        await self._memory_service.structured.add_message(
            session_id=session_id,
            role="user",
            content=input_text,
            metadata=(
                {
                    "project_id": effective_project_id,
                    "project_path": effective_project_path,
                }
                if effective_project_id
                else None
            ),
        )

        # Retrieve relevant memories
        memories = await self._memory_service.search(
            query=input_text,
            agent_id=agent_id,
            metadata_filters={"project_id": effective_project_id} if effective_project_id else None,
            top_k=5,
        )

        # Get conversation history
        history = await self._memory_service.structured.get_messages(
            session_id=session_id, limit=20
        )

        # Build and run the agent graph
        graph = create_agent_graph(
            system_prompt=agent.system_prompt or get_default_system_prompt(agent.name),
            memory_service=self._memory_service,
        )

        from app.agent.tools import reset_tool_runtime_context, set_tool_runtime_context

        tool_context_token = set_tool_runtime_context(
            {
                "agent_id": str(agent_id),
                "session_id": str(session_id),
                "project_id": effective_project_id,
                "project_path": effective_project_path,
            }
        )
        try:
            result = await graph.ainvoke({
                "input": input_text,
                "agent_id": str(agent_id),
                "session_id": str(session_id),
                "memories": memories,
                "history": [
                    {"role": m.role, "content": m.content}
                    for m in history[:-1]  # Exclude the just-added user msg
                ],
                "context": {
                    "system_prompt": agent.system_prompt or get_default_system_prompt(agent.name),
                    **effective_context,
                },
                "messages": [],
                "output": "",
                "tool_calls": [],
            })
        finally:
            reset_tool_runtime_context(tool_context_token)

        output = result.get("output", "")

        # Store assistant response
        await self._memory_service.structured.add_message(
            session_id=session_id,
            role="assistant",
            content=output,
            metadata=(
                {
                    "project_id": effective_project_id,
                    "project_path": effective_project_path,
                }
                if effective_project_id
                else None
            ),
        )

        # Update agent state in Redis
        await self._short_term.set_agent_state(
            str(agent_id),
            {
                "last_session_id": str(session_id),
                "last_input": input_text,
                "last_output": output[:500],
                "project_id": effective_project_id,
                "project_path": effective_project_path,
            },
        )

        return {
            "agent_id": str(agent_id),
            "session_id": str(session_id),
            "output": output,
            "messages": result.get("messages", []),
            "tool_calls": result.get("tool_calls", []),
            "metadata": {
                "memories_used": len(memories),
                "project_id": effective_project_id,
                "project_path": effective_project_path,
                "project_scoped": bool(effective_project_id),
            },
        }
