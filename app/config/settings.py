"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration for the Agent Brain backend."""

    # ── Database ──────────────────────────────────────────────────────
    postgres_url: str = Field(
        default="postgresql+asyncpg://agent:agentpass@localhost:5432/agent_brain",
        description="Async PostgreSQL connection URL",
    )

    # ── Redis ─────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # ── MCP ───────────────────────────────────────────────────────────
    mcp_enabled: bool = Field(default=True, description="Enable MCP server")

    # ── Ollama (Local LLM) ────────────────────────────────────────────
    ollama_enabled: bool = Field(default=True, description="Enable Ollama")
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL",
    )

    # ── Embedding ─────────────────────────────────────────────────────
    embedding_provider: str = Field(
        default="ollama",
        description="Embedding provider: ollama | openai | local",
    )
    embedding_model: str = Field(
        default="nomic-embed-text",
        description="Model name for embedding provider",
    )
    embedding_dim: int = Field(
        default=768,
        description="Embedding vector dimension",
    )

    # ── OpenAI-compatible ─────────────────────────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_base_url: str = Field(
        default="",
        description="OpenAI-compatible base URL (leave empty for default)",
    )

    # ── LLM ───────────────────────────────────────────────────────────
    llm_provider: str = Field(
        default="ollama",
        description="LLM provider: ollama | openai",
    )
    llm_model: str = Field(
        default="llama3.2",
        description="LLM model name",
    )

    # ── Orchestration ─────────────────────────────────────────────────
    orchestration_enabled: bool = Field(
        default=True, description="Enable multi-agent orchestration"
    )
    orchestration_max_parallel_agents: int = Field(
        default=4, description="Max agents running in parallel"
    )
    orchestration_max_retries: int = Field(
        default=3, description="Max retries per orchestration step"
    )

    # ── General ───────────────────────────────────────────────────────
    debug: bool = Field(default=False)
    app_name: str = Field(default="Agent Brain")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# Singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
