"""SQLAlchemy models for orchestration persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class OrchestrationRun(Base):
    """Persists an orchestration workflow execution."""

    __tablename__ = "orchestration_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    workflow_name = Column(String(255), nullable=False, index=True)
    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending | running | completed | failed | partial
    input = Column(Text, nullable=False)
    output = Column(Text, nullable=True)
    agent_sequence = Column(JSONB, nullable=True, default=list)
    intermediate_results = Column(JSONB, nullable=True, default=list)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    steps = relationship(
        "OrchestrationStep", back_populates="run", lazy="selectin",
        order_by="OrchestrationStep.step_index",
    )


class OrchestrationStep(Base):
    """Persists a single step within an orchestration run."""

    __tablename__ = "orchestration_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orchestration_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id = Column(UUID(as_uuid=True), nullable=True)
    agent_name = Column(String(255), nullable=False)
    step_index = Column(Integer, nullable=False)
    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending | running | completed | failed | skipped
    input = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    run = relationship("OrchestrationRun", back_populates="steps")
