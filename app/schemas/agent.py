"""Pydantic schemas for Agent endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────
class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    system_prompt: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None


class AgentRun(BaseModel):
    input: str = Field(..., min_length=1)
    session_id: uuid.UUID | None = None
    context: dict[str, Any] | None = None


# ── Response ──────────────────────────────────────────────────────────
class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    system_prompt: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentRunResponse(BaseModel):
    agent_id: uuid.UUID
    session_id: uuid.UUID
    output: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
