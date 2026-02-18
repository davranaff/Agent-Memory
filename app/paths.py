"""Project path normalization and host->container mapping utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


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
