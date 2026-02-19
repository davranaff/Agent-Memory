"""Built-in tools available to the LangGraph agent."""

from __future__ import annotations

from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

_TOOL_RUNTIME_CONTEXT: ContextVar[dict[str, Any]] = ContextVar(
    "agent_tool_runtime_context",
    default={},
)

_MAX_READ_LINES = 800
_MAX_WRITE_CHARS = 500_000
_DEFAULT_LIST_LIMIT = 200
_MAX_LIST_LIMIT = 1000
_SKIP_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
}


def set_tool_runtime_context(context: dict[str, Any]) -> Token:
    """Set per-run context for tools (project scope, IDs, etc.)."""
    return _TOOL_RUNTIME_CONTEXT.set(dict(context or {}))


def reset_tool_runtime_context(token: Token) -> None:
    """Reset per-run tool context."""
    _TOOL_RUNTIME_CONTEXT.reset(token)


def _runtime_context() -> dict[str, Any]:
    return dict(_TOOL_RUNTIME_CONTEXT.get({}) or {})


def _project_root() -> Path:
    context = _runtime_context()
    raw = str(context.get("project_path") or "").strip()
    if not raw:
        raise ValueError(
            "project_path is required in agent context. "
            "Run project_analyze/context_set first so file tools are scoped."
        )
    root = Path(raw).expanduser().resolve(strict=False)
    return root


def _resolve_target_path(path: str) -> tuple[Path, Path]:
    root = _project_root()
    raw = (path or "").strip()
    if not raw:
        raise ValueError("path is required")
    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve(strict=False)
    else:
        resolved = (root / candidate).resolve(strict=False)

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"Path '{raw}' is outside project root '{root}'."
        ) from exc
    return root, resolved


def _read_text_lines(target: Path) -> list[str]:
    try:
        text = target.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError as exc:
        raise ValueError(f"File not found: {target}") from exc
    return text.splitlines()


@tool
async def memory_store(content: str, memory_type: str = "general", importance: int = 5) -> str:
    """Use this tool to persist durable facts and decisions."""
    return f"Stored memory: {content[:100]}"


@tool
async def memory_search(query: str, top_k: int = 5) -> str:
    """Use this tool first to recover prior context before reasoning."""
    return f"Searching memory for: {query}"


@tool
async def memory_get(memory_id: str) -> str:
    """Use this tool for exact memory lookup by known ID."""
    return f"Getting memory: {memory_id}"


@tool("project_list_files")
async def project_list_files(limit: int = _DEFAULT_LIST_LIMIT) -> str:
    """List project files within active project root. Use this before editing files."""
    root = _project_root()
    effective_limit = max(1, min(int(limit), _MAX_LIST_LIMIT))
    files: list[str] = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in file_path.parts):
            continue
        files.append(str(file_path.relative_to(root)))
        if len(files) >= effective_limit:
            break

    files.sort()
    if not files:
        return f"No files found in project root: {root}"
    joined = "\n".join(files)
    return f"Project files ({len(files)}):\n{joined}"


@tool("project_file_read")
async def project_file_read(path: str, start_line: int = 1, end_line: int = 200) -> str:
    """Read file content from active project. Path is relative to project root unless absolute inside root."""
    _, target = _resolve_target_path(path)
    lines = _read_text_lines(target)
    if start_line < 1:
        start_line = 1
    if end_line < start_line:
        end_line = start_line
    if (end_line - start_line + 1) > _MAX_READ_LINES:
        end_line = start_line + _MAX_READ_LINES - 1

    start_idx = start_line - 1
    end_idx = min(len(lines), end_line)
    snippet = lines[start_idx:end_idx]
    rendered = "\n".join(
        f"{idx}: {line}"
        for idx, line in enumerate(snippet, start=start_line)
    )
    return f"Read {target} lines {start_line}-{end_idx}:\n{rendered}"


@tool("project_file_write")
async def project_file_write(
    path: str,
    content: str,
    overwrite: bool = True,
    create_dirs: bool = True,
) -> str:
    """Write file in active project. Use for creating/updating code files."""
    root, target = _resolve_target_path(path)
    if len(content) > _MAX_WRITE_CHARS:
        raise ValueError(f"content is too large (max {_MAX_WRITE_CHARS} chars)")
    if target.exists() and not overwrite:
        raise ValueError(f"File already exists and overwrite=false: {target}")
    if create_dirs:
        target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    rel = target.relative_to(root)
    return f"Wrote {len(content)} chars to {rel}"


@tool("project_file_append")
async def project_file_append(
    path: str,
    content: str,
    create_file: bool = True,
) -> str:
    """Append content to a file in active project."""
    root, target = _resolve_target_path(path)
    if len(content) > _MAX_WRITE_CHARS:
        raise ValueError(f"content is too large (max {_MAX_WRITE_CHARS} chars)")
    if not target.exists():
        if not create_file:
            raise ValueError(f"File not found: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    with target.open("a", encoding="utf-8") as handle:
        handle.write(content)
    rel = target.relative_to(root)
    return f"Appended {len(content)} chars to {rel}"


def get_builtin_tools() -> list[Any]:
    """Return the list of built-in tools."""
    return [
        memory_store,
        memory_search,
        memory_get,
        project_list_files,
        project_file_read,
        project_file_write,
        project_file_append,
    ]

