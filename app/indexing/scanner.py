"""Project scanner for discovering files and directories."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass

from app.parsing import get_parser_by_file


@dataclass
class FileInfo:
    """Information about a discovered file."""
    path: str
    relative_path: str
    size_bytes: int
    extension: str
    language: Optional[str]
    is_binary: bool
    is_generated: bool
    is_test: bool
    is_config: bool
    is_documentation: bool


@dataclass 
class DirectoryInfo:
    """Information about a discovered directory."""
    path: str
    relative_path: str
    file_count: int
    subdirectory_count: int
    total_size_bytes: int


class ProjectScanner:
    """Scans project directory structure and discovers files."""

    def __init__(self, 
                 ignore_patterns: Optional[List[str]] = None,
                 max_file_size_mb: int = 10,
                 include_generated: bool = False) -> None:
        self.ignore_patterns = ignore_patterns or self._default_ignore_patterns()
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.include_generated = include_generated

    def _default_ignore_patterns(self) -> List[str]:
        """Default patterns to ignore during scanning."""
        return [
            # Version control
            ".git", ".svn", ".hg",
            # Dependencies and build artifacts
            "node_modules", ".venv", "venv", "env", 
            "__pycache__", ".pytest_cache", ".mypy_cache",
            "target", "build", "dist", "out",
            # IDE files
            ".vscode", ".idea", ".eclipse", ".vs",
            # OS files
            ".DS_Store", "Thumbs.db",
            # Logs and temporary
            "*.log", "*.tmp", "*.temp", "*.swp", "*.swo",
            # Generated files
            "*.pyc", "*.pyo", "*.pyd", "*.class",
            "*.egg-info", "*.dist-info",
        ]

    def should_ignore_path(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        path_str = str(path)
        
        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if pattern.startswith('*'):
                if path.name.endswith(pattern[1:]):
                    return True
            elif pattern in path_str:
                return True
        
        return False

    def is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except (IOError, OSError):
            return True

    def is_generated_file(self, file_path: Path) -> bool:
        """Check if file is auto-generated."""
        generated_indicators = [
            "generated", "auto-generated", "do not edit",
            "code generated", "automatically generated"
        ]
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [f.readline().strip() for _ in range(5)]
                content = ' '.join(first_lines).lower()
                
                for indicator in generated_indicators:
                    if indicator in content:
                        return True
        except (IOError, OSError, UnicodeDecodeError):
            pass
        
        return False

    def is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file."""
        test_patterns = [
            "test_", "_test.", "spec_", "_spec.",
            "tests/", "test/", "__tests__/",
            ".test.", ".spec."
        ]
        
        path_str = str(file_path).lower()
        return any(pattern in path_str for pattern in test_patterns)

    def is_config_file(self, file_path: Path) -> bool:
        """Check if file is a configuration file."""
        config_extensions = {
            ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
            ".conf", ".config", ".env", ".dockerfile", "dockerfile"
        }
        
        config_names = {
            "package.json", "requirements.txt", "pipfile", "poetry.lock",
            "cargo.toml", "pom.xml", "build.gradle", "webpack.config.js",
            "tsconfig.json", "babel.config.js", ".eslintrc.js", "prettier.config.js"
        }
        
        extension_match = file_path.suffix.lower() in config_extensions
        name_match = file_path.name.lower() in config_names
        
        return extension_match or name_match

    def is_documentation_file(self, file_path: Path) -> bool:
        """Check if file is documentation."""
        doc_extensions = {".md", ".rst", ".txt", ".pdf", ".doc", ".docx"}
        doc_names = {"readme", "changelog", "license", "contributing", "install"}
        
        extension_match = file_path.suffix.lower() in doc_extensions
        name_match = file_path.name.lower().startswith(tuple(doc_names))
        
        return extension_match or name_match

    def scan_file(self, file_path: Path, project_root: Path) -> FileInfo:
        """Scan a single file and extract information."""
        relative_path = str(file_path.relative_to(project_root))
        
        try:
            stat = file_path.stat()
            size_bytes = stat.st_size
        except (OSError, IOError):
            size_bytes = 0

        extension = file_path.suffix.lower()
        is_binary = self.is_binary_file(file_path)
        is_generated = self.is_generated_file(file_path) if not is_binary else False
        is_test = self.is_test_file(file_path)
        is_config = self.is_config_file(file_path)
        is_documentation = self.is_documentation_file(file_path)
        
        # Detect language
        language = None
        if not is_binary:
            parser = get_parser_by_file(str(file_path))
            if parser:
                language = parser.language

        return FileInfo(
            path=str(file_path),
            relative_path=relative_path,
            size_bytes=size_bytes,
            extension=extension,
            language=language,
            is_binary=is_binary,
            is_generated=is_generated and not self.include_generated,
            is_test=is_test,
            is_config=is_config,
            is_documentation=is_documentation
        )

    def scan_directory(self, dir_path: Path, project_root: Path) -> DirectoryInfo:
        """Scan a directory and extract information."""
        relative_path = str(dir_path.relative_to(project_root))
        
        file_count = 0
        subdirectory_count = 0
        total_size_bytes = 0
        
        try:
            for item in dir_path.iterdir():
                if self.should_ignore_path(item):
                    continue
                    
                if item.is_file():
                    file_count += 1
                    try:
                        total_size_bytes += item.stat().st_size
                    except (OSError, IOError):
                        pass
                elif item.is_dir():
                    subdirectory_count += 1
        except (OSError, PermissionError):
            pass

        return DirectoryInfo(
            path=str(dir_path),
            relative_path=relative_path,
            file_count=file_count,
            subdirectory_count=subdirectory_count,
            total_size_bytes=total_size_bytes
        )

    def scan_project(self, project_path: str) -> Tuple[List[FileInfo], List[DirectoryInfo]]:
        """Scan entire project structure."""
        project_root = Path(project_path).resolve()
        
        if not project_root.exists() or not project_root.is_dir():
            raise ValueError(f"Invalid project path: {project_path}")

        files: List[FileInfo] = []
        directories: List[DirectoryInfo] = []

        # Walk through directory tree
        for root, dirs, filenames in os.walk(project_root):
            root_path = Path(root)
            
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self.should_ignore_path(root_path / d)]
            
            # Scan directory
            if root_path != project_root:  # Skip root directory for now
                try:
                    dir_info = self.scan_directory(root_path, project_root)
                    directories.append(dir_info)
                except Exception:
                    pass
            
            # Scan files
            for filename in filenames:
                file_path = root_path / filename
                
                if self.should_ignore_path(file_path):
                    continue
                
                # Skip files that are too large
                try:
                    if file_path.stat().st_size > self.max_file_size_bytes:
                        continue
                except (OSError, IOError):
                    continue
                
                try:
                    file_info = self.scan_file(file_path, project_root)
                    if not file_info.is_generated:  # Skip generated files unless included
                        files.append(file_info)
                except Exception:
                    continue

        return files, directories

    def get_file_statistics(self, files: List[FileInfo]) -> Dict[str, any]:
        """Get statistics about discovered files."""
        total_files = len(files)
        total_size = sum(f.size_bytes for f in files)
        
        language_counts: Dict[str, int] = {}
        binary_count = 0
        test_count = 0
        config_count = 0
        documentation_count = 0
        
        for file_info in files:
            if file_info.is_binary:
                binary_count += 1
            else:
                if file_info.language:
                    language_counts[file_info.language] = language_counts.get(file_info.language, 0) + 1
            
            if file_info.is_test:
                test_count += 1
            if file_info.is_config:
                config_count += 1
            if file_info.is_documentation:
                documentation_count += 1

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "binary_files": binary_count,
            "source_files": total_files - binary_count,
            "test_files": test_count,
            "config_files": config_count,
            "documentation_files": documentation_count,
            "language_distribution": language_counts,
            "most_common_language": max(language_counts.items(), key=lambda x: x[1])[0] if language_counts else None
        }

    def get_directory_statistics(self, directories: List[DirectoryInfo]) -> Dict[str, any]:
        """Get statistics about discovered directories."""
        total_directories = len(directories)
        total_files = sum(d.file_count for d in directories)
        total_subdirectories = sum(d.subdirectory_count for d in directories)
        total_size = sum(d.total_size_bytes for d in directories)
        
        # Find largest directories
        largest_dirs = sorted(directories, key=lambda d: d.total_size_bytes, reverse=True)[:10]
        
        return {
            "total_directories": total_directories,
            "total_files_in_dirs": total_files,
            "total_subdirectories": total_subdirectories,
            "total_size_bytes": total_size,
            "largest_directories": [
                {
                    "path": d.relative_path,
                    "file_count": d.file_count,
                    "size_bytes": d.total_size_bytes
                }
                for d in largest_dirs
            ]
        }
