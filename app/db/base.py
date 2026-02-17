"""Database initialization and declarative base."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.db.session import _get_engine


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def init_db() -> None:
    """Create pgvector extension and all tables."""
    engine = _get_engine()
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Import models so they register with Base.metadata
        import app.core.models  # noqa: F401
        import app.orchestration.models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
