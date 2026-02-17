"""Agent API endpoints."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.agent import AgentCreate, AgentRun, AgentResponse, AgentRunResponse
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)


def _get_agent_service(db: AsyncSession = Depends(get_db)) -> AgentService:
    return AgentService(db)


@router.post("", response_model=None, status_code=201)
async def create_agent(
    body: AgentCreate,
    svc: AgentService = Depends(_get_agent_service),
):
    """Create a new agent."""
    result = await svc.create_agent(
        name=body.name,
        system_prompt=body.system_prompt,
        description=body.description,
        config=body.config,
    )
    return result


@router.get("/{agent_id}")
async def get_agent(
    agent_id: uuid.UUID,
    svc: AgentService = Depends(_get_agent_service),
):
    """Get an agent by ID."""
    result = await svc.get_agent(agent_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return result


@router.post("/{agent_id}/run")
async def run_agent(
    agent_id: uuid.UUID,
    body: AgentRun,
    svc: AgentService = Depends(_get_agent_service),
):
    """Run the agent with a given input."""
    try:
        result = await svc.run_agent(
            agent_id=agent_id,
            input_text=body.input,
            session_id=body.session_id,
            context=body.context,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Agent run failed for %s: %s", agent_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error during agent execution")
