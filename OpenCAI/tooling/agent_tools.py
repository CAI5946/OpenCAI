"""Subagent boundary tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from OpenCAI.tooling.contracts import ToolExposure, ToolResult, ToolSpec, tool_result


def _agent_runtime_required(tool_name: str) -> Any:
    def _run(arguments: dict[str, Any], cwd: Path) -> ToolResult:
        return tool_result(tool_name, False, error=f"{tool_name} requires the future Multi-agent runtime")

    return _run


AGENT_TOOLS: dict[str, ToolSpec] = {
    name: ToolSpec(
        name=name,
        description=description,
        input_schema=schema,
        read_only=read_only,
        function=_agent_runtime_required(name),
        category="agent",
        exposure=ToolExposure.DEFERRED,
    )
    for name, description, schema, read_only in [
        (
            "spawn_agent",
            "Spawn a subagent with a scoped task and tool policy.",
            {"type": "object", "properties": {"task": {"type": "string"}, "role": {"type": "string"}}, "required": ["task"]},
            False,
        ),
        (
            "send_agent_message",
            "Send a message to a running subagent.",
            {"type": "object", "properties": {"agent_id": {"type": "string"}, "message": {"type": "string"}}, "required": ["agent_id", "message"]},
            False,
        ),
        (
            "wait_agent",
            "Wait for a subagent result.",
            {"type": "object", "properties": {"agent_id": {"type": "string"}}},
            True,
        ),
        (
            "list_agents",
            "List running subagents.",
            {"type": "object", "properties": {}},
            True,
        ),
        (
            "stop_agent",
            "Stop a running subagent.",
            {"type": "object", "properties": {"agent_id": {"type": "string"}}, "required": ["agent_id"]},
            False,
        ),
        (
            "merge_agent_result",
            "Merge a completed subagent result into the parent workflow.",
            {"type": "object", "properties": {"agent_id": {"type": "string"}}, "required": ["agent_id"]},
            False,
        ),
    ]
}
