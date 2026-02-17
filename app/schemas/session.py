"""Pydantic schemas for Session endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────
class SessionCreate(BaseModel):
    agent_id: uuid.UUID
    title: str | None = None
    metadata: dict[str, Any] | None = None


# ── Response ──────────────────────────────────────────────────────────
class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    metadata: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    title: str | None = None
    metadata: dict[str, Any] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
