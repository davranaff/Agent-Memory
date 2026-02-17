# Agent Brain Backend

Production-grade AI agent brain with persistent memory, semantic vector search, and MCP integration.

## Quick Start

```bash
# 1. Copy env and configure
cp .env.example .env

# 2. Start all services
docker compose up --build

# 3. Verify
curl http://localhost:8000/health
```

## Architecture

```
app/
├── api/             # FastAPI endpoints
├── agent/           # LangGraph agent (state, graph, tools)
├── config/          # Pydantic settings
├── core/            # SQLAlchemy models
├── db/              # Database session & init
├── mcp/             # MCP server + client
├── memory/          # 3-layer memory system
├── orchestration/   # Multi-agent orchestration engine
├── schemas/         # Pydantic request/response schemas
└── services/        # Business logic orchestration
```

## Memory System

| Layer | Backend | Purpose |
|-------|---------|---------|
| Structured | PostgreSQL | Agents, sessions, messages, tools, tool calls |
| Vector | pgvector | Semantic similarity search, embeddings |
| Short-term | Redis | Session context, agent state, cache (TTL) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| POST | `/agents` | Create agent |
| GET | `/agents/{id}` | Get agent |
| POST | `/agents/{id}/run` | Run agent (requires LLM) |
| POST | `/sessions` | Create session |
| GET | `/sessions/{id}` | Get session with messages |
| POST | `/memory/store` | Store memory with embedding |
| POST | `/memory/search` | Semantic memory search |
| GET | `/memory/{id}` | Get memory |
| DELETE | `/memory/{id}` | Delete memory |
| POST | `/orchestration/run` | Start orchestration workflow |
| GET | `/orchestration/{run_id}` | Get run status & results |
| GET | `/orchestration/workflows/list` | List available workflows |

## MCP Integration

### Server (exposed at `/mcp/sse`)

Tools: `memory_store`, `memory_search`, `memory_get`, `memory_delete`, `memory_reindex`, `agent_run`, `agent_get_state`, `db_query`, `embeddings_create`, `orchestration_run`

Connect from any MCP client (Windsurf, Claude, etc.):
```json
{
  "mcpServers": {
    "agent-brain": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

### Client

The system can also connect to external MCP servers to discover and use their tools.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_URL` | `postgresql+asyncpg://agent:agentpass@postgres:5432/agent_brain` | Database URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL |
| `LLM_PROVIDER` | `ollama` | LLM: `ollama` or `openai` |
| `LLM_MODEL` | `llama3.2` | Model name |
| `EMBEDDING_PROVIDER` | `ollama` | Embeddings: `ollama`, `openai`, or `local` |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `MCP_ENABLED` | `true` | Enable MCP server |
| `ORCHESTRATION_ENABLED` | `true` | Enable multi-agent orchestration |
| `ORCHESTRATION_MAX_PARALLEL_AGENTS` | `4` | Max concurrent agents |
| `ORCHESTRATION_MAX_RETRIES` | `3` | Max retries per step |

## LLM Providers

- **Ollama** (default): Install Ollama, pull a model (`ollama pull llama3.2`), and it works
- **OpenAI**: Set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `OPENAI_BASE_URL`
- **No LLM**: Memory and MCP operations work without any LLM — only `agent_run` requires one
