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

    # ── Graph Backend ────────────────────────────────────────────────
    graph_backend: str = Field(
        default="inmemory",
        description="Graph backend: inmemory | neo4j",
    )
    graph_fallback_to_inmemory: bool = Field(
        default=True,
        description="Fallback to in-memory graph backend if Neo4j is unavailable",
    )
    neo4j_uri: str = Field(default="", description="Neo4j bolt URI")
    neo4j_user: str = Field(default="", description="Neo4j username")
    neo4j_password: str = Field(default="", description="Neo4j password")
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")

    # ── General ───────────────────────────────────────────────────────
    debug: bool = Field(default=False)
    app_name: str = Field(default="Agent Brain")
    api_key: str = Field(default="", description="Optional API key for protected access")
    project_path_mappings: str = Field(
        default="",
        description="Comma-separated host/container path mappings: /host=/container,/host2=/container2",
    )
    cors_allow_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated CORS origins; use * only for trusted dev environments",
    )
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: str = Field(default="GET,POST,PUT,PATCH,DELETE,OPTIONS")
    cors_allow_headers: str = Field(default="Authorization,Content-Type,X-API-Key")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @staticmethod
    def _csv_to_list(raw: str) -> list[str]:
        if not raw:
            return []
        if raw.strip() == "*":
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return self._csv_to_list(self.cors_allow_origins)

    @property
    def cors_methods_list(self) -> list[str]:
        return self._csv_to_list(self.cors_allow_methods)

    @property
    def cors_headers_list(self) -> list[str]:
        return self._csv_to_list(self.cors_allow_headers)


# Singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
