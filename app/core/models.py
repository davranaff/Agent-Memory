"""SQLAlchemy ORM models for the Agent Brain backend."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.config.settings import get_settings
from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    name = Column(String(255), nullable=False, index=True)
    system_prompt = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    config = Column(JSONB, nullable=True, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    sessions = relationship("Session", back_populates="agent", lazy="selectin")
    tools = relationship("Tool", back_populates="agent", lazy="selectin")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(255), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    agent = relationship("Agent", back_populates="sessions")
    messages = relationship("Message", back_populates="session", lazy="selectin")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(50), nullable=False)  # user | assistant | system | tool
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    session = relationship("Session", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )


class Memory(Base):
    __tablename__ = "memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    content = Column(Text, nullable=False)
    memory_type = Column(
        String(50), nullable=False, default="general"
    )  # general | fact | episode | procedure
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    embedding = Column(Vector(get_settings().embedding_dim), nullable=True)
    importance = Column(Integer, default=5, nullable=False)  # 1-10
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_memories_agent_type", "agent_id", "memory_type"),
        Index("ix_memories_metadata_gin", metadata_, postgresql_using="gin"),
        Index("ix_memories_active_created", is_active, created_at.desc()),
        Index(
            "ix_memories_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
    )


class Tool(Base):
    __tablename__ = "tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=True
    )
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    input_schema = Column(JSONB, nullable=True)
    source = Column(
        String(50), nullable=False, default="builtin"
    )  # builtin | mcp | custom
    mcp_server_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="tools")
    tool_calls = relationship("ToolCall", back_populates="tool", lazy="selectin")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    tool_id = Column(
        UUID(as_uuid=True), ForeignKey("tools.id", ondelete="SET NULL"), nullable=True
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending | running | success | error
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    tool = relationship("Tool", back_populates="tool_calls")


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    name = Column(String(255), nullable=False, index=True)
    path = Column(String(1000), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    tech_stack = Column(JSONB, nullable=True, default=list)  # ["python", "fastapi", "postgresql"]
    architecture_type = Column(String(100), nullable=True)  # mvc, microservices, serverless, monolith
    frameworks = Column(JSONB, nullable=True, default=list)  # ["fastapi", "react", "vue"]
    languages = Column(JSONB, nullable=True, default=list)  # ["python", "javascript", "sql"]
    databases = Column(JSONB, nullable=True, default=list)  # ["postgresql", "redis", "mongodb"]
    build_tools = Column(JSONB, nullable=True, default=list)  # ["docker", "webpack", "maven"]
    total_files = Column(Integer, default=0, nullable=False)
    total_lines = Column(Integer, default=0, nullable=False)
    last_analyzed = Column(DateTime(timezone=True), nullable=True)
    analysis_status = Column(
        String(50), nullable=False, default="pending"
    )  # pending | analyzing | completed | error
    analysis_error = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    components = relationship("Component", back_populates="project", lazy="selectin")
    patterns = relationship("CodePattern", back_populates="project", lazy="selectin")
    documentation = relationship("Documentation", back_populates="project", lazy="selectin")

    __table_args__ = (
        Index("ix_projects_path", "path"),
        Index("ix_projects_tech_stack", tech_stack, postgresql_using="gin"),
        Index("ix_projects_status", "analysis_status"),
    )


class Component(Base):
    __tablename__ = "components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False, index=True)
    type = Column(
        String(50), nullable=False
    )  # file | directory | class | function | interface | enum | struct
    path = Column(String(1000), nullable=False)
    relative_path = Column(String(1000), nullable=False)
    language = Column(String(50), nullable=True)  # python, javascript, java, go, rust, etc.
    file_extension = Column(String(10), nullable=True)  # .py, .js, .java, .go, .rs
    size_bytes = Column(Integer, default=0, nullable=False)
    line_count = Column(Integer, default=0, nullable=False)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    complexity_score = Column(Integer, default=0, nullable=False)  # 1-10
    dependencies = Column(JSONB, nullable=True, default=list)  # imported components
    dependents = Column(JSONB, nullable=True, default=list)  # components that import this
    exports = Column(JSONB, nullable=True, default=list)  # public API
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    project = relationship("Project", back_populates="components")

    __table_args__ = (
        Index("ix_components_project_type", "project_id", "type"),
        Index("ix_components_path", "path"),
        Index("ix_components_language", "language"),
        Index("ix_components_dependencies", dependencies, postgresql_using="gin"),
    )


class CodePattern(Base):
    __tablename__ = "code_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False)  # architectural | design | creational | structural | behavioral
    pattern_type = Column(String(100), nullable=False)  # repository | factory | observer | singleton | etc.
    description = Column(Text, nullable=False)
    implementation_example = Column(Text, nullable=True)
    use_cases = Column(JSONB, nullable=True, default=list)
    benefits = Column(JSONB, nullable=True, default=list)
    drawbacks = Column(JSONB, nullable=True, default=list)
    related_patterns = Column(JSONB, nullable=True, default=list)  # pattern names
    components_involved = Column(JSONB, nullable=True, default=list)  # component IDs
    confidence_score = Column(Integer, default=5, nullable=False)  # 1-10 how certain we are
    is_builtin = Column(Boolean, default=False, nullable=False)  # built-in pattern library
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    project = relationship("Project", back_populates="patterns")

    __table_args__ = (
        Index("ix_patterns_project_category", "project_id", "category"),
        Index("ix_patterns_type", "pattern_type"),
        Index("ix_patterns_builtin", "is_builtin"),
    )


class Documentation(Base):
    __tablename__ = "documentation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    component_id = Column(
        UUID(as_uuid=True), ForeignKey("components.id", ondelete="CASCADE"), nullable=True
    )
    title = Column(String(255), nullable=False)
    type = Column(
        String(50), nullable=False
    )  # readme | api | guide | tutorial | reference | changelog | license
    path = Column(String(1000), nullable=False)
    relative_path = Column(String(1000), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    language = Column(String(50), nullable=True)  # markdown | html | pdf | txt
    format = Column(String(20), nullable=True)  # md | html | pdf | txt
    size_bytes = Column(Integer, default=0, nullable=False)
    word_count = Column(Integer, default=0, nullable=False)
    links = Column(JSONB, nullable=True, default=list)  # internal and external links
    tags = Column(JSONB, nullable=True, default=list)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    project = relationship("Project", back_populates="documentation")
    component = relationship("Component")

    __table_args__ = (
        Index("ix_documentation_project_type", "project_id", "type"),
        Index("ix_documentation_component", "component_id"),
        Index("ix_documentation_path", "path"),
        Index("ix_documentation_tags", tags, postgresql_using="gin"),
    )
