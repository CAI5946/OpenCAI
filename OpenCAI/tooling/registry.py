"""Tool registry and dispatch."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from OpenCAI.tooling.agent_tools import AGENT_TOOLS
from OpenCAI.tooling.code_intelligence_tools import CODE_INTELLIGENCE_TOOLS
from OpenCAI.tooling.command_tools import (
    COMMAND_TOOLS,
    read_command,
    run_command,
    start_command,
    stop_command,
    write_stdin,
)
from OpenCAI.tooling.contracts import ToolExposure, ToolResult, ToolSpec, tool_result
from OpenCAI.tooling.context_tools import CONTEXT_TOOLS, context_status, read_context_block, search_memory, summarize_context
from OpenCAI.tooling.edit_tools import EDIT_TOOLS, apply_patch, edit_file
from OpenCAI.tooling.external_tools import EXTERNAL_TOOLS
from OpenCAI.tooling.file_tools import (
    FILE_TOOLS,
    copy_file,
    delete_file,
    move_file,
    read_file,
    write_file,
)
from OpenCAI.tooling.planning_tools import (
    PLANNING_TOOLS,
    complete_task,
    create_task,
    list_tasks,
    update_plan,
    update_task,
)
from OpenCAI.tooling.search_tools import SEARCH_TOOLS, glob_files, list_files, search_files
from OpenCAI.tooling.skill_tools import SKILL_TOOLS, invoke_skill, list_skills, read_skill
from OpenCAI.tooling.web_tools import WEB_TOOLS, web_extract, web_fetch, web_search
from OpenCAI.tooling.workflow_tools import WORKFLOW_TOOLS, workflow_plan


class ToolRegistry:
    def __init__(self, tools: Iterable[ToolSpec] = ()) -> None:
        self._tools: dict[str, ToolSpec] = {}
        for spec in tools:
            self.register(spec)

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Duplicate tool registered: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def as_dict(self) -> dict[str, ToolSpec]:
        return dict(self._tools)

    def visible_tools(
        self,
        *,
        exposure: ToolExposure | None = None,
        category: str | None = None,
        read_only: bool | None = None,
    ) -> dict[str, ToolSpec]:
        selected: dict[str, ToolSpec] = {}
        for name, spec in self._tools.items():
            if exposure is not None and spec.exposure != exposure:
                continue
            if category is not None and spec.category != category:
                continue
            if read_only is not None and spec.read_only != read_only:
                continue
            selected[name] = spec
        return selected


DEFAULT_REGISTRY = ToolRegistry(
    [
        *FILE_TOOLS.values(),
        *SEARCH_TOOLS.values(),
        *WEB_TOOLS.values(),
        *SKILL_TOOLS.values(),
        *EDIT_TOOLS.values(),
        *CONTEXT_TOOLS.values(),
        *WORKFLOW_TOOLS.values(),
        *AGENT_TOOLS.values(),
        *CODE_INTELLIGENCE_TOOLS.values(),
        *PLANNING_TOOLS.values(),
        *COMMAND_TOOLS.values(),
        *EXTERNAL_TOOLS.values(),
    ]
)
TOOLS: dict[str, ToolSpec] = DEFAULT_REGISTRY.as_dict()


def run_tool(tool_name: str, arguments: dict[str, Any], cwd: Path | None = None) -> ToolResult:
    spec = TOOLS.get(tool_name)
    if spec is None:
        return tool_result(tool_name, False, error=f"Unknown tool: {tool_name}")

    return spec.function(arguments, cwd or Path.cwd())


__all__ = [
    "TOOLS",
    "DEFAULT_REGISTRY",
    "ToolExposure",
    "ToolRegistry",
    "ToolResult",
    "ToolSpec",
    "apply_patch",
    "complete_task",
    "context_status",
    "copy_file",
    "create_task",
    "delete_file",
    "edit_file",
    "glob_files",
    "invoke_skill",
    "list_files",
    "list_skills",
    "list_tasks",
    "move_file",
    "read_file",
    "read_command",
    "read_context_block",
    "read_skill",
    "run_command",
    "run_tool",
    "search_files",
    "search_memory",
    "start_command",
    "stop_command",
    "summarize_context",
    "update_plan",
    "update_task",
    "write_file",
    "write_stdin",
    "web_extract",
    "web_fetch",
    "web_search",
    "workflow_plan",
]
