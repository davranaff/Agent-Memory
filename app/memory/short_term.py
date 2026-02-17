"""Short-term memory store — Redis with TTL support."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# Default TTL: 1 hour
DEFAULT_TTL = 3600


class ShortTermMemory:
    """Redis-backed short-term memory for session context and agent state."""

    def __init__(self, redis_client: aioredis.Redis | None = None) -> None:
        self._redis = redis_client

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            settings = get_settings()
            self._redis = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
        return self._redis

    # ── Session Context ───────────────────────────────────────────────
    async def set_session_context(
        self,
        session_id: str,
        context: dict[str, Any],
        ttl: int = DEFAULT_TTL,
    ) -> None:
        """Store session context with TTL."""
        r = await self._get_redis()
        key = f"session:{session_id}:context"
        await r.setex(key, ttl, json.dumps(context, default=str))

    async def get_session_context(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve session context."""
        r = await self._get_redis()
        key = f"session:{session_id}:context"
        data = await r.get(key)
        if data:
            return json.loads(data)
        return None

    async def update_session_context(
        self,
        session_id: str,
        updates: dict[str, Any],
        ttl: int = DEFAULT_TTL,
    ) -> dict[str, Any]:
        """Merge updates into existing session context."""
        ctx = await self.get_session_context(session_id) or {}
        ctx.update(updates)
        await self.set_session_context(session_id, ctx, ttl)
        return ctx

    async def delete_session_context(self, session_id: str) -> bool:
        """Remove session context."""
        r = await self._get_redis()
        key = f"session:{session_id}:context"
        return bool(await r.delete(key))

    # ── Agent State ───────────────────────────────────────────────────
    async def set_agent_state(
        self,
        agent_id: str,
        state: dict[str, Any],
        ttl: int = DEFAULT_TTL,
    ) -> None:
        """Store temporary agent state."""
        r = await self._get_redis()
        key = f"agent:{agent_id}:state"
        await r.setex(key, ttl, json.dumps(state, default=str))

    async def get_agent_state(self, agent_id: str) -> dict[str, Any] | None:
        """Retrieve agent state."""
        r = await self._get_redis()
        key = f"agent:{agent_id}:state"
        data = await r.get(key)
        if data:
            return json.loads(data)
        return None

    async def delete_agent_state(self, agent_id: str) -> bool:
        """Remove agent state."""
        r = await self._get_redis()
        key = f"agent:{agent_id}:state"
        return bool(await r.delete(key))

    # ── Cache ─────────────────────────────────────────────────────────
    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl: int = DEFAULT_TTL,
    ) -> None:
        """Generic cache set with TTL."""
        r = await self._get_redis()
        cache_key = f"cache:{key}"
        await r.setex(cache_key, ttl, json.dumps(value, default=str))

    async def cache_get(self, key: str) -> Any | None:
        """Generic cache get."""
        r = await self._get_redis()
        cache_key = f"cache:{key}"
        data = await r.get(cache_key)
        if data:
            return json.loads(data)
        return None

    async def cache_delete(self, key: str) -> bool:
        """Generic cache delete."""
        r = await self._get_redis()
        cache_key = f"cache:{key}"
        return bool(await r.delete(cache_key))

    # ── Retrieval Cache ───────────────────────────────────────────────
    async def cache_search_results(
        self,
        query_hash: str,
        results: list[dict[str, Any]],
        ttl: int = 300,  # 5 min default for search cache
    ) -> None:
        """Cache vector search results."""
        await self.cache_set(f"search:{query_hash}", results, ttl)

    async def get_cached_search_results(
        self, query_hash: str
    ) -> list[dict[str, Any]] | None:
        """Retrieve cached search results."""
        return await self.cache_get(f"search:{query_hash}")

    async def bump_memory_search_epoch(self) -> int:
        """Increment global memory search epoch to invalidate stale search caches."""
        r = await self._get_redis()
        return int(await r.incr("memory:search:epoch"))

    async def get_memory_search_epoch(self) -> int:
        """Read current memory search epoch."""
        r = await self._get_redis()
        val = await r.get("memory:search:epoch")
        return int(val) if val is not None else 0

    # ── Health ────────────────────────────────────────────────────────
    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            r = await self._get_redis()
            return await r.ping()
        except Exception:
            return False

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis:
            await self._redis.close()
