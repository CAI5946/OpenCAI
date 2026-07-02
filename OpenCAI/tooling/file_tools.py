"""File tools."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from OpenCAI.tooling.contracts import ToolResult, ToolSpec, tool_result
from OpenCAI.tooling.common import coerce_positive_int
from OpenCAI.tooling.path_utils import display_path, resolve_child_path


DEFAULT_READ_MAX_CHARS = 200000
MAX_READ_MAX_CHARS = 1000000


def _required_path(arguments: dict[str, Any], name: str = "path") -> tuple[str | None, ToolResult | None]:
    path = arguments.get(name)
    if not isinstance(path, str) or not path:
        return None, tool_result("", False, error=f"Missing required string argument: {name}")
    return path, None


def _workspace_path(cwd: Path, path: str, tool_name: str) -> tuple[Path | None, ToolResult | None]:
    target = resolve_child_path(cwd, path)
    if target is None:
        return None, tool_result(tool_name, False, error=f"Path escapes workspace: {path}")
    return target, None


def read_file(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    path = arguments.get("path")
    if not isinstance(path, str) or not path:
        return tool_result("read_file", False, error="Missing required string argument: path")

    target, path_error = _workspace_path(cwd, path, "read_file")
    if path_error is not None or target is None:
        return path_error or tool_result("read_file", False, error="Invalid path")
    max_chars = coerce_positive_int(
        arguments.get("max_chars"),
        default=DEFAULT_READ_MAX_CHARS,
        minimum=1,
        maximum=MAX_READ_MAX_CHARS,
    )
    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return tool_result("read_file", False, error=f"Read failed: {exc}")

    original_chars = len(content)
    truncated = original_chars > max_chars
    if truncated:
        content = content[:max_chars]

    return tool_result(
        "read_file",
        True,
        {
            "path": display_path(target, cwd),
            "content": content,
            "truncated": truncated,
            "chars": original_chars,
        },
    )


def write_file(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    path = arguments.get("path")
    content = arguments.get("content")
    if not isinstance(path, str) or not path:
        return tool_result("write_file", False, error="Missing required string argument: path")
    if not isinstance(content, str):
        return tool_result("write_file", False, error="Missing required string argument: content")

    target, path_error = _workspace_path(cwd, path, "write_file")
    if path_error is not None or target is None:
        return path_error or tool_result("write_file", False, error="Invalid path")

    overwrite = bool(arguments.get("overwrite", False))
    create_dirs = bool(arguments.get("create_dirs", False))
    exists = target.exists()
    if exists and not overwrite:
        return tool_result("write_file", False, error=f"File already exists: {path}")
    if not target.parent.exists():
        if not create_dirs:
            return tool_result("write_file", False, error=f"Parent directory does not exist: {display_path(target.parent, cwd)}")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return tool_result("write_file", False, error=f"Create parent directories failed: {exc}")

    try:
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        return tool_result("write_file", False, error=f"Write failed: {exc}")

    return tool_result(
        "write_file",
        True,
        {
            "path": display_path(target, cwd),
            "bytes_written": len(content.encode("utf-8")),
            "created": not exists,
            "overwritten": exists,
        },
    )


def delete_file(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    path = arguments.get("path")
    if not isinstance(path, str) or not path:
        return tool_result("delete_file", False, error="Missing required string argument: path")
    target, path_error = _workspace_path(cwd, path, "delete_file")
    if path_error is not None or target is None:
        return path_error or tool_result("delete_file", False, error="Invalid path")
    if not target.exists():
        return tool_result("delete_file", False, error=f"File does not exist: {path}")
    if not target.is_file():
        return tool_result("delete_file", False, error=f"Path is not a file: {path}")
    try:
        target.unlink()
    except OSError as exc:
        return tool_result("delete_file", False, error=f"Delete failed: {exc}")
    return tool_result("delete_file", True, {"path": display_path(target, cwd), "deleted": True})


def copy_file(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    return _copy_or_move_file("copy_file", arguments, cwd, move=False)


def move_file(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    return _copy_or_move_file("move_file", arguments, cwd, move=True)


def _copy_or_move_file(
    tool_name: str,
    arguments: dict[str, Any],
    cwd: Path,
    *,
    move: bool,
) -> ToolResult:
    source = arguments.get("source")
    destination = arguments.get("destination")
    if not isinstance(source, str) or not source:
        return tool_result(tool_name, False, error="Missing required string argument: source")
    if not isinstance(destination, str) or not destination:
        return tool_result(tool_name, False, error="Missing required string argument: destination")

    src, src_error = _workspace_path(cwd, source, tool_name)
    dst, dst_error = _workspace_path(cwd, destination, tool_name)
    if src_error is not None or src is None:
        return src_error or tool_result(tool_name, False, error="Invalid source")
    if dst_error is not None or dst is None:
        return dst_error or tool_result(tool_name, False, error="Invalid destination")
    if not src.is_file():
        return tool_result(tool_name, False, error=f"Source is not a file: {source}")
    overwrite = bool(arguments.get("overwrite", False))
    create_dirs = bool(arguments.get("create_dirs", True))
    if dst.exists() and not overwrite:
        return tool_result(tool_name, False, error=f"Destination already exists: {destination}")
    if not dst.parent.exists():
        if not create_dirs:
            return tool_result(tool_name, False, error=f"Parent directory does not exist: {display_path(dst.parent, cwd)}")
        dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        if move:
            shutil.move(str(src), str(dst))
        else:
            shutil.copy2(src, dst)
    except OSError as exc:
        return tool_result(tool_name, False, error=f"{tool_name} failed: {exc}")

    return tool_result(
        tool_name,
        True,
        {
            "source": display_path(src, cwd),
            "destination": display_path(dst, cwd),
            "moved": move,
            "copied": not move,
        },
    )


FILE_TOOLS: dict[str, ToolSpec] = {
    "read_file": ToolSpec(
        name="read_file",
        description="Read a UTF-8 text file from the current working directory.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_chars": {"type": "integer", "minimum": 1, "maximum": MAX_READ_MAX_CHARS},
            },
            "required": ["path"],
        },
        read_only=True,
        function=read_file,
        category="file",
    ),
    "write_file": ToolSpec(
        name="write_file",
        description="Create or overwrite a UTF-8 text file inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "overwrite": {"type": "boolean"},
                "create_dirs": {"type": "boolean"},
            },
            "required": ["path", "content"],
        },
        read_only=False,
        function=write_file,
        category="file",
    ),
    "delete_file": ToolSpec(
        name="delete_file",
        description="Delete a file inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        read_only=False,
        function=delete_file,
        category="file",
    ),
    "copy_file": ToolSpec(
        name="copy_file",
        description="Copy a file inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
                "overwrite": {"type": "boolean"},
                "create_dirs": {"type": "boolean"},
            },
            "required": ["source", "destination"],
        },
        read_only=False,
        function=copy_file,
        category="file",
    ),
    "move_file": ToolSpec(
        name="move_file",
        description="Move or rename a file inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
                "overwrite": {"type": "boolean"},
                "create_dirs": {"type": "boolean"},
            },
            "required": ["source", "destination"],
        },
        read_only=False,
        function=move_file,
        category="file",
    ),
}
