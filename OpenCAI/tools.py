"""Minimal tool model for the learning-first Agent prototype."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypedDict


class ToolCall(TypedDict):
    tool_name: str
    arguments: dict[str, Any]


class ToolResult(TypedDict):
    tool_name: str
    ok: bool
    result: dict[str, Any]
    error: str | None


ToolFunction = Callable[[dict[str, Any], Path], ToolResult]


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
        function=_not_implemented_tool("search_files"),
    ),
    "apply_patch": ToolSpec(
        name="apply_patch",
        description="Apply a text patch to files.",
        input_schema={
            "type": "object",
            "properties": {
                "patch": {"type": "string"},
            },
            "required": ["patch"],
        },
        read_only=False,
        function=_not_implemented_tool("apply_patch"),
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
        function=_not_implemented_tool("run_command"),
    ),
}


def run_tool(tool_name: str, arguments: dict[str, Any], cwd: Path | None = None) -> ToolResult:
    spec = TOOLS.get(tool_name)
    if spec is None:
        return _tool_result(tool_name, False, error=f"Unknown tool: {tool_name}")

    return spec.function(arguments, cwd or Path.cwd())
