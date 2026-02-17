"""Memory API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.memory import MemoryStore, MemorySearch
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


def _get_memory_service(db: AsyncSession = Depends(get_db)) -> MemoryService:
    return MemoryService(db)


@router.post("/store", status_code=201)
async def store_memory(
    body: MemoryStore,
    svc: MemoryService = Depends(_get_memory_service),
):
    """Store a new memory with embedding."""
    result = await svc.store(
        content=body.content,
        memory_type=body.memory_type,
        agent_id=body.agent_id,
        metadata=body.metadata,
        importance=body.importance,
    )
    return result


@router.post("/search")
async def search_memory(
    body: MemorySearch,
    svc: MemoryService = Depends(_get_memory_service),
):
    """Semantic search through memories."""
    results = await svc.search(
        query=body.query,
        agent_id=body.agent_id,
        memory_type=body.memory_type,
        metadata_filters=body.metadata_filters,
        top_k=body.top_k,
        min_similarity=body.min_similarity,
    )
    return {"results": results, "count": len(results)}


@router.get("/{memory_id}")
async def get_memory(
    memory_id: uuid.UUID,
    svc: MemoryService = Depends(_get_memory_service),
):
    """Get a specific memory by ID."""
    result = await svc.get(memory_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return result


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: uuid.UUID,
    svc: MemoryService = Depends(_get_memory_service),
):
    """Soft-delete a memory."""
    deleted = await svc.delete(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True, "id": str(memory_id)}
