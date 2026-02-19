from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.indexing.analyzer import ProjectAnalyzer
from app.indexing.scanner import FileInfo


def _file_info(
    path: Path,
    *,
    language: str | None = None,
    is_documentation: bool = False,
    is_config: bool = False,
) -> FileInfo:
    return FileInfo(
        path=str(path),
        relative_path=path.name,
        size_bytes=path.stat().st_size,
        extension=path.suffix.lower(),
        language=language,
        is_binary=False,
        is_generated=False,
        is_test=False,
        is_config=is_config,
        is_documentation=is_documentation,
    )


class ProjectAnalyzerTechnologyTests(unittest.TestCase):
    def test_framework_detection_is_scoped_by_language_and_docs_ignored(self) -> None:
        analyzer = ProjectAnalyzer()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            py_file = tmp / "main.py"
            py_file.write_text(
                "from fastapi import FastAPI\napp = FastAPI()\n",
                encoding="utf-8",
            )
            readme = tmp / "README.md"
            readme.write_text(
                "react vue angular express spring rails django flask",
                encoding="utf-8",
            )

            files = [
                _file_info(py_file, language="python"),
                _file_info(readme, is_documentation=True),
            ]

            stack = analyzer.detect_technology_stack(files)
            self.assertIn("fastapi", stack["frameworks"])
            self.assertNotIn("react", stack["frameworks"])
            self.assertNotIn("vue", stack["frameworks"])
            self.assertNotIn("angular", stack["frameworks"])
            self.assertNotIn("express", stack["frameworks"])
            self.assertNotIn("spring", stack["frameworks"])
            self.assertNotIn("rails", stack["frameworks"])

    def test_database_detection_requires_explicit_database_signal(self) -> None:
        analyzer = ProjectAnalyzer()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            py_file = tmp / "db.py"
            py_file.write_text(
                "import sqlalchemy\nfrom redis import Redis\n",
                encoding="utf-8",
            )
            env_file = tmp / ".env"
            env_file.write_text("REDIS_URL=redis://localhost:6379/0\n", encoding="utf-8")

            files = [
                _file_info(py_file, language="python"),
                _file_info(env_file, is_config=True),
            ]

            stack = analyzer.detect_technology_stack(files)
            self.assertIn("redis", stack["databases"])
            self.assertNotIn("postgresql", stack["databases"])
            self.assertNotIn("mysql", stack["databases"])
            self.assertNotIn("mongodb", stack["databases"])


if __name__ == "__main__":
    unittest.main()
