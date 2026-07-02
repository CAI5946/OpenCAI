"""Compatibility facade for OpenCAI tools.

The concrete implementations live under ``OpenCAI.tooling`` so tool categories
can grow without turning this module into a monolith.
"""

from __future__ import annotations

from OpenCAI.tooling.contracts import ToolCall, ToolFunction, ToolResult, ToolSpec
from OpenCAI.tooling.registry import DEFAULT_REGISTRY, TOOLS, ToolExposure, ToolRegistry, run_tool
from OpenCAI.tooling.command_tools import read_command, run_command, start_command, stop_command, write_stdin
from OpenCAI.tooling.context_tools import context_status, read_context_block, search_memory, summarize_context
from OpenCAI.tooling.edit_tools import apply_patch, edit_file
from OpenCAI.tooling.file_tools import copy_file, delete_file, move_file, read_file, write_file
from OpenCAI.tooling.planning_tools import complete_task, create_task, list_tasks, update_plan, update_task
from OpenCAI.tooling.search_tools import glob_files, list_files, search_files
from OpenCAI.tooling.skill_tools import invoke_skill, list_skills, read_skill
from OpenCAI.tooling.web_tools import web_extract, web_fetch, web_search
from OpenCAI.tooling.workflow_tools import workflow_plan

__all__ = [
    "DEFAULT_REGISTRY",
    "TOOLS",
    "ToolCall",
    "ToolExposure",
    "ToolFunction",
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
