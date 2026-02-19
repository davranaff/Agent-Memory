"""Helpers to persist project-level memory snapshots into Brain."""

from __future__ import annotations

from typing import Any, Protocol


class _MemoryStoreProtocol(Protocol):
    async def store(
        self,
        content: str,
        memory_type: str = "general",
        agent_id: Any = None,
        metadata: dict[str, Any] | None = None,
        importance: int = 5,
    ) -> dict[str, Any]:
        ...


def _csv(values: list[Any] | None, fallback: str = "none") -> str:
    cleaned = [str(v).strip() for v in (values or []) if str(v).strip()]
    return ", ".join(cleaned) if cleaned else fallback


def _component_distribution(components: dict[str, Any]) -> tuple[int, str]:
    items: list[tuple[str, int]] = []
    total = 0

    for component_type, stats in components.items():
        if not isinstance(stats, dict):
            continue
        count = int(stats.get("count") or 0)
        if count <= 0:
            continue
        total += count
        items.append((str(component_type), count))

    if not items:
        return 0, "none"

    items.sort(key=lambda x: x[1], reverse=True)
    top = items[:8]
    return total, ", ".join(f"{name}:{count}" for name, count in top)


def build_project_memory_entries(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Build deterministic project memory entries from project summary payload."""
    project = summary.get("project") if isinstance(summary, dict) else {}
    project = project if isinstance(project, dict) else {}
    components = summary.get("components") if isinstance(summary, dict) else {}
    components = components if isinstance(components, dict) else {}
    metadata = summary.get("metadata") if isinstance(summary, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}

    project_name = str(project.get("name") or "unknown")
    project_id = str(project.get("id") or "unknown")
    project_path = str(project.get("path") or "unknown")
    architecture = str(project.get("architecture_type") or "unknown")
    languages = _csv(project.get("languages") if isinstance(project.get("languages"), list) else [])
    frameworks = _csv(project.get("frameworks") if isinstance(project.get("frameworks"), list) else [])
    databases = _csv(project.get("databases") if isinstance(project.get("databases"), list) else [])
    build_tools = _csv(project.get("build_tools") if isinstance(project.get("build_tools"), list) else [])
    total_files = int(project.get("total_files") or 0)
    total_lines = int(project.get("total_lines") or 0)
    documentation_count = int(summary.get("documentation_count") or 0)
    total_components, component_distribution = _component_distribution(components)
    metadata_keys = _csv(sorted(metadata.keys())) if metadata else "none"

    return [
        {
            "memory_type": "project_summary",
            "importance": 9,
            "content": (
                f"Project {project_name} ({project_id}) at {project_path}. "
                f"Architecture={architecture}. Languages={languages}. Frameworks={frameworks}. "
                f"Databases={databases}. BuildTools={build_tools}. "
                f"Files={total_files}. Lines={total_lines}. Components={total_components}. "
                f"Documentation={documentation_count}."
            ),
        },
        {
            "memory_type": "project_architecture",
            "importance": 8,
            "content": (
                f"Architecture profile for {project_name}: type={architecture}; "
                f"languages={languages}; frameworks={frameworks}; "
                f"component_distribution={component_distribution}; metadata_keys={metadata_keys}."
            ),
        },
        {
            "memory_type": "database_structure",
            "importance": 7,
            "content": (
                f"Database profile for {project_name}: detected_databases={databases}; "
                f"build_tools={build_tools}; architecture={architecture}. "
                "If detected_databases=none then no explicit database layer was found during static analysis."
            ),
        },
        {
            "memory_type": "service_architecture",
            "importance": 7,
            "content": (
                f"Service/component profile for {project_name}: "
                f"component_distribution={component_distribution}; "
                f"total_component_types={len(components)}; total_components={total_components}; "
                f"languages={languages}; frameworks={frameworks}."
            ),
        },
    ]


async def persist_project_memories(
    memory_store: _MemoryStoreProtocol,
    summary: dict[str, Any],
    *,
    project_id: str,
    project_name: str | None = None,
    project_path: str | None = None,
    agent_id: Any = None,
) -> dict[str, Any]:
    """Persist project profile memories and return write statistics."""
    entries = build_project_memory_entries(summary)
    created = 0
    deduplicated = 0
    memory_ids: list[str] = []

    base_metadata: dict[str, Any] = {
        "project_id": project_id,
        "project_name": project_name,
        "project_path": project_path,
        "source": "project_analyze",
    }

    for entry in entries:
        metadata = dict(base_metadata)
        metadata["profile_type"] = entry["memory_type"]
        result = await memory_store.store(
            content=entry["content"],
            memory_type=entry["memory_type"],
            agent_id=agent_id,
            metadata=metadata,
            importance=entry["importance"],
        )
        if result.get("created"):
            created += 1
        if result.get("deduplicated"):
            deduplicated += 1
        if result.get("id"):
            memory_ids.append(str(result["id"]))

    return {
        "stored": len(entries),
        "created": created,
        "deduplicated": deduplicated,
        "memory_ids": memory_ids,
    }
