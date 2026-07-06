from __future__ import annotations

from collections.abc import Callable
from typing import Any

from OpenCAI.demand import DemandBrief
from OpenCAI.events import Event
from OpenCAI.workflow.clarify import ClarifyResult, render_clarify_run
from OpenCAI.workflow.commands import run_clarify_for_session


ExecuteGuidedTask = Callable[[str, DemandBrief], list[Event]]


def demand_brief_from_clarify_result(result: ClarifyResult) -> DemandBrief:
    constraints = result.constraints + tuple(
        f"Out of scope: {item}" for item in result.out_of_scope
    )
    return DemandBrief(
        original_task=result.original_task,
        refined_goal=result.refined_task,
        success_criteria=result.acceptance_criteria,
        scope=result.allowed_changes,
        constraints=constraints,
        assumptions=result.assumptions,
        open_questions=result.open_questions,
    )


def run_guided_task(
    session: Any,
    task: str,
    *,
    execute_task: ExecuteGuidedTask,
) -> list[Event]:
    session_context = getattr(session, "session_context", None)
    session_context_summary = session_context.render() if session_context else ""
    clarify_run = run_clarify_for_session(
        session,
        task,
        session_context_summary=session_context_summary,
    )
    print(render_clarify_run(clarify_run))
    if clarify_run.status == "blocked" or clarify_run.result is None:
        return []

    demand_brief = demand_brief_from_clarify_result(clarify_run.result)
    return execute_task(demand_brief.refined_goal, demand_brief)
