"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import _get_session_factory
from app.memory.short_term import ShortTermMemory

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Check the health of all backend services."""
    status = {"status": "ok", "services": {}}

    # Check PostgreSQL
    try:
        factory = _get_session_factory()
        async with factory() as db:
            await db.execute(text("SELECT 1"))
        status["services"]["postgres"] = "healthy"
    except Exception as e:
        status["services"]["postgres"] = f"unhealthy: {e}"
        status["status"] = "degraded"

    # Check Redis
    try:
        stm = ShortTermMemory()
        redis_ok = await stm.ping()
        status["services"]["redis"] = "healthy" if redis_ok else "unhealthy"
        if not redis_ok:
            status["status"] = "degraded"
    except Exception as e:
        status["services"]["redis"] = f"unhealthy: {e}"
        status["status"] = "degraded"

    # Check Ollama (optional)
    from app.config.settings import get_settings

    settings = get_settings()
    if settings.ollama_enabled:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.ollama_base_url}/api/tags", timeout=5.0
                )
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    status["services"]["ollama"] = {
                        "status": "healthy",
                        "models": [m["name"] for m in models],
                    }
                else:
                    status["services"]["ollama"] = "unhealthy"
        except Exception:
            status["services"]["ollama"] = "unavailable (optional)"

    return status
