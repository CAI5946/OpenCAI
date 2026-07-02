"""Minimal tool model for the learning-first Agent prototype."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, TypedDict


class ToolCall(TypedDict):
    tool_name: str
    arguments: dict[str, Any]


class ToolResult(TypedDict):
    tool_name: str
    ok: bool
    result: dict[str, Any]
    error: str | None


ToolFunction = Callable[[dict[str, Any], Path], ToolResult]
SKIPPED_SEARCH_DIRS = {".git", ".venv", "__pycache__", "node_modules", "venv"}
DEFAULT_SKILL_ROOT = "skills"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    read_only: bool
    function: ToolFunction


def _tool_result(
    tool_name: str,
    ok: bool,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> ToolResult:
    return {
        "tool_name": tool_name,
        "ok": ok,
        "result": result or {},
        "error": error,
    }


def read_file(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    path = arguments.get("path")
    if not isinstance(path, str) or not path:
        return _tool_result("read_file", False, error="Missing required string argument: path")

    target = cwd / path
    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _tool_result("read_file", False, error=f"Read failed: {exc}")

    return _tool_result(
        "read_file",
        True,
        {
            "path": str(target),
            "content": content,
        },
    )


def _iter_text_files(target: Path) -> Iterable[Path]:
    if target.is_file():
        yield target
        return

    for path in target.rglob("*"):
        if any(part in SKIPPED_SEARCH_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def _display_path(path: Path, cwd: Path) -> str:
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return str(path)


def _resolve_child_path(cwd: Path, path: str) -> Path | None:
    resolved_cwd = cwd.resolve()
    resolved_target = (resolved_cwd / path).resolve()
    try:
        resolved_target.relative_to(resolved_cwd)
    except ValueError:
        return None
    return resolved_target


def _skill_root(arguments: dict[str, Any], cwd: Path) -> Path | None:
    root = arguments.get("root", DEFAULT_SKILL_ROOT)
    if not isinstance(root, str) or not root:
        return None
    return _resolve_child_path(cwd, root)


def _is_valid_skill_name(name: str) -> bool:
    path = Path(name)
    return bool(name) and not path.is_absolute() and len(path.parts) == 1 and name not in {".", ".."}


def _extract_frontmatter_description(content: str) -> str:
    if not content.startswith("---\n"):
        return ""

    end = content.find("\n---", 4)
    if end == -1:
        return ""

    frontmatter = content[4:end].splitlines()
    for line in frontmatter:
        key, separator, value = line.partition(":")
        if separator and key.strip() == "description":
            return value.strip().strip('"')
    return ""


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


def search_files(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    pattern = arguments.get("pattern")
    path = arguments.get("path", ".")
    if not isinstance(pattern, str) or not pattern:
        return _tool_result("search_files", False, error="Missing required string argument: pattern")
    # Omitting path is valid; reject only an explicit empty or non-string path.
    if not isinstance(path, str) or not path:
        return _tool_result("search_files", False, error="Missing string argument: path")

    target = cwd / path
    if not target.exists():
        return _tool_result("search_files", False, error=f"Search path does not exist: {path}")

    max_matches = 50
    matches: list[dict[str, Any]] = []
    skipped: list[str] = []

    for file_path in _iter_text_files(target):
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            skipped.append(_display_path(file_path, cwd))
            continue

        for line_number, line in enumerate(lines, start=1):
            if pattern in line:
                matches.append(
                    {
                        "path": _display_path(file_path, cwd),
                        "line": line_number,
                        "text": line.strip(),
                    }
                )
                if len(matches) >= max_matches:
                    return _tool_result(
                        "search_files",
                        True,
                        {
                            "path": str(target),
                            "content": _format_search_content(matches, True, skipped),
                            "pattern": pattern,
                            "matches": matches,
                            "truncated": True,
                            "skipped": skipped,
                        },
                    )

    return _tool_result(
        "search_files",
        True,
        {
            "path": str(target),
            "content": _format_search_content(matches, False, skipped),
            "pattern": pattern,
            "matches": matches,
            "truncated": False,
            "skipped": skipped,
        },
    )


def list_skills(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    root = _skill_root(arguments, cwd)
    if root is None:
        return _tool_result("list_skills", False, error="Invalid skill root")
    if not root.exists():
        return _tool_result(
            "list_skills",
            True,
            {
                "root": _display_path(root, cwd),
                "skills": [],
            },
        )
    if not root.is_dir():
        return _tool_result("list_skills", False, error="Skill root is not a directory")

    skills: list[dict[str, str]] = []
    for entry in sorted(root.iterdir(), key=lambda path: path.name.lower()):
        skill_file = entry / "SKILL.md"
        if not entry.is_dir() or not skill_file.is_file():
            continue

        description = ""
        try:
            description = _extract_frontmatter_description(
                skill_file.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError):
            pass

        skills.append(
            {
                "name": entry.name,
                "path": _display_path(entry, cwd),
                "description": description,
            }
        )

    return _tool_result(
        "list_skills",
        True,
        {
            "root": _display_path(root, cwd),
            "skills": skills,
        },
    )


def read_skill(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    name = arguments.get("name")
    if not isinstance(name, str) or not _is_valid_skill_name(name):
        return _tool_result("read_skill", False, error="Invalid skill name")

    root = _skill_root(arguments, cwd)
    if root is None:
        return _tool_result("read_skill", False, error="Invalid skill root")

    skill_file = root / name / "SKILL.md"
    try:
        content = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _tool_result("read_skill", False, error=f"Read failed: {exc}")

    return _tool_result(
        "read_skill",
        True,
        {
            "name": name,
            "path": _display_path(skill_file, cwd),
            "content": content,
        },
    )


def run_command(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    command = arguments.get("command")
    if not isinstance(command, str) or not command:
        return _tool_result("run_command", False, error="Missing required string argument: command")

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _tool_result("run_command", False, error=f"Command failed: {exc}")

    return _tool_result(
        "run_command",
        True,
        {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
    )


def apply_patch(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    path = arguments.get("path")
    old = arguments.get("old")
    new = arguments.get("new")
    if not isinstance(path, str) or not path:
        return _tool_result("apply_patch", False, error="Missing required string argument: path")
    if not isinstance(old, str) or not old:
        return _tool_result("apply_patch", False, error="Missing required string argument: old")
    if not isinstance(new, str):
        return _tool_result("apply_patch", False, error="Missing required string argument: new")

    target = cwd / path
    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _tool_result("apply_patch", False, error=f"Read failed: {exc}")

    if old not in content:
        return _tool_result("apply_patch", False, error="Patch failed: old text not found")

    updated = content.replace(old, new, 1)
    try:
        target.write_text(updated, encoding="utf-8")
    except OSError as exc:
        return _tool_result("apply_patch", False, error=f"Write failed: {exc}")

    return _tool_result(
        "apply_patch",
        True,
        {
            "path": str(target),
            "summary": "Replaced text",
        },
    )


def _not_implemented_tool(tool_name: str) -> ToolFunction:
    def _run(arguments: dict[str, Any], cwd: Path) -> ToolResult:
        return _tool_result(
            tool_name,
            False,
            error=f"{tool_name} is not implemented in Phase 3 yet",
        )

    return _run


TOOLS: dict[str, ToolSpec] = {
    "read_file": ToolSpec(
        name="read_file",
        description="Read a UTF-8 text file from the current working directory.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
        read_only=True,
        function=read_file,
    ),
    "search_files": ToolSpec(
        name="search_files",
        description="Search files by pattern under a path.",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["pattern"],
        },
        read_only=True,
        function=search_files,
    ),
    "list_skills": ToolSpec(
        name="list_skills",
        description="List local OpenCAI skills under a workspace skill root.",
        input_schema={
            "type": "object",
            "properties": {
                "root": {"type": "string"},
            },
        },
        read_only=True,
        function=list_skills,
    ),
    "read_skill": ToolSpec(
        name="read_skill",
        description="Read the SKILL.md entrypoint for a local OpenCAI skill.",
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "root": {"type": "string"},
            },
            "required": ["name"],
        },
        read_only=True,
        function=read_skill,
    ),
    "apply_patch": ToolSpec(
        name="apply_patch",
        description="Replace one matching text block in a UTF-8 file.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
        },
        read_only=False,
        function=apply_patch,
    ),
    "run_command": ToolSpec(
        name="run_command",
        description="Run a shell command and return exit code, stdout, and stderr.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
            },
            "required": ["command"],
        },
        read_only=False,
        function=run_command,
    ),
}


def run_tool(tool_name: str, arguments: dict[str, Any], cwd: Path | None = None) -> ToolResult:
    spec = TOOLS.get(tool_name)
    if spec is None:
        return _tool_result(tool_name, False, error=f"Unknown tool: {tool_name}")

    return spec.function(arguments, cwd or Path.cwd())
