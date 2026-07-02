"""Deferred external tool placeholders.

These tools define OpenCAI's extension boundary without pretending an MCP or
plugin runtime exists yet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from OpenCAI.tooling.contracts import ToolExposure, ToolResult, ToolSpec, tool_result


def _not_configured(tool_name: str) -> Any:
    def _run(arguments: dict[str, Any], cwd: Path) -> ToolResult:
        return tool_result(tool_name, False, error=f"{tool_name} is not configured in this OpenCAI runtime")

    return _run


EXTERNAL_TOOLS: dict[str, ToolSpec] = {
    "tool_search": ToolSpec(
        name="tool_search",
        description="Discover deferred external, MCP, plugin, or dynamic tools available to this runtime.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        read_only=True,
        function=_not_configured("tool_search"),
        category="external",
        exposure=ToolExposure.DEFERRED,
    ),
    "call_external_tool": ToolSpec(
        name="call_external_tool",
        description="Call an external dynamic tool selected through tool_search.",
        input_schema={
            "type": "object",
            "properties": {
                "tool_name": {"type": "string"},
                "arguments": {"type": "object"},
            },
            "required": ["tool_name", "arguments"],
        },
        read_only=False,
        function=_not_configured("call_external_tool"),
        category="external",
        exposure=ToolExposure.DEFERRED,
    ),
    "list_mcp_resources": ToolSpec(
        name="list_mcp_resources",
        description="List MCP resources from configured MCP servers.",
        input_schema={
            "type": "object",
            "properties": {
                "server": {"type": "string"},
            },
        },
        read_only=True,
        function=_not_configured("list_mcp_resources"),
        category="external",
        exposure=ToolExposure.DEFERRED,
    ),
    "read_mcp_resource": ToolSpec(
        name="read_mcp_resource",
        description="Read one MCP resource from a configured MCP server.",
        input_schema={
            "type": "object",
            "properties": {
                "server": {"type": "string"},
                "uri": {"type": "string"},
            },
            "required": ["server", "uri"],
        },
        read_only=True,
        function=_not_configured("read_mcp_resource"),
        category="external",
        exposure=ToolExposure.DEFERRED,
    ),
}
