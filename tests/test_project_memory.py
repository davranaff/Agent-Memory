from __future__ import annotations

import unittest

from app.services.project_memory import (
    build_project_memory_entries,
    persist_project_memories,
)


class _FakeMemoryStore:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def store(
        self,
        content: str,
        memory_type: str = "general",
        agent_id=None,
        metadata: dict | None = None,
        importance: int = 5,
    ) -> dict:
        self.calls.append(
            {
                "content": content,
                "memory_type": memory_type,
                "agent_id": agent_id,
                "metadata": metadata or {},
                "importance": importance,
            }
        )
        return {
            "id": f"id-{len(self.calls)}",
            "created": True,
            "deduplicated": False,
        }


class ProjectMemoryTests(unittest.IsolatedAsyncioTestCase):
    def test_build_project_memory_entries(self) -> None:
        summary = {
            "project": {
                "id": "p1",
                "name": "Agent Memory",
                "path": "/host-projects/agents memory",
                "architecture_type": "layered",
                "languages": ["python"],
                "frameworks": ["fastapi"],
                "databases": ["postgresql"],
                "build_tools": ["docker"],
                "total_files": 10,
                "total_lines": 200,
            },
            "components": {
                "file": {"count": 12, "avg_complexity": 1.2},
                "function": {"count": 4, "avg_complexity": 2.0},
            },
            "documentation_count": 3,
            "metadata": {"name": "agent-memory", "version": "0.1.0"},
        }

        entries = build_project_memory_entries(summary)
        self.assertEqual(len(entries), 4)
        self.assertEqual(
            [entry["memory_type"] for entry in entries],
            [
                "project_summary",
                "project_architecture",
                "database_structure",
                "service_architecture",
            ],
        )
        self.assertTrue(all(entry["content"] for entry in entries))

    async def test_persist_project_memories(self) -> None:
        summary = {
            "project": {
                "id": "p1",
                "name": "Agent Memory",
                "path": "/host-projects/agents memory",
            }
        }
        store = _FakeMemoryStore()

        result = await persist_project_memories(
            store,
            summary,
            project_id="p1",
            project_name="Agent Memory",
            project_path="/host-projects/agents memory",
        )

        self.assertEqual(result["stored"], 4)
        self.assertEqual(result["created"], 4)
        self.assertEqual(result["deduplicated"], 0)
        self.assertEqual(len(result["memory_ids"]), 4)
        self.assertEqual(len(store.calls), 4)
        self.assertTrue(all(call["metadata"]["project_id"] == "p1" for call in store.calls))
        self.assertTrue(all(call["metadata"]["source"] == "project_analyze" for call in store.calls))


if __name__ == "__main__":
    unittest.main()
