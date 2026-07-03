from __future__ import annotations

from typing import Any

from OpenCAI.output_format import format_output_title
from OpenCAI.workflow import (
    SerialWorkflowRunner,
    build_inspect_handoff_workflow,
    render_workflow_plan,
    render_workflow_process,
)


def handle_workflow_command(session: Any, task: str) -> None:
    if not task.strip():
        print("No task for workflow. Usage: /workflow TASK")
        return

    spec = build_inspect_handoff_workflow()
    print(format_output_title(f"Workflow task: {task}"))
    print(render_workflow_plan(spec))

    runner = SerialWorkflowRunner(
        cwd=session.cwd,
        adapter=session.adapter,
        max_steps=session.max_steps,
        policy=session.build_policy(),
    )
    workflow_run = runner.run(spec, task)

    print()
    print(render_workflow_process(workflow_run))
