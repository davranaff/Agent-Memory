from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.paths import parse_project_path_mappings, resolve_project_path


class PathResolutionTests(unittest.TestCase):
    def test_resolve_existing_path_without_mapping(self) -> None:
        with TemporaryDirectory() as project_dir:
            result = resolve_project_path(project_dir, raw_mappings="")
            self.assertEqual(result.resolved_path, Path(project_dir).resolve())
            self.assertFalse(result.used_mapping)

    def test_resolve_path_with_mapping(self) -> None:
        with TemporaryDirectory() as host_root, TemporaryDirectory() as container_root:
            mapped_project = Path(container_root) / "repo"
            mapped_project.mkdir()
            requested_path = str(Path(host_root) / "repo")

            result = resolve_project_path(
                requested_path,
                raw_mappings=f"{host_root}={container_root}",
            )

            self.assertEqual(result.resolved_path, mapped_project.resolve())
            self.assertTrue(result.used_mapping)

    def test_resolve_uses_most_specific_mapping_prefix(self) -> None:
        with TemporaryDirectory() as host_root, TemporaryDirectory() as container_root:
            host_root_path = Path(host_root)
            specific_host_prefix = host_root_path / "workspace"
            specific_container_prefix = Path(container_root) / "mapped-workspace"
            generic_container_prefix = Path(container_root) / "mapped-generic"
            specific_container_prefix.mkdir()
            generic_container_prefix.mkdir()
            (specific_container_prefix / "repo").mkdir()

            requested_path = str(specific_host_prefix / "repo")
            mappings = (
                f"{host_root_path}={generic_container_prefix},"
                f"{specific_host_prefix}={specific_container_prefix}"
            )

            result = resolve_project_path(requested_path, raw_mappings=mappings)
            self.assertEqual(result.resolved_path, (specific_container_prefix / "repo").resolve())
            self.assertTrue(result.used_mapping)

    def test_parse_ignores_invalid_entries(self) -> None:
        mappings = parse_project_path_mappings("/a=/b,invalid-entry,/c=/d")
        self.assertEqual(len(mappings), 2)


if __name__ == "__main__":
    unittest.main()
