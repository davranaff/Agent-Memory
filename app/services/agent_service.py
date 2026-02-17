"""Agent service — CRUD and run delegation to LangGraph agent."""

from __future__ import annotations

import logging
import uuid
from typing import Any
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.prompts import get_default_system_prompt
from app.memory.short_term import ShortTermMemory
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


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
                    )
                    session_id = session.id
        else:
            session = await self._memory_service.structured.get_session(session_id)
            if session is None:
                raise ValueError(f"Session {session_id} not found")
            if session.agent_id != agent_id:
                raise ValueError(f"Session {session_id} does not belong to agent {agent_id}")

        # Store user message
        await self._memory_service.structured.add_message(
            session_id=session_id,
            role="user",
            content=input_text,
        )

        # Retrieve relevant memories
        memories = await self._memory_service.search(
            query=input_text,
            agent_id=agent_id,
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
                **(context or {}),
            },
            "messages": [],
            "output": "",
            "tool_calls": [],
        })

        output = result.get("output", "")

        # Store assistant response
        await self._memory_service.structured.add_message(
            session_id=session_id,
            role="assistant",
            content=output,
        )

        # Update agent state in Redis
        await self._short_term.set_agent_state(
            str(agent_id),
            {
                "last_session_id": str(session_id),
                "last_input": input_text,
                "last_output": output[:500],
            },
        )

        return {
            "agent_id": str(agent_id),
            "session_id": str(session_id),
            "output": output,
            "messages": result.get("messages", []),
            "tool_calls": result.get("tool_calls", []),
            "metadata": {"memories_used": len(memories)},
        }
