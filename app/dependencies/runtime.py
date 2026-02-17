"""Runtime graph backend factory and lifecycle helpers."""

from __future__ import annotations

import asyncio
import logging

from app.config.settings import get_settings
from app.dependencies.store import (
    GraphStore,
    InMemoryGraphStore,
    Neo4jGraphStore,
    ResilientGraphStore,
)

logger = logging.getLogger(__name__)

_graph_store: GraphStore | None = None
_graph_lock = asyncio.Lock()


async def get_graph_store() -> GraphStore:
    """Get or initialize the configured graph store backend."""
    global _graph_store
    if _graph_store is not None:
        return _graph_store

    async with _graph_lock:
        if _graph_store is not None:
            return _graph_store

        settings = get_settings()
        backend = settings.graph_backend.strip().lower()

        fallback = InMemoryGraphStore()

        if backend == "neo4j":
            if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
                if settings.graph_fallback_to_inmemory:
                    logger.warning(
                        "GRAPH_BACKEND=neo4j but credentials are incomplete; using in-memory fallback"
                    )
                    _graph_store = fallback
                    return _graph_store
                raise ValueError("Neo4j backend selected but NEO4J_URI/USER/PASSWORD are missing")

            primary = Neo4jGraphStore(
                uri=settings.neo4j_uri,
                user=settings.neo4j_user,
                password=settings.neo4j_password,
                database=settings.neo4j_database,
            )

            try:
                await primary.verify_connectivity()
                logger.info("Connected to Neo4j graph backend: %s", settings.neo4j_uri)
            except Exception as e:
                await primary.close()
                if settings.graph_fallback_to_inmemory:
                    logger.warning(
                        "Neo4j unavailable (%s); using in-memory graph fallback",
                        e,
                    )
                    _graph_store = fallback
                    return _graph_store
                raise

            _graph_store = ResilientGraphStore(
                primary=primary,
                fallback=fallback,
                fallback_enabled=settings.graph_fallback_to_inmemory,
            )
            return _graph_store

        _graph_store = fallback
        logger.info("Using in-memory graph backend")
        return _graph_store


async def close_graph_store() -> None:
    """Close graph backend resources."""
    global _graph_store
    if _graph_store is not None:
        await _graph_store.close()
        _graph_store = None
