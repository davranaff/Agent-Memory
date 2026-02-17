"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.db.base import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info("Starting %s...", settings.app_name)

    # Initialize database and create tables
    await init_db()
    logger.info("Database initialized")

    # Register MCP routes directly on the main app if enabled
    if settings.mcp_enabled:
        try:
            from app.mcp.server import configure_mcp
            configure_mcp(app)
            logger.info("MCP server routes registered at /mcp")
        except Exception as e:
            logger.error("Failed to configure MCP server: %s", e)

    logger.info(
        "%s is ready | LLM: %s (%s) | Embeddings: %s (%s)",
        settings.app_name,
        settings.llm_provider,
        settings.llm_model,
        settings.embedding_provider,
        settings.embedding_model,
    )

    yield

    # Shutdown
    logger.info("Shutting down %s...", settings.app_name)

    # Close MCP shared Redis client
    try:
        from app.mcp.server import close_shared_short_term
        await close_shared_short_term()
    except Exception:
        pass


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Production-grade AI Agent Brain Backend with persistent memory, "
                    "multi-database support, and MCP integration.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from app.api.health import router as health_router
    from app.api.agents import router as agents_router
    from app.api.sessions import router as sessions_router
    from app.api.memory import router as memory_router
    from app.api.orchestration import router as orchestration_router

    app.include_router(health_router)
    app.include_router(agents_router)
    app.include_router(sessions_router)
    app.include_router(memory_router)
    app.include_router(orchestration_router)

    return app


# Application instance
app = create_app()
