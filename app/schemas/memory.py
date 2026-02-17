"""Pydantic schemas for Memory endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────
class MemoryStore(BaseModel):
    content: str = Field(..., min_length=1)
    memory_type: str = Field(default="general")
    agent_id: uuid.UUID | None = None
    metadata: dict[str, Any] | None = None
    importance: int = Field(default=5, ge=1, le=10)


class MemorySearch(BaseModel):
    query: str = Field(..., min_length=1)
    agent_id: uuid.UUID | None = None
    memory_type: str | None = None
    metadata_filters: dict[str, Any] | None = None
    top_k: int = Field(default=10, ge=1, le=100)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)


# ── Response ──────────────────────────────────────────────────────────
class MemoryResponse(BaseModel):
    id: uuid.UUID
    content: str
    memory_type: str
    agent_id: uuid.UUID | None = None
    metadata: dict[str, Any] | None = None
    importance: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    similarity: float | None = None  # Populated during search

    model_config = {"from_attributes": True}
