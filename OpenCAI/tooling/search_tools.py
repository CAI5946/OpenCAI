"""Local search tools."""

from __future__ import annotations

import fnmatch
from pathlib import Path
import shutil
import subprocess
from typing import Any, Iterable

from OpenCAI.tooling.contracts import ToolResult, ToolSpec, tool_result
from OpenCAI.tooling.common import coerce_positive_int
from OpenCAI.tooling.path_utils import display_path, resolve_child_path


SKIPPED_SEARCH_DIRS = {".git", ".venv", "__pycache__", "node_modules", "venv"}
DEFAULT_MAX_RESULTS = 50
MAX_MAX_RESULTS = 500
DEFAULT_MAX_BYTES = 200000
MAX_MAX_BYTES = 2000000


def _resolve_search_path(arguments: dict[str, Any], cwd: Path, tool_name: str) -> tuple[Path | None, str | None]:
    path = arguments.get("path", ".")
    if not isinstance(path, str) or not path:
        return None, "Missing string argument: path"
    target = resolve_child_path(cwd, path)
    if target is None:
        return None, f"Path escapes workspace: {path}"
    return target, None


def _is_skipped(path: Path) -> bool:
    return any(part in SKIPPED_SEARCH_DIRS for part in path.parts)


def _iter_text_files(target: Path) -> Iterable[Path]:
    if target.is_file():
        yield target
        return

    for path in target.rglob("*"):
        if _is_skipped(path):
            continue
        if path.is_file():
            yield path


def _format_search_content(
    matches: list[dict[str, Any]],
    truncated: bool,
    skipped: list[str],
) -> str:
    if not matches:
        content = "No matches found."
    else:
        content = "\n".join(
            f"{match['path']}:{match['line']}: {match['text']}" for match in matches
        )

    if truncated:
        content += "\n[truncated: narrow the search path or pattern for more results.]"
    if skipped:
        content += f"\n[skipped unreadable files: {len(skipped)}]"

    return content


def list_files(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    target, error = _resolve_search_path(arguments, cwd, "list_files")
    if error is not None or target is None:
        return tool_result("list_files", False, error=error)
    if not target.exists():
        return tool_result("list_files", False, error=f"Path does not exist: {arguments.get('path', '.')}")
    if not target.is_dir():
        return tool_result("list_files", False, error=f"Path is not a directory: {arguments.get('path', '.')}")

    max_results = coerce_positive_int(arguments.get("max_results"), DEFAULT_MAX_RESULTS, 1, MAX_MAX_RESULTS)
    entries: list[dict[str, Any]] = []
    for child in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        if child.name in SKIPPED_SEARCH_DIRS:
            continue
        entries.append(
            {
                "path": display_path(child, cwd),
                "name": child.name,
                "is_dir": child.is_dir(),
                "is_file": child.is_file(),
                "size": child.stat().st_size if child.is_file() else None,
            }
        )
        if len(entries) >= max_results:
            break

    return tool_result(
        "list_files",
        True,
        {
            "path": display_path(target, cwd),
            "entries": entries,
            "truncated": len(entries) >= max_results,
        },
    )


def glob_files(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    pattern = arguments.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        return tool_result("glob_files", False, error="Missing required string argument: pattern")
    target, error = _resolve_search_path(arguments, cwd, "glob_files")
    if error is not None or target is None:
        return tool_result("glob_files", False, error=error)
    if not target.exists():
        return tool_result("glob_files", False, error=f"Path does not exist: {arguments.get('path', '.')}")

    max_results = coerce_positive_int(arguments.get("max_results"), DEFAULT_MAX_RESULTS, 1, MAX_MAX_RESULTS)
    matches: list[str] = []
    for path in sorted(target.glob(pattern), key=lambda item: display_path(item, cwd).lower()):
        if _is_skipped(path):
            continue
        matches.append(display_path(path, cwd))
        if len(matches) >= max_results:
            break

    return tool_result(
        "glob_files",
        True,
        {
            "path": display_path(target, cwd),
            "pattern": pattern,
            "matches": matches,
            "truncated": len(matches) >= max_results,
        },
    )


def search_files(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    pattern = arguments.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        return tool_result("search_files", False, error="Missing required string argument: pattern")

    target, error = _resolve_search_path(arguments, cwd, "search_files")
    if error is not None or target is None:
        return tool_result("search_files", False, error=error)
    if not target.exists():
        return tool_result("search_files", False, error=f"Search path does not exist: {arguments.get('path', '.')}")

    max_matches = coerce_positive_int(arguments.get("max_results"), DEFAULT_MAX_RESULTS, 1, MAX_MAX_RESULTS)
    max_bytes = coerce_positive_int(arguments.get("max_bytes"), DEFAULT_MAX_BYTES, 1, MAX_MAX_BYTES)
    case_sensitive = bool(arguments.get("case_sensitive", True))
    include = arguments.get("include")
    exclude = arguments.get("exclude")
    if include is not None and not isinstance(include, str):
        return tool_result("search_files", False, error="include must be a string")
    if exclude is not None and not isinstance(exclude, str):
        return tool_result("search_files", False, error="exclude must be a string")

    rg_result = _search_with_rg(
        pattern=pattern,
        target=target,
        cwd=cwd,
        max_matches=max_matches,
        max_bytes=max_bytes,
        case_sensitive=case_sensitive,
        include=include,
        exclude=exclude,
    )
    if rg_result is not None:
        return rg_result

    matches: list[dict[str, Any]] = []
    skipped: list[str] = []
    bytes_read = 0
    needle = pattern if case_sensitive else pattern.lower()

    for file_path in _iter_text_files(target):
        relative = display_path(file_path, cwd)
        if include is not None and not fnmatch.fnmatch(file_path.name, include) and not fnmatch.fnmatch(relative, include):
            continue
        if exclude is not None and (fnmatch.fnmatch(file_path.name, exclude) or fnmatch.fnmatch(relative, exclude)):
            continue
        try:
            raw = file_path.read_bytes()
            bytes_read += len(raw)
            if bytes_read > max_bytes:
                return tool_result(
                    "search_files",
                    True,
                    {
                        "path": display_path(target, cwd),
                        "content": _format_search_content(matches, True, skipped),
                        "pattern": pattern,
                        "matches": matches,
                        "truncated": True,
                        "skipped": skipped,
                        "backend": "python",
                    },
                )
            lines = raw.decode("utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            skipped.append(relative)
            continue

        for line_number, line in enumerate(lines, start=1):
            haystack = line if case_sensitive else line.lower()
            column = haystack.find(needle)
            if column != -1:
                matches.append(
                    {
                        "path": relative,
                        "line": line_number,
                        "column": column + 1,
                        "text": line.strip(),
                    }
                )
                if len(matches) >= max_matches:
                    return tool_result(
                        "search_files",
                        True,
                        {
                            "path": display_path(target, cwd),
                            "content": _format_search_content(matches, True, skipped),
                            "pattern": pattern,
                            "matches": matches,
                            "truncated": True,
                            "skipped": skipped,
                            "backend": "python",
                        },
                    )

    return tool_result(
        "search_files",
        True,
        {
            "path": display_path(target, cwd),
            "content": _format_search_content(matches, False, skipped),
            "pattern": pattern,
            "matches": matches,
            "truncated": False,
            "skipped": skipped,
            "backend": "python",
        },
    )


def _search_with_rg(
    *,
    pattern: str,
    target: Path,
    cwd: Path,
    max_matches: int,
    max_bytes: int,
    case_sensitive: bool,
    include: str | None,
    exclude: str | None,
) -> ToolResult | None:
    rg = shutil.which("rg")
    if rg is None:
        return None

    command = [
        rg,
        "--line-number",
        "--column",
        "--with-filename",
        "--no-heading",
        "--color",
        "never",
        "--max-count",
        str(max_matches),
        "--max-filesize",
        str(max_bytes),
    ]
    if not case_sensitive:
        command.append("--ignore-case")
    if include:
        command.extend(["--glob", include])
    if exclude:
        command.extend(["--glob", f"!{exclude}"])
    for skipped in sorted(SKIPPED_SEARCH_DIRS):
        command.extend(["--glob", f"!**/{skipped}/**"])
    target_arg = display_path(target, cwd)
    command.extend(["--", pattern, target_arg])

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode not in {0, 1}:
        return None

    matches: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        file_path, line_no, column, text = _parse_rg_line(line)
        if file_path is None:
            continue
        matches.append(
            {
                "path": display_path(Path(file_path), cwd),
                "line": line_no,
                "column": column,
                "text": text.strip(),
            }
        )
        if len(matches) >= max_matches:
            break

    return tool_result(
        "search_files",
        True,
        {
            "path": display_path(target, cwd),
            "content": _format_search_content(matches, len(matches) >= max_matches, []),
            "pattern": pattern,
            "matches": matches,
            "truncated": len(matches) >= max_matches,
            "skipped": [],
            "backend": "rg",
        },
    )


def _parse_rg_line(line: str) -> tuple[str | None, int, int, str]:
    first, sep, rest = line.partition(":")
    if not sep:
        return None, 0, 0, ""
    line_no, sep, rest = rest.partition(":")
    if not sep:
        return None, 0, 0, ""
    column, sep, text = rest.partition(":")
    if not sep:
        return None, 0, 0, ""
    try:
        return first, int(line_no), int(column), text
    except ValueError:
        return None, 0, 0, ""


SEARCH_TOOLS: dict[str, ToolSpec] = {
    "list_files": ToolSpec(
        name="list_files",
        description="List direct children of a workspace directory with file metadata.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_MAX_RESULTS},
            },
        },
        read_only=True,
        function=list_files,
        category="search",
    ),
    "glob_files": ToolSpec(
        name="glob_files",
        description="Find workspace files by glob pattern without reading file contents.",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_MAX_RESULTS},
            },
            "required": ["pattern"],
        },
        read_only=True,
        function=glob_files,
        category="search",
    ),
    "search_files": ToolSpec(
        name="search_files",
        description="Search file contents by pattern under a workspace path. Uses ripgrep when available.",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "include": {"type": "string"},
                "exclude": {"type": "string"},
                "case_sensitive": {"type": "boolean"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_MAX_RESULTS},
                "max_bytes": {"type": "integer", "minimum": 1, "maximum": MAX_MAX_BYTES},
            },
            "required": ["pattern"],
        },
        read_only=True,
        function=search_files,
        category="search",
    ),
}
