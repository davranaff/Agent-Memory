"""Session API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.session import SessionCreate
from app.services.agent_service import AgentService

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _get_agent_service(db: AsyncSession = Depends(get_db)) -> AgentService:
    return AgentService(db)


@router.post("", status_code=201)
async def create_session(
    body: SessionCreate,
    svc: AgentService = Depends(_get_agent_service),
):
    """Create a new session for an agent."""
    # Verify agent exists
    agent = await svc.get_agent(body.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    result = await svc.create_session(
        agent_id=body.agent_id,
        title=body.title,
        metadata=body.metadata,
    )
    return result


@router.get("/{session_id}")
async def get_session(
    session_id: uuid.UUID,
    svc: AgentService = Depends(_get_agent_service),
):
    """Get a session by ID, including messages."""
    result = await svc.get_session(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result
