from __future__ import annotations

from typing import Any

from OpenCAI.output_format import format_output_title
from OpenCAI.llm_adapter import FakeLLMAdapter
from OpenCAI.workflow import (
    SerialWorkflowRunner,
    render_workflow_plan,
    render_workflow_process,
)
from OpenCAI.workflow.clarify import (
    ClarifyPhaseRunner,
    ClarifyRun,
    DeterministicClarifyAgent,
    LLMClarifyAgent,
    render_clarify_run,
)
from OpenCAI.workflow.planner import compile_workflow


def handle_workflow_command(session: Any, task: str) -> None:
    if not task.strip():
        print("No task for workflow. Usage: /workflow TASK")
        return

    clarify_run = run_clarify_for_session(session, task)
    print(render_clarify_run(clarify_run))
    if clarify_run.status == "blocked" or clarify_run.result is None:
        return

    plan = compile_workflow(task, clarify_result=clarify_run.result)
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


def run_clarify_for_session(
    session: Any,
    task: str,
    *,
    session_context_summary: str = "",
) -> ClarifyRun:
    adapter = getattr(session, "adapter", None)
    if adapter is None or isinstance(adapter, FakeLLMAdapter):
        agent = DeterministicClarifyAgent()
    else:
        agent = LLMClarifyAgent(adapter=adapter)
    runner = ClarifyPhaseRunner(agent=agent)
    return runner.run(
        task,
        cwd=session.cwd,
        session_context_summary=session_context_summary,
    )
