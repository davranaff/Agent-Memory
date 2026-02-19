# Agent Brain Backend

Current version: `1.0.0`

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

### Indexing Projects Outside This Repo (Docker)

If you analyze projects by host path (for example `/Users/...`), configure:

- `HOST_PROJECTS_ROOT` in `.env` for a host directory mounted into the `app` container.
- `PROJECT_PATH_MAPPINGS` for host-to-container translation, e.g.:

```env
HOST_PROJECTS_ROOT=..
PROJECT_PATH_MAPPINGS=/Users/your-user/Desktop=/host-projects
```

For autonomous IDE flows over MCP:
- `project_analyze` can run without `project_path`.
- server auto-captures workspace path from MCP `initialize` payload (`rootUri`/`workspaceFolders` when provided by client).
- fallback env detection is configurable:

```env
AUTONOMOUS_PROJECT_ENV_KEYS=MCP_PROJECT_PATH,IDE_PROJECT_PATH,WORKSPACE_FOLDER,WORKSPACE_ROOT,VSCODE_WORKSPACE_FOLDER,PROJECT_PATH
AUTONOMOUS_PROJECT_FALLBACK_PATH=
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

Notes:
- `memory_store` now deduplicates by content fingerprint (scoped by `agent_id` + memory scope metadata such as `project_id`/`session_id` when provided).
- `agent_run` reuses the last active session by default when `session_id` is not provided.

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
| POST | `/projects/dependencies/sync` | Sync project graph (full or incremental via `changed_files`) |
| GET | `/projects/{project_id}/graph/impact` | Impact analysis for a component |
| GET | `/projects/{project_id}/graph/path` | Path between two components |
| GET | `/projects/{project_id}/graph/neighbors` | Neighbor traversal around a component |
| POST | `/orchestration/run` | Start orchestration workflow |
| GET | `/orchestration/{run_id}` | Get run status & results |
| GET | `/orchestration/workflows/list` | List available workflows |
| GET | `/agents/runs/{run_id}` | Get async agent run status/result |

`/orchestration/run` accepts `background` (default `true`): queued runs return `status=pending`, then transition to `running/completed/failed`.
`/agents/{agent_id}/run` accepts `background` (default `true`) and returns `run_id` for polling via `/agents/runs/{run_id}`.

## MCP Integration

### Server (exposed at `/mcp/sse`)

Tools: `context_set`, `context_get`, `context_clear`, `memory_store`, `memory_search`, `memory_get`, `memory_delete`, `memory_reindex`, `agent_run`, `agent_run_status`, `agent_get_state`, `db_query`, `embeddings_create`, `orchestration_run`, `project_analyze`, `project_list`, `project_components`, `project_dependencies_analyze`, `project_graph_sync`, `project_graph_impact`, `project_graph_path`, `project_graph_neighbors`

`db_query` is enabled by default, supports read-only `SELECT`, and allows metadata queries from `information_schema`/`pg_catalog`.
`orchestration_run` supports `background=true` (default) and returns a pending `run_id` immediately.

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

### MCP Auto Context

You can set context once, then most tools auto-inject missing IDs:

```json
{
  "tool": "context_set",
  "arguments": {
    "agent_id": "<agent-uuid>",
    "project_id": "<project-uuid>"
  }
}
```

Then:
- `agent_run` can omit `agent_id` and `session_id`.
- `memory_store` can omit `agent_id`; it auto-adds `metadata.project_id/session_id` from context.
- graph tools can omit `project_id`.
- `project_analyze` can omit `project_path` if `context.project_path`/MCP initialize/env already provides it.

Note: current active MCP context is server-level (one active context at a time).

## Graph Backend (Optional)

PostgreSQL remains the system of record. The graph backend is a read-model
for dependency traversal and impact analysis.

- `GRAPH_BACKEND=inmemory`: default, zero extra infra.
- `GRAPH_BACKEND=neo4j`: uses Neo4j for graph queries.
- `GRAPH_FALLBACK_TO_INMEMORY=true`: keeps API operational if Neo4j is down.

To run Neo4j locally with Docker profile:

```bash
docker compose --profile graph up --build
```

Typical flow:

```bash
# 1) Build/sync graph projection from Postgres
curl -X POST http://localhost:8000/projects/dependencies/sync \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"<project-id>"}'

# Optional incremental sync
curl -X POST http://localhost:8000/projects/dependencies/sync \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"<project-id>","changed_files":["app/main.py","app/api/projects.py"]}'

# 2) Query impact
curl "http://localhost:8000/projects/<project-id>/graph/impact?component_id=<component-id>"
```

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
| `MCP_DB_QUERY_ENABLED` | `true` | Enable MCP `db_query` tool |
| `PROJECT_PATH_MAPPINGS` | `` | Host/container prefix mappings for project paths (`/host=/container`) |
| `AUTONOMOUS_PROJECT_ENV_KEYS` | `MCP_PROJECT_PATH,...` | Env keys used to auto-detect active IDE project path |
| `AUTONOMOUS_PROJECT_FALLBACK_PATH` | `` | Optional fallback project path for autonomous analyze |
| `HOST_PROJECTS_ROOT` | `..` | Docker Compose host directory mounted to `/host-projects` |
| `ORCHESTRATION_ENABLED` | `true` | Enable multi-agent orchestration |
| `ORCHESTRATION_MAX_PARALLEL_AGENTS` | `4` | Max concurrent agents |
| `ORCHESTRATION_MAX_RETRIES` | `3` | Max retries per step |
| `ORCHESTRATION_AUTOCREATE_AGENTS` | `true` | Auto-create missing workflow role agents (`reasoning_agent`, etc.) |
| `GRAPH_BACKEND` | `inmemory` | Graph backend (`inmemory` or `neo4j`) |
| `GRAPH_FALLBACK_TO_INMEMORY` | `true` | Fallback when Neo4j unavailable |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j Bolt URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `changeme` | Neo4j password |
| `NEO4J_DATABASE` | `neo4j` | Neo4j database |
| `API_KEY` | `` | Optional API key (sent via `X-API-Key`) |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed origins |
| `CORS_ALLOW_CREDENTIALS` | `true` | CORS credentials flag |
| `CORS_ALLOW_METHODS` | `GET,POST,PUT,PATCH,DELETE,OPTIONS` | Allowed CORS methods |
| `CORS_ALLOW_HEADERS` | `Authorization,Content-Type,X-API-Key` | Allowed CORS headers |

## LLM Providers

- **Ollama** (default): Install Ollama, pull a model (`ollama pull llama3.2`), and it works
- **OpenAI**: Set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `OPENAI_BASE_URL`
- **No LLM**: Memory and MCP operations work without any LLM — only `agent_run` requires one
