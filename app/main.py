"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.config.settings import get_settings
from app.db.base import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)
_autonomous_supervisor = None


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

    global _autonomous_supervisor
    if settings.autonomous_background_enabled:
        try:
            from app.services.autonomous_supervisor import AutonomousProjectSupervisor

            _autonomous_supervisor = AutonomousProjectSupervisor()
            _autonomous_supervisor.start()
        except Exception as e:
            logger.error("Failed to start autonomous supervisor: %s", e)

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

    # Close graph backend resources (Neo4j driver, etc.)
    try:
        from app.dependencies import close_graph_store
        await close_graph_store()
    except Exception:
        pass

    # Stop autonomous supervisor
    if _autonomous_supervisor is not None:
        try:
            await _autonomous_supervisor.stop()
        except Exception:
            pass
        _autonomous_supervisor = None


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

    @app.middleware("http")
    async def api_key_guard(request: Request, call_next):
        # Optional guard: enabled only when API_KEY is configured.
        if not settings.api_key:
            return await call_next(request)

        public_paths = {"/health", "/docs", "/openapi.json", "/redoc"}
        if request.url.path in public_paths or request.url.path.startswith("/docs"):
            return await call_next(request)

        provided_key = request.headers.get("x-api-key")
        if provided_key != settings.api_key:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_methods_list,
        allow_headers=settings.cors_headers_list,
    )

    # Register routers
    from app.api.health import router as health_router
    from app.api.agents import router as agents_router
    from app.api.sessions import router as sessions_router
    from app.api.memory import router as memory_router
    from app.api.orchestration import router as orchestration_router
    from app.api.projects import router as projects_router
    from app.api.semantic import router as semantic_router
    from app.api.enhanced import router as enhanced_router
    from app.api.advanced import router as advanced_router

    app.include_router(health_router)
    app.include_router(agents_router)
    app.include_router(sessions_router)
    app.include_router(memory_router)
    app.include_router(orchestration_router)
    app.include_router(projects_router)
    app.include_router(semantic_router)
    app.include_router(enhanced_router)
    app.include_router(advanced_router)

    return app


# Application instance
app = create_app()
