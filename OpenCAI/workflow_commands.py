from __future__ import annotations

from typing import Any

from OpenCAI.output_format import format_output_title
from OpenCAI.workflow_planner import compile_workflow
from OpenCAI.workflow import (
    SerialWorkflowRunner,
    render_workflow_plan,
    render_workflow_process,
)


def handle_workflow_command(session: Any, task: str) -> None:
    if not task.strip():
        print("No task for workflow. Usage: /workflow TASK")
        return

    plan = compile_workflow(task)
    print(format_output_title(f"Workflow task: {task}"))
    print(render_workflow_plan(plan))

    runner = SerialWorkflowRunner(
        cwd=session.cwd,
        adapter=session.adapter,
        max_steps=session.max_steps,
        policy=session.build_policy(),
    )
    workflow_run = runner.run(plan, task)

    print()
    print(render_workflow_process(workflow_run))
