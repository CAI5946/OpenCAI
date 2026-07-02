"""Planning and task tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from OpenCAI.tooling.contracts import ToolResult, ToolSpec, tool_result


VALID_PLAN_STATUSES = {"pending", "in_progress", "completed"}
VALID_TASK_STATUSES = {"pending", "in_progress", "blocked", "completed", "cancelled"}

PLAN_STATE: list[dict[str, str]] = []
TASK_STATE: dict[str, dict[str, Any]] = {}


def update_plan(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    raw_plan = arguments.get("plan")
    if not isinstance(raw_plan, list) or not raw_plan:
        return tool_result("update_plan", False, error="Missing required list argument: plan")

    plan: list[dict[str, str]] = []
    in_progress_count = 0
    for item in raw_plan:
        if not isinstance(item, dict):
            return tool_result("update_plan", False, error="Each plan item must be an object")
        step = item.get("step")
        status = item.get("status", "pending")
        if not isinstance(step, str) or not step.strip():
            return tool_result("update_plan", False, error="Each plan item requires a non-empty step")
        if status not in VALID_PLAN_STATUSES:
            return tool_result("update_plan", False, error=f"Invalid plan status: {status}")
        if status == "in_progress":
            in_progress_count += 1
        plan.append({"step": step.strip(), "status": str(status)})

    if in_progress_count > 1:
        return tool_result("update_plan", False, error="At most one plan item can be in_progress")

    PLAN_STATE.clear()
    PLAN_STATE.extend(plan)
    summary = _plan_summary(plan)
    return tool_result("update_plan", True, {"plan": list(PLAN_STATE), "summary": summary})


def create_task(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    title = arguments.get("title")
    if not isinstance(title, str) or not title.strip():
        return tool_result("create_task", False, error="Missing required string argument: title")
    description = arguments.get("description", "")
    if not isinstance(description, str):
        return tool_result("create_task", False, error="description must be a string")
    task_id = uuid4().hex[:12]
    task = {
        "id": task_id,
        "title": title.strip(),
        "description": description,
        "status": "pending",
    }
    TASK_STATE[task_id] = task
    return tool_result("create_task", True, {"task": dict(task)})


def update_task(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    task_id = arguments.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        return tool_result("update_task", False, error="Missing required string argument: task_id")
    task = TASK_STATE.get(task_id)
    if task is None:
        return tool_result("update_task", False, error=f"Unknown task: {task_id}")

    status = arguments.get("status")
    if status is not None:
        if status not in VALID_TASK_STATUSES:
            return tool_result("update_task", False, error=f"Invalid task status: {status}")
        task["status"] = status
    title = arguments.get("title")
    if title is not None:
        if not isinstance(title, str) or not title.strip():
            return tool_result("update_task", False, error="title must be a non-empty string")
        task["title"] = title.strip()
    description = arguments.get("description")
    if description is not None:
        if not isinstance(description, str):
            return tool_result("update_task", False, error="description must be a string")
        task["description"] = description

    return tool_result("update_task", True, {"task": dict(task)})


def list_tasks(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    status = arguments.get("status")
    if status is not None and status not in VALID_TASK_STATUSES:
        return tool_result("list_tasks", False, error=f"Invalid task status: {status}")
    tasks = [dict(task) for task in TASK_STATE.values() if status is None or task["status"] == status]
    return tool_result("list_tasks", True, {"tasks": tasks})


def complete_task(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    task_id = arguments.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        return tool_result("complete_task", False, error="Missing required string argument: task_id")
    task = TASK_STATE.get(task_id)
    if task is None:
        return tool_result("complete_task", False, error=f"Unknown task: {task_id}")
    task["status"] = "completed"
    return tool_result("complete_task", True, {"task": dict(task)})


def _plan_summary(plan: list[dict[str, str]]) -> str:
    counts = {status: 0 for status in ("completed", "in_progress", "pending")}
    for item in plan:
        counts[item["status"]] += 1
    return (
        f"{counts['completed']} completed, "
        f"{counts['in_progress']} in_progress, "
        f"{counts['pending']} pending"
    )


PLANNING_TOOLS: dict[str, ToolSpec] = {
    "update_plan": ToolSpec(
        name="update_plan",
        description="Update the current multi-step plan. At most one item may be in_progress.",
        input_schema={
            "type": "object",
            "properties": {
                "plan": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "string"},
                            "status": {"type": "string", "enum": sorted(VALID_PLAN_STATUSES)},
                        },
                        "required": ["step", "status"],
                    },
                }
            },
            "required": ["plan"],
        },
        read_only=False,
        function=update_plan,
        category="planning",
    ),
    "create_task": ToolSpec(
        name="create_task",
        description="Create a tracked task for multi-step agent work.",
        input_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["title"],
        },
        read_only=False,
        function=create_task,
        category="planning",
    ),
    "update_task": ToolSpec(
        name="update_task",
        description="Update title, description, or status for a tracked task.",
        input_schema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "status": {"type": "string", "enum": sorted(VALID_TASK_STATUSES)},
            },
            "required": ["task_id"],
        },
        read_only=False,
        function=update_task,
        category="planning",
    ),
    "list_tasks": ToolSpec(
        name="list_tasks",
        description="List tracked tasks, optionally filtered by status.",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": sorted(VALID_TASK_STATUSES)},
            },
        },
        read_only=True,
        function=list_tasks,
        category="planning",
    ),
    "complete_task": ToolSpec(
        name="complete_task",
        description="Mark a tracked task completed.",
        input_schema={
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
        read_only=False,
        function=complete_task,
        category="planning",
    ),
}
