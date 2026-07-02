"""IDE / code intelligence boundary tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from OpenCAI.tooling.contracts import ToolExposure, ToolResult, ToolSpec, tool_result


def _lsp_runtime_required(tool_name: str) -> Any:
    def _run(arguments: dict[str, Any], cwd: Path) -> ToolResult:
        return tool_result(tool_name, False, error=f"{tool_name} requires an IDE/LSP backend")

    return _run


CODE_INTELLIGENCE_TOOLS: dict[str, ToolSpec] = {
    name: ToolSpec(
        name=name,
        description=description,
        input_schema=schema,
        read_only=read_only,
        function=_lsp_runtime_required(name),
        category="code_intelligence",
        exposure=ToolExposure.DEFERRED,
    )
    for name, description, schema, read_only in [
        (
            "get_diagnostics",
            "Return IDE/LSP diagnostics for a file or workspace.",
            {"type": "object", "properties": {"path": {"type": "string"}}},
            True,
        ),
        (
            "go_to_definition",
            "Resolve a symbol definition through an IDE/LSP backend.",
            {"type": "object", "properties": {"path": {"type": "string"}, "line": {"type": "integer"}, "column": {"type": "integer"}}, "required": ["path", "line", "column"]},
            True,
        ),
        (
            "find_references",
            "Find references through an IDE/LSP backend.",
            {"type": "object", "properties": {"path": {"type": "string"}, "line": {"type": "integer"}, "column": {"type": "integer"}}, "required": ["path", "line", "column"]},
            True,
        ),
        (
            "rename_symbol",
            "Rename a symbol through an IDE/LSP backend.",
            {"type": "object", "properties": {"path": {"type": "string"}, "line": {"type": "integer"}, "column": {"type": "integer"}, "new_name": {"type": "string"}}, "required": ["path", "line", "column", "new_name"]},
            False,
        ),
        (
            "format_file",
            "Format a file through an IDE/LSP backend.",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            False,
        ),
    ]
}
