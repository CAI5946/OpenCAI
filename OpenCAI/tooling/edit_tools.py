"""Edit tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from OpenCAI.tooling.contracts import ToolResult, ToolSpec, tool_result
from OpenCAI.tooling.path_utils import display_path, resolve_child_path


def _workspace_path(cwd: Path, path: str, tool_name: str) -> tuple[Path | None, ToolResult | None]:
    target = resolve_child_path(cwd, path)
    if target is None:
        return None, tool_result(tool_name, False, error=f"Path escapes workspace: {path}")
    return target, None


def edit_file(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    return _replace_in_file(
        tool_name="edit_file",
        path=arguments.get("path"),
        old=arguments.get("old"),
        new=arguments.get("new"),
        cwd=cwd,
        replace_all=bool(arguments.get("replace_all", False)),
    )


def apply_patch(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    patch = arguments.get("patch")
    if isinstance(patch, str) and patch:
        return _apply_freeform_patch(patch, cwd)

    path = arguments.get("path")
    old = arguments.get("old")
    new = arguments.get("new")
    return _replace_in_file(
        tool_name="apply_patch",
        path=path,
        old=old,
        new=new,
        cwd=cwd,
        replace_all=False,
    )


def _replace_in_file(
    *,
    tool_name: str,
    path: object,
    old: object,
    new: object,
    cwd: Path,
    replace_all: bool,
) -> ToolResult:
    if not isinstance(path, str) or not path:
        return tool_result(tool_name, False, error="Missing required string argument: path")
    if not isinstance(old, str) or not old:
        return tool_result(tool_name, False, error="Missing required string argument: old")
    if not isinstance(new, str):
        return tool_result(tool_name, False, error="Missing required string argument: new")

    target, path_error = _workspace_path(cwd, path, tool_name)
    if path_error is not None or target is None:
        return path_error or tool_result(tool_name, False, error="Invalid path")
    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return tool_result(tool_name, False, error=f"Read failed: {exc}")

    if old not in content:
        return tool_result(tool_name, False, error="Patch failed: old text not found")

    replacements = content.count(old) if replace_all else 1
    updated = content.replace(old, new) if replace_all else content.replace(old, new, 1)
    try:
        target.write_text(updated, encoding="utf-8")
    except OSError as exc:
        return tool_result(tool_name, False, error=f"Write failed: {exc}")

    return tool_result(
        tool_name,
        True,
        {
            "path": display_path(target, cwd),
            "summary": "Replaced text",
            "replacements": replacements,
        },
    )


def _apply_freeform_patch(patch: str, cwd: Path) -> ToolResult:
    lines = patch.splitlines()
    if not lines or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        return tool_result("apply_patch", False, error="Patch must start with *** Begin Patch and end with *** End Patch")

    index = 1
    operations = 0
    changed_paths: list[str] = []
    while index < len(lines) - 1:
        header = lines[index]
        if header.startswith("*** Add File: "):
            path = header.removeprefix("*** Add File: ").strip()
            index, result = _apply_add_file(lines, index + 1, path, cwd)
        elif header.startswith("*** Update File: "):
            path = header.removeprefix("*** Update File: ").strip()
            index, result = _apply_update_file(lines, index + 1, path, cwd)
        elif header.startswith("*** Delete File: "):
            path = header.removeprefix("*** Delete File: ").strip()
            index, result = _apply_delete_file(index + 1, path, cwd)
        else:
            return tool_result("apply_patch", False, error=f"Unsupported patch header: {header}")

        if not result["ok"]:
            return result
        operations += 1
        changed_paths.append(str(result["result"].get("path", path)))

    return tool_result(
        "apply_patch",
        True,
        {
            "operations": operations,
            "paths": changed_paths,
            "summary": f"Applied {operations} patch operations",
        },
    )


def _is_operation_header(line: str) -> bool:
    return (
        line.startswith("*** Add File: ")
        or line.startswith("*** Update File: ")
        or line.startswith("*** Delete File: ")
        or line == "*** End Patch"
    )


def _apply_add_file(lines: list[str], index: int, path: str, cwd: Path) -> tuple[int, ToolResult]:
    target, path_error = _workspace_path(cwd, path, "apply_patch")
    if path_error is not None or target is None:
        return index, path_error or tool_result("apply_patch", False, error="Invalid path")
    if target.exists():
        return index, tool_result("apply_patch", False, error=f"File already exists: {path}")
    content_lines: list[str] = []
    while index < len(lines) and not _is_operation_header(lines[index]):
        line = lines[index]
        if not line.startswith("+"):
            return index, tool_result("apply_patch", False, error=f"Add file lines must start with +: {path}")
        content_lines.append(line[1:])
        index += 1
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(content_lines) + ("\n" if content_lines else ""), encoding="utf-8")
    except OSError as exc:
        return index, tool_result("apply_patch", False, error=f"Add file failed: {exc}")
    return index, tool_result("apply_patch", True, {"path": display_path(target, cwd), "action": "add"})


def _apply_update_file(lines: list[str], index: int, path: str, cwd: Path) -> tuple[int, ToolResult]:
    target, path_error = _workspace_path(cwd, path, "apply_patch")
    if path_error is not None or target is None:
        return index, path_error or tool_result("apply_patch", False, error="Invalid path")
    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return index, tool_result("apply_patch", False, error=f"Read failed: {exc}")

    old_lines: list[str] = []
    new_lines: list[str] = []
    saw_hunk = False
    while index < len(lines) and not _is_operation_header(lines[index]):
        line = lines[index]
        if line.startswith("@@"):
            saw_hunk = True
        elif line.startswith("-"):
            old_lines.append(line[1:])
        elif line.startswith("+"):
            new_lines.append(line[1:])
        elif line.startswith(" "):
            old_lines.append(line[1:])
            new_lines.append(line[1:])
        elif line == "":
            old_lines.append("")
            new_lines.append("")
        else:
            return index, tool_result("apply_patch", False, error=f"Unsupported update line: {line}")
        index += 1

    if not saw_hunk:
        return index, tool_result("apply_patch", False, error=f"Update patch missing hunk marker: {path}")
    old = "\n".join(old_lines)
    new = "\n".join(new_lines)
    if old and old not in content:
        old_with_newline = old + "\n"
        if old_with_newline not in content:
            return index, tool_result("apply_patch", False, error=f"Patch hunk not found: {path}")
        old = old_with_newline
        new = new + "\n"
    updated = content.replace(old, new, 1)
    try:
        target.write_text(updated, encoding="utf-8")
    except OSError as exc:
        return index, tool_result("apply_patch", False, error=f"Write failed: {exc}")
    return index, tool_result("apply_patch", True, {"path": display_path(target, cwd), "action": "update"})


def _apply_delete_file(index: int, path: str, cwd: Path) -> tuple[int, ToolResult]:
    target, path_error = _workspace_path(cwd, path, "apply_patch")
    if path_error is not None or target is None:
        return index, path_error or tool_result("apply_patch", False, error="Invalid path")
    if not target.exists():
        return index, tool_result("apply_patch", False, error=f"File does not exist: {path}")
    if not target.is_file():
        return index, tool_result("apply_patch", False, error=f"Path is not a file: {path}")
    try:
        target.unlink()
    except OSError as exc:
        return index, tool_result("apply_patch", False, error=f"Delete failed: {exc}")
    return index, tool_result("apply_patch", True, {"path": display_path(target, cwd), "action": "delete"})


EDIT_TOOLS: dict[str, ToolSpec] = {
    "edit_file": ToolSpec(
        name="edit_file",
        description="Replace text in one UTF-8 workspace file with clear replacement semantics.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
                "replace_all": {"type": "boolean"},
            },
            "required": ["path", "old", "new"],
        },
        read_only=False,
        function=edit_file,
        category="edit",
    ),
    "apply_patch": ToolSpec(
        name="apply_patch",
        description="Apply a structured multi-file patch, or the legacy path/old/new replacement schema.",
        input_schema={
            "type": "object",
            "properties": {
                "patch": {"type": "string"},
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
        },
        read_only=False,
        function=apply_patch,
        category="edit",
    ),
}
