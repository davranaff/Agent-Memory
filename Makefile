SHELL := /bin/bash

COMPOSE ?= docker compose
APP_SERVICE ?= app
API_URL ?= http://localhost:10001
PROJECT_PATH ?= $(CURDIR)
PROJECT_NAME ?= $(notdir $(CURDIR))
FORCE_REINDEX ?= false
PROJECT_ID ?=

.DEFAULT_GOAL := help

.PHONY: help up up-graph build down down-build restart ps logs logs-all shell health mcp analyze \
	test test-api test-mcp test-graph test-docker migrate \
	db-projects db-components db-memories graph-projects graph-project

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Docker:"
	@echo "  up           - Start app + postgres + redis in background"
	@echo "  up-graph     - Start stack with Neo4j profile"
	@echo "  build        - Build/rebuild Docker images"
	@echo "  down         - Stop and remove containers"
	@echo "  down-build   - Run: down && build"
	@echo "  restart      - Restart core stack"
	@echo "  ps           - Show running services"
	@echo "  logs         - Follow app logs"
	@echo "  logs-all     - Follow logs for all services"
	@echo "  shell        - Open shell inside app container"
	@echo "  migrate      - Run alembic upgrade head in app container"
	@echo ""
	@echo "HTTP shortcuts:"
	@echo "  health       - GET /health"
	@echo "  mcp          - Check MCP SSE endpoint headers"
	@echo "  analyze      - POST /projects/analyze"
	@echo "                vars: PROJECT_PATH, PROJECT_NAME, FORCE_REINDEX, API_URL"
	@echo ""
	@echo "DB / Graph checks:"
	@echo "  db-projects  - List projects in Postgres"
	@echo "  db-components - Count component types for PROJECT_ID"
	@echo "  db-memories  - Count active memory types for PROJECT_ID"
	@echo "  graph-projects - List Neo4j project nodes with component counts"
	@echo "  graph-project  - Count nodes/edges in Neo4j for PROJECT_ID"
	@echo "                var: PROJECT_ID=<uuid>"
	@echo ""
	@echo "Tests:"
	@echo "  test         - Run all tests locally"
	@echo "  test-api     - Run API-focused tests locally"
	@echo "  test-mcp     - Run MCP tests locally"
	@echo "  test-graph   - Run graph tests locally"
	@echo "  test-docker  - Run all tests inside app container"

up:
	$(COMPOSE) up -d --build

up-graph:
	$(COMPOSE) --profile graph up -d --build

build:
	$(COMPOSE) build

down:
	$(COMPOSE) down

down-build: down build

restart: down up

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f $(APP_SERVICE)

logs-all:
	$(COMPOSE) logs -f

shell:
	$(COMPOSE) exec $(APP_SERVICE) sh

migrate:
	$(COMPOSE) exec $(APP_SERVICE) sh -lc 'alembic upgrade head'

health:
	curl -fsS $(API_URL)/health | python -m json.tool

mcp:
	curl -sSI $(API_URL)/mcp/sse

analyze:
	@set -e; \
	payload="$$(python -c 'import json,sys; force=sys.argv[3].strip().lower() in {"1","true","yes","y","on"}; print(json.dumps({"project_path": sys.argv[1], "project_name": sys.argv[2], "force_reindex": force, "analysis_options": {}}))' '$(PROJECT_PATH)' '$(PROJECT_NAME)' '$(FORCE_REINDEX)')" ; \
	raw="$$(curl -sS -X POST $(API_URL)/projects/analyze -H 'Content-Type: application/json' -d "$$payload" -w '\n%{http_code}')" ; \
	body="$${raw%$$'\n'*}" ; \
	code="$${raw##*$$'\n'}" ; \
	echo "$$body" | python -m json.tool >/dev/null 2>&1 && echo "$$body" | python -m json.tool || echo "$$body" ; \
	test "$$code" -ge 200 -a "$$code" -lt 300 || (echo "HTTP $$code" && exit 1)

test:
	python3 -m unittest discover -s tests -v

test-api:
	python -m unittest -v tests.test_projects_api tests.test_graph_api

test-mcp:
	python -m unittest -v tests.test_mcp_tools

test-graph:
	python -m unittest -v tests.test_graph_store tests.test_graph_api

test-docker:
	$(COMPOSE) exec $(APP_SERVICE) sh -lc 'python -m unittest discover -s tests -v'

db-projects:
	$(COMPOSE) exec postgres psql -U agent -d agent_brain -c "SELECT id, name, path, analysis_status, last_analyzed FROM projects ORDER BY last_analyzed DESC NULLS LAST LIMIT 20;"

db-components:
	@test -n "$(PROJECT_ID)" || (echo "PROJECT_ID is required"; exit 1)
	$(COMPOSE) exec postgres psql -U agent -d agent_brain -c "SELECT type, COUNT(*) AS cnt FROM components WHERE project_id = '$(PROJECT_ID)' GROUP BY type ORDER BY cnt DESC;"

db-memories:
	@test -n "$(PROJECT_ID)" || (echo "PROJECT_ID is required"; exit 1)
	$(COMPOSE) exec postgres psql -U agent -d agent_brain -c "SELECT memory_type, COUNT(*) AS cnt FROM memories WHERE is_active = true AND metadata->>'project_id' = '$(PROJECT_ID)' GROUP BY memory_type ORDER BY cnt DESC;"

graph-projects:
	$(COMPOSE) exec neo4j cypher-shell -u neo4j -p changeme "MATCH (p:Project) OPTIONAL MATCH (p)-[:HAS_COMPONENT]->(c:Component) RETURN p.id AS project_id, count(c) AS components ORDER BY components DESC, project_id;"

graph-project:
	@test -n "$(PROJECT_ID)" || (echo "PROJECT_ID is required"; exit 1)
	$(COMPOSE) exec neo4j cypher-shell -u neo4j -p changeme "MATCH (:Project {id:'$(PROJECT_ID)'})-[:HAS_COMPONENT]->(c:Component) OPTIONAL MATCH (c)-[r:DEPENDS_ON {project_id:'$(PROJECT_ID)'}]->() RETURN count(DISTINCT c) AS nodes, count(r) AS edges;"
