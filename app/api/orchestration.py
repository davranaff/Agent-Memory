"""Orchestration API endpoints."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.orchestration import OrchestrationRunRequest
from app.orchestration.service import OrchestrationService
from app.orchestration.workflows import list_workflows

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestration", tags=["orchestration"])


def _get_orchestration_service(
    db: AsyncSession = Depends(get_db),
) -> OrchestrationService:
    return OrchestrationService(db)


@router.post("/run", status_code=201)
async def run_orchestration(
    body: OrchestrationRunRequest,
    svc: OrchestrationService = Depends(_get_orchestration_service),
):
    """Start an orchestration run.

    If `workflow` is omitted and `auto_route` is True, the router selects
    the best workflow based on input content.
    """
    try:
        result = await svc.start_run(
            workflow_name=body.workflow,
            input_text=body.input,
            auto_route=body.auto_route,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Orchestration run failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error during orchestration")


@router.get("/{run_id}")
async def get_orchestration_run(
    run_id: uuid.UUID,
    svc: OrchestrationService = Depends(_get_orchestration_service),
):
    """Get orchestration run status and results."""
    result = await svc.get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Orchestration run not found")
    return result


@router.get("/workflows/list")
async def get_workflows():
    """List all available workflow definitions."""
    return {"workflows": list_workflows()}
