from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.agent.tools import (
    get_builtin_tools,
    reset_tool_runtime_context,
    set_tool_runtime_context,
)


class AgentFilesystemToolsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._project_root = Path(self._tmp.name)
        self._token = set_tool_runtime_context({"project_path": str(self._project_root)})
        self._tools = {tool.name: tool for tool in get_builtin_tools()}

    async def asyncTearDown(self) -> None:
        reset_tool_runtime_context(self._token)
        self._tmp.cleanup()

    async def test_write_read_append_and_list(self) -> None:
        write_tool = self._tools["project_file_write"]
        append_tool = self._tools["project_file_append"]
        read_tool = self._tools["project_file_read"]
        list_tool = self._tools["project_list_files"]

        write_result = await write_tool.ainvoke(
            {"path": "src/example.py", "content": "print('hi')\n", "overwrite": True}
        )
        self.assertIn("Wrote", write_result)
        self.assertTrue((self._project_root / "src/example.py").exists())

        append_result = await append_tool.ainvoke(
            {"path": "src/example.py", "content": "print('bye')\n"}
        )
        self.assertIn("Appended", append_result)

        read_result = await read_tool.ainvoke(
            {"path": "src/example.py", "start_line": 1, "end_line": 10}
        )
        self.assertIn("1: print('hi')", read_result)
        self.assertIn("2: print('bye')", read_result)

        list_result = await list_tool.ainvoke({"limit": 50})
        self.assertIn("src/example.py", list_result)

    async def test_write_blocks_paths_outside_project_root(self) -> None:
        write_tool = self._tools["project_file_write"]
        with self.assertRaises(ValueError):
            await write_tool.ainvoke({"path": "../outside.py", "content": "x = 1\n"})

    async def test_tools_require_project_path_context(self) -> None:
        list_tool = self._tools["project_list_files"]
        reset_tool_runtime_context(self._token)
        missing_context_token = set_tool_runtime_context({})
        try:
            with self.assertRaises(ValueError):
                await list_tool.ainvoke({"limit": 10})
        finally:
            reset_tool_runtime_context(missing_context_token)
            self._token = set_tool_runtime_context({"project_path": str(self._project_root)})


if __name__ == "__main__":
    unittest.main()

