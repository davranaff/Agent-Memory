"""Structured memory store — full CRUD over PostgreSQL tables."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Text, cast, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Agent, Session, Message, Memory, Tool, ToolCall


class StructuredMemoryStore:
    """CRUD operations for all structured data in PostgreSQL."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Agents ────────────────────────────────────────────────────────
    async def create_agent(
        self,
        name: str,
        system_prompt: str | None = None,
        description: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> Agent:
        agent = Agent(
            name=name,
            system_prompt=system_prompt,
            description=description,
            config=config or {},
        )
        self._db.add(agent)
        await self._db.flush()
        await self._db.refresh(agent)
        return agent

    async def get_agent(self, agent_id: uuid.UUID) -> Agent | None:
        result = await self._db.execute(select(Agent).where(Agent.id == agent_id))
        return result.scalar_one_or_none()

    async def list_agents(self, active_only: bool = True) -> list[Agent]:
        q = select(Agent)
        if active_only:
            q = q.where(Agent.is_active.is_(True))
        result = await self._db.execute(q.order_by(Agent.created_at.desc()))
        return list(result.scalars().all())

    async def update_agent(self, agent_id: uuid.UUID, **kwargs: Any) -> Agent | None:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self._db.execute(
            update(Agent).where(Agent.id == agent_id).values(**kwargs)
        )
        await self._db.flush()
        return await self.get_agent(agent_id)

    async def delete_agent(self, agent_id: uuid.UUID) -> bool:
        result = await self._db.execute(
            delete(Agent).where(Agent.id == agent_id)
        )
        await self._db.flush()
        return result.rowcount > 0

    # ── Sessions ──────────────────────────────────────────────────────
    async def create_session(
        self,
        agent_id: uuid.UUID,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        session = Session(
            agent_id=agent_id,
            title=title,
            metadata_=metadata or {},
        )
        self._db.add(session)
        await self._db.flush()
        await self._db.refresh(session)
        return session

    async def get_session(self, session_id: uuid.UUID) -> Session | None:
        result = await self._db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(self, agent_id: uuid.UUID) -> list[Session]:
        result = await self._db.execute(
            select(Session)
            .where(Session.agent_id == agent_id, Session.is_active.is_(True))
            .order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Messages ──────────────────────────────────────────────────────
    async def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
            metadata_=metadata or {},
        )
        self._db.add(msg)
        await self._db.flush()
        await self._db.refresh(msg)
        return msg

    async def get_messages(
        self,
        session_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Message]:
        result = await self._db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Memories ──────────────────────────────────────────────────────
    async def create_memory(
        self,
        content: str,
        memory_type: str = "general",
        agent_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
        importance: int = 5,
    ) -> Memory:
        mem = Memory(
            content=content,
            memory_type=memory_type,
            agent_id=agent_id,
            metadata_=metadata or {},
            embedding=embedding,
            importance=importance,
        )
        self._db.add(mem)
        await self._db.flush()
        await self._db.refresh(mem)
        return mem

    async def get_memory(self, memory_id: uuid.UUID) -> Memory | None:
        result = await self._db.execute(
            select(Memory).where(Memory.id == memory_id)
        )
        return result.scalar_one_or_none()

    async def list_memories(
        self,
        agent_id: uuid.UUID | None = None,
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[Memory]:
        q = select(Memory).where(Memory.is_active.is_(True))
        if agent_id:
            q = q.where(Memory.agent_id == agent_id)
        if memory_type:
            q = q.where(Memory.memory_type == memory_type)
        result = await self._db.execute(
            q.order_by(Memory.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def search_memories_text(
        self,
        query: str,
        agent_id: uuid.UUID | None = None,
        memory_type: str | None = None,
        metadata_filters: dict[str, Any] | None = None,
        limit: int = 50,
    ) -> list[Memory]:
        """Fallback lexical search across memory content and metadata."""
        q = select(Memory).where(Memory.is_active.is_(True))

        if agent_id:
            q = q.where(Memory.agent_id == agent_id)
        if memory_type:
            q = q.where(Memory.memory_type == memory_type)
        if metadata_filters:
            q = q.where(Memory.metadata_.contains(metadata_filters))

        import re
        terms = [t for t in re.findall(r"[a-zA-Z0-9_-]+", query.lower()) if len(t) >= 3]
        if terms:
            text_filters = [Memory.content.ilike(f"%{t}%") for t in terms[:8]]
            metadata_text = cast(Memory.metadata_, Text)
            text_filters.extend([metadata_text.ilike(f"%{t}%") for t in terms[:5]])
            q = q.where(or_(*text_filters))
        else:
            q = q.where(Memory.content.ilike(f"%{query}%"))

        result = await self._db.execute(
            q.order_by(Memory.importance.desc(), Memory.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def find_active_memory_by_fingerprint(
        self,
        fingerprint: str,
        agent_id: uuid.UUID | None = None,
        memory_type: str | None = None,
        metadata_scope: dict[str, Any] | None = None,
    ) -> Memory | None:
        """Find an active memory row by stable fingerprint and optional scope."""
        q = select(Memory).where(
            Memory.is_active.is_(True),
            Memory.metadata_.contains({"__fingerprint": fingerprint}),
        )
        if agent_id:
            q = q.where(Memory.agent_id == agent_id)
        if memory_type:
            q = q.where(Memory.memory_type == memory_type)
        if metadata_scope:
            q = q.where(Memory.metadata_.contains(metadata_scope))

        result = await self._db.execute(
            q.order_by(Memory.updated_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def update_memory(
        self, memory_id: uuid.UUID, **kwargs: Any
    ) -> Memory | None:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self._db.execute(
            update(Memory).where(Memory.id == memory_id).values(**kwargs)
        )
        await self._db.flush()
        return await self.get_memory(memory_id)

    async def delete_memory(self, memory_id: uuid.UUID) -> bool:
        result = await self._db.execute(
            update(Memory)
            .where(Memory.id == memory_id)
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        await self._db.flush()
        return result.rowcount > 0

    # ── Tools ─────────────────────────────────────────────────────────
    async def create_tool(
        self,
        name: str,
        description: str | None = None,
        input_schema: dict[str, Any] | None = None,
        source: str = "builtin",
        agent_id: uuid.UUID | None = None,
        mcp_server_url: str | None = None,
    ) -> Tool:
        tool = Tool(
            name=name,
            description=description,
            input_schema=input_schema,
            source=source,
            agent_id=agent_id,
            mcp_server_url=mcp_server_url,
        )
        self._db.add(tool)
        await self._db.flush()
        await self._db.refresh(tool)
        return tool

    async def get_tools(self, agent_id: uuid.UUID | None = None) -> list[Tool]:
        q = select(Tool).where(Tool.is_active.is_(True))
        if agent_id:
            q = q.where(Tool.agent_id == agent_id)
        result = await self._db.execute(q)
        return list(result.scalars().all())

    # ── Tool Calls ────────────────────────────────────────────────────
    async def record_tool_call(
        self,
        tool_id: uuid.UUID | None,
        session_id: uuid.UUID | None,
        input_data: dict[str, Any] | None,
        output_data: dict[str, Any] | None = None,
        status: str = "pending",
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> ToolCall:
        tc = ToolCall(
            tool_id=tool_id,
            session_id=session_id,
            input_data=input_data,
            output_data=output_data,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        self._db.add(tc)
        await self._db.flush()
        await self._db.refresh(tc)
        return tc
