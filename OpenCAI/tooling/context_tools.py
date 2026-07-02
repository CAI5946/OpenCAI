"""Context inspection tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from OpenCAI.tooling.contracts import ToolExposure, ToolResult, ToolSpec, tool_result
from OpenCAI.tooling.path_utils import display_path


CONTEXT_BLOCKS = {"readme", "status", "project_agents", "global_agents"}


def context_status(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    from OpenCAI.context import ContextProvider

    snapshot = ContextProvider(max_instruction_chars=2000).collect(
        cwd=cwd,
        adapter_name="unknown",
        permission_profile="unknown",
        max_steps=0,
    )
    return tool_result(
        "context_status",
        True,
        {
            "cwd": str(snapshot.cwd),
            "repo_root": str(snapshot.repo_root),
            "git": {
                "branch": snapshot.git.branch,
                "dirty": snapshot.git.dirty,
                "warning": snapshot.git.warning,
            },
            "project_agents": {
                "path": str(snapshot.project_agents.path),
                "exists": snapshot.project_agents.exists,
            },
            "global_agents": {
                "path": str(snapshot.global_agents.path),
                "exists": snapshot.global_agents.exists,
            },
            "readme_exists": snapshot.readme.exists,
            "status_doc_exists": snapshot.status_doc.exists,
            "skills_count": snapshot.skills.total_count,
        },
    )


def read_context_block(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    from OpenCAI.context import ContextProvider

    block = arguments.get("block")
    if block not in CONTEXT_BLOCKS:
        return tool_result("read_context_block", False, error=f"Unknown context block: {block}")
    snapshot = ContextProvider().collect(
        cwd=cwd,
        adapter_name="unknown",
        permission_profile="unknown",
        max_steps=0,
    )
    mapping = {
        "readme": snapshot.readme.path,
        "status": snapshot.status_doc.path,
        "project_agents": snapshot.project_agents.path,
        "global_agents": snapshot.global_agents.path,
    }
    path = mapping[str(block)]
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return tool_result("read_context_block", False, error=f"Read failed: {exc}")
    return tool_result(
        "read_context_block",
        True,
        {
            "block": block,
            "path": display_path(path, snapshot.repo_root),
            "content": content,
        },
    )


def summarize_context(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    status = context_status(arguments, cwd)
    if not status["ok"]:
        return status
    result = status["result"]
    summary = (
        f"repo_root={result['repo_root']}; "
        f"branch={result['git']['branch']}; "
        f"dirty={result['git']['dirty']}; "
        f"readme={result['readme_exists']}; "
        f"status_doc={result['status_doc_exists']}; "
        f"skills={result['skills_count']}"
    )
    return tool_result("summarize_context", True, {"summary": summary, "context": result})


def search_memory(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    return tool_result(
        "search_memory",
        False,
        error="search_memory is not configured; persistent memory indexing is outside the current OpenCAI runtime",
    )


CONTEXT_TOOLS: dict[str, ToolSpec] = {
    "context_status": ToolSpec(
        name="context_status",
        description="Report the currently available repository/session context blocks.",
        input_schema={"type": "object", "properties": {}},
        read_only=True,
        function=context_status,
        category="context",
    ),
    "read_context_block": ToolSpec(
        name="read_context_block",
        description="Read a named context block such as readme, status, project_agents, or global_agents.",
        input_schema={
            "type": "object",
            "properties": {"block": {"type": "string", "enum": sorted(CONTEXT_BLOCKS)}},
            "required": ["block"],
        },
        read_only=True,
        function=read_context_block,
        category="context",
    ),
    "summarize_context": ToolSpec(
        name="summarize_context",
        description="Return a compact summary of current repository/session context.",
        input_schema={"type": "object", "properties": {}},
        read_only=True,
        function=summarize_context,
        category="context",
    ),
    "search_memory": ToolSpec(
        name="search_memory",
        description="Search persistent OpenCAI memory if a memory backend is configured.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        read_only=True,
        function=search_memory,
        category="context",
        exposure=ToolExposure.DEFERRED,
    ),
}
