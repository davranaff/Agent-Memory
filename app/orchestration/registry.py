"""Agent registry — dynamic agent registration and lookup."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Agent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for addressable agents by unique string name.

    Supports both static name registration and dynamic DB-backed lookup.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._static_map: dict[str, uuid.UUID] = {}
        self._cache: dict[str, dict[str, Any]] = {}

    def register(self, name: str, agent_id: uuid.UUID) -> None:
        """Register a static agent name mapping."""
        self._static_map[name] = agent_id
        logger.info("Registered agent '%s' -> %s", name, agent_id)

    async def resolve(self, name: str) -> uuid.UUID | None:
        """Resolve an agent name to its UUID.

        Checks static registrations first, then falls back to DB lookup by name.
        """
        # Static map first
        if name in self._static_map:
            return self._static_map[name]

        # DB lookup by name
        result = await self._db.execute(
            select(Agent).where(Agent.name == name, Agent.is_active.is_(True))
        )
        agent = result.scalar_one_or_none()
        if agent:
            # Cache for subsequent lookups
            self._static_map[name] = agent.id
            return agent.id

        return None

    async def get(self, name: str) -> dict[str, Any] | None:
        """Get full agent info by name."""
        if name in self._cache:
            return self._cache[name]

        agent_id = await self.resolve(name)
        if agent_id is None:
            return None

        result = await self._db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            return None

        info = {
            "id": str(agent.id),
            "name": agent.name,
            "system_prompt": agent.system_prompt,
            "description": agent.description,
        }
        self._cache[name] = info
        return info

    async def list_agents(self) -> list[dict[str, Any]]:
        """List all registered and active agents."""
        result = await self._db.execute(
            select(Agent).where(Agent.is_active.is_(True)).order_by(Agent.name)
        )
        agents = result.scalars().all()
        return [
            {
                "id": str(a.id),
                "name": a.name,
                "description": a.description,
            }
            for a in agents
        ]

    async def ensure_registered(self, names: list[str]) -> dict[str, uuid.UUID]:
        """Resolve multiple agent names, returning name→UUID mapping.

        Raises ValueError if any agent is not found.
        """
        resolved: dict[str, uuid.UUID] = {}
        missing: list[str] = []

        for name in names:
            agent_id = await self.resolve(name)
            if agent_id is None:
                missing.append(name)
            else:
                resolved[name] = agent_id

        if missing:
            raise ValueError(f"Agents not found: {', '.join(missing)}")

        return resolved
