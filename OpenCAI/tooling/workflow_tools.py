"""Workflow boundary tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from OpenCAI.tooling.contracts import ToolExposure, ToolResult, ToolSpec, tool_result


def workflow_plan(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    from OpenCAI.workflow import build_inspect_handoff_workflow, render_workflow_plan

    spec = build_inspect_handoff_workflow()
    return tool_result(
        "workflow_plan",
        True,
        {
            "name": spec.name,
            "final_phase_id": spec.final_phase_id,
            "phases": [
                {
                    "id": phase.id,
                    "role": phase.role,
                    "depends_on": list(phase.depends_on),
                    "instruction": phase.prompt_template,
                }
                for phase in spec.phases
            ],
            "content": render_workflow_plan(spec),
        },
    )


def _workflow_runtime_required(tool_name: str) -> Any:
    def _run(arguments: dict[str, Any], cwd: Path) -> ToolResult:
        return tool_result(tool_name, False, error=f"{tool_name} requires RuntimeSession workflow control integration")

    return _run


WORKFLOW_TOOLS: dict[str, ToolSpec] = {
    "workflow_plan": ToolSpec(
        name="workflow_plan",
        description="Render the current built-in workflow plan without executing it.",
        input_schema={"type": "object", "properties": {"task": {"type": "string"}}},
        read_only=True,
        function=workflow_plan,
        category="workflow",
    ),
    "workflow_execute": ToolSpec(
        name="workflow_execute",
        description="Execute a workflow through the runtime workflow controller.",
        input_schema={"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]},
        read_only=False,
        function=_workflow_runtime_required("workflow_execute"),
        category="workflow",
        exposure=ToolExposure.DEFERRED,
    ),
    "workflow_status": ToolSpec(
        name="workflow_status",
        description="Read workflow execution status from the runtime workflow controller.",
        input_schema={"type": "object", "properties": {"workflow_id": {"type": "string"}}},
        read_only=True,
        function=_workflow_runtime_required("workflow_status"),
        category="workflow",
        exposure=ToolExposure.DEFERRED,
    ),
    "workflow_pause": ToolSpec(
        name="workflow_pause",
        description="Pause a running workflow.",
        input_schema={"type": "object", "properties": {"workflow_id": {"type": "string"}}, "required": ["workflow_id"]},
        read_only=False,
        function=_workflow_runtime_required("workflow_pause"),
        category="workflow",
        exposure=ToolExposure.DEFERRED,
    ),
    "workflow_resume": ToolSpec(
        name="workflow_resume",
        description="Resume a paused workflow.",
        input_schema={"type": "object", "properties": {"workflow_id": {"type": "string"}}, "required": ["workflow_id"]},
        read_only=False,
        function=_workflow_runtime_required("workflow_resume"),
        category="workflow",
        exposure=ToolExposure.DEFERRED,
    ),
    "workflow_cancel": ToolSpec(
        name="workflow_cancel",
        description="Cancel a running workflow.",
        input_schema={"type": "object", "properties": {"workflow_id": {"type": "string"}}, "required": ["workflow_id"]},
        read_only=False,
        function=_workflow_runtime_required("workflow_cancel"),
        category="workflow",
        exposure=ToolExposure.DEFERRED,
    ),
    "workflow_replay": ToolSpec(
        name="workflow_replay",
        description="Replay a saved workflow run.",
        input_schema={"type": "object", "properties": {"workflow_id": {"type": "string"}}, "required": ["workflow_id"]},
        read_only=True,
        function=_workflow_runtime_required("workflow_replay"),
        category="workflow",
        exposure=ToolExposure.DEFERRED,
    ),
}
