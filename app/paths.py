"""Project path normalization and host->container mapping utilities."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Mapping, Sequence, Tuple
from urllib.parse import unquote, urlparse

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

DEFAULT_AUTONOMOUS_PROJECT_ENV_KEYS = (
    "MCP_PROJECT_PATH",
    "IDE_PROJECT_PATH",
    "WORKSPACE_FOLDER",
    "WORKSPACE_ROOT",
    "VSCODE_WORKSPACE_FOLDER",
    "PROJECT_PATH",
)


@dataclass(frozen=True)
class PathResolutionResult:
    """Result of project path resolution."""

    requested_path: str
    resolved_path: Path
    used_mapping: bool


def parse_project_path_mappings(raw_mappings: str) -> List[Tuple[Path, Path]]:
    """
    Parse PROJECT_PATH_MAPPINGS value.

    Expected format:
    "/host/prefix=/container/prefix,/host2=/container2"
    """
    mappings: List[Tuple[Path, Path]] = []
    for entry in raw_mappings.split(","):
        normalized_entry = entry.strip()
        if not normalized_entry:
            continue
        if "=" not in normalized_entry:
            logger.warning("Ignoring invalid PROJECT_PATH_MAPPINGS entry: %s", normalized_entry)
            continue
        host_prefix_raw, container_prefix_raw = normalized_entry.split("=", 1)
        host_prefix = host_prefix_raw.strip()
        container_prefix = container_prefix_raw.strip()
        if not host_prefix or not container_prefix:
            logger.warning("Ignoring invalid PROJECT_PATH_MAPPINGS entry: %s", normalized_entry)
            continue
        mappings.append((Path(host_prefix).expanduser(), Path(container_prefix).expanduser()))

    # Most specific prefixes should be matched first.
    mappings.sort(key=lambda item: len(str(item[0])), reverse=True)
    return mappings


def _path_from_file_uri(uri: str) -> str | None:
    """Convert file:// URI to a local path string."""
    parsed = urlparse(uri)
    if parsed.scheme and parsed.scheme != "file":
        return None
    if parsed.scheme != "file":
        return uri

    raw_path = unquote(parsed.path or "")
    if parsed.netloc and parsed.netloc not in ("", "localhost"):
        raw_path = f"//{parsed.netloc}{raw_path}"

    # Handle Windows drive letter notation: /C:/Users/...
    if len(raw_path) >= 3 and raw_path[0] == "/" and raw_path[2] == ":":
        raw_path = raw_path[1:]

    return raw_path or None


def normalize_project_path_candidates(values: Sequence[str]) -> List[str]:
    """Normalize and deduplicate candidate project paths preserving order."""
    normalized: List[str] = []
    seen: set[str] = set()

    for raw_value in values:
        if not isinstance(raw_value, str):
            continue
        candidate = raw_value.strip()
        if not candidate:
            continue
        parsed = _path_from_file_uri(candidate)
        if not parsed:
            continue
        canonical = str(Path(parsed).expanduser().resolve(strict=False))
        if canonical in seen:
            continue
        seen.add(canonical)
        normalized.append(canonical)

    return normalized


def extract_project_paths_from_mcp_params(params: Any) -> List[str]:
    """Extract candidate project paths from MCP initialize-like params."""
    if not isinstance(params, dict):
        return []

    candidates: List[str] = []

    direct_keys = (
        "project_path",
        "workspace_path",
        "workspaceRoot",
        "rootPath",
    )
    for key in direct_keys:
        value = params.get(key)
        if isinstance(value, str):
            candidates.append(value)

    for key in ("rootUri", "root_uri"):
        value = params.get(key)
        if isinstance(value, str):
            candidates.append(value)

    collection_keys = ("workspaceFolders", "workspace_folders", "roots")
    for key in collection_keys:
        collection = params.get(key)
        if not isinstance(collection, list):
            continue
        for item in collection:
            if isinstance(item, str):
                candidates.append(item)
                continue
            if not isinstance(item, dict):
                continue

            for path_key in ("path", "project_path", "workspace_path", "rootPath"):
                path_value = item.get(path_key)
                if isinstance(path_value, str):
                    candidates.append(path_value)

            for uri_key in ("uri", "rootUri"):
                uri_value = item.get(uri_key)
                if isinstance(uri_value, str):
                    candidates.append(uri_value)

    return normalize_project_path_candidates(candidates)


def project_path_candidates_from_env(
    raw_env_keys: str | None = None,
    fallback_path: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> List[str]:
    """Collect candidate project paths from environment variables."""
    env_map = environ or os.environ
    if raw_env_keys:
        env_keys = [item.strip() for item in raw_env_keys.split(",") if item.strip()]
    else:
        env_keys = list(DEFAULT_AUTONOMOUS_PROJECT_ENV_KEYS)

    candidates: List[str] = []
    for key in env_keys:
        value = env_map.get(key)
        if isinstance(value, str):
            candidates.append(value)

    if fallback_path:
        candidates.append(fallback_path)

    return normalize_project_path_candidates(candidates)


def resolve_project_path(project_path: str, raw_mappings: str | None = None) -> PathResolutionResult:
    """Resolve project path and optionally apply host->container prefix mapping."""
    requested = Path(project_path).expanduser().resolve(strict=False)
    if requested.exists() and requested.is_dir():
        return PathResolutionResult(
            requested_path=project_path,
            resolved_path=requested,
            used_mapping=False,
        )

    mappings_value = (
        raw_mappings if raw_mappings is not None else get_settings().project_path_mappings
    )
    mappings = parse_project_path_mappings(mappings_value)

    for host_prefix, container_prefix in mappings:
        normalized_host = host_prefix.resolve(strict=False)
        try:
            relative_suffix = requested.relative_to(normalized_host)
        except ValueError:
            continue

        translated = (container_prefix / relative_suffix).resolve(strict=False)
        if translated.exists() and translated.is_dir():
            return PathResolutionResult(
                requested_path=project_path,
                resolved_path=translated,
                used_mapping=True,
            )

    return PathResolutionResult(
        requested_path=project_path,
        resolved_path=requested,
        used_mapping=False,
    )
