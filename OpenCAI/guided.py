from __future__ import annotations

from collections.abc import Callable
import sys
from typing import Any

from OpenCAI.demand import DemandBrief, render_demand_brief
from OpenCAI.events import Event
from OpenCAI.user_prompt import UserPromptOption, UserPromptRequest
from OpenCAI.workflow.clarify import ClarifyResult, render_clarify_run
from OpenCAI.workflow.commands import run_clarify_for_session


ExecuteGuidedTask = Callable[[str, DemandBrief], list[Event]]
GuidedReviewProvider = Callable[[DemandBrief], str]
GUIDED_EXECUTE_RESPONSES = {"execute", "run", "yes", "y"}
GUIDED_STOP_RESPONSES = {"stop", "abort", "cancel", "no", "n"}
DEFAULT_MAX_REVIEW_ROUNDS = 3


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
    review_provider: GuidedReviewProvider | None = None,
    max_review_rounds: int = DEFAULT_MAX_REVIEW_ROUNDS,
) -> list[Event]:
    session_context = getattr(session, "session_context", None)
    base_session_context_summary = session_context.render() if session_context else ""
    review_feedback: list[str] = []
    previous_brief: DemandBrief | None = None
    ask_review = review_provider or _prompt_for_guided_review

    while True:
        clarify_run = run_clarify_for_session(
            session,
            task,
            session_context_summary=_compose_guided_clarify_context(
                base_session_context_summary,
                previous_brief,
                tuple(review_feedback),
            ),
        )
        print(render_clarify_run(clarify_run))
        if clarify_run.status == "blocked" or clarify_run.result is None:
            return []

        demand_brief = demand_brief_from_clarify_result(clarify_run.result)
        print(render_guided_demand_brief(demand_brief))
        review_input = ask_review(demand_brief).strip()
        normalized_review = review_input.lower()

        if normalized_review in GUIDED_EXECUTE_RESPONSES:
            return execute_task(demand_brief.refined_goal, demand_brief)

        if normalized_review in GUIDED_STOP_RESPONSES:
            print("Guided task stopped before execution.")
            return []

        if not review_input:
            print('Empty guided review response. Type "execute", "stop", or describe changes.')
            continue

        review_feedback.append(review_input)
        previous_brief = demand_brief
        if len(review_feedback) > max_review_rounds:
            print("Guided task stopped before execution: maximum review rounds reached.")
            return []


def render_guided_demand_brief(brief: DemandBrief) -> str:
    lines = [
        "• Guided demand brief:",
        "Refined goal:",
        brief.refined_goal,
        "",
        "Success criteria:",
        *_render_items(brief.success_criteria),
        "",
        "Scope:",
        *_render_items(brief.scope),
        "",
        "Constraints:",
        *_render_items(brief.constraints),
        "",
        "Assumptions:",
        *_render_items(brief.assumptions),
        "",
        "Open questions:",
        *_render_items(brief.open_questions),
    ]
    return "\n".join(lines)


def _prompt_for_guided_review(brief: DemandBrief) -> str:
    if not sys.stdin.isatty():
        return "execute"
    try:
        from OpenCAI.tui import ask_user_prompt

        result = ask_user_prompt(
            UserPromptRequest(
                kind="guided_review",
                title="Review guided demand",
                question="How should OpenCAI handle this DemandBrief?",
                options=(
                    UserPromptOption(
                        id="execute",
                        label="Execute",
                        description="Run the refined task with this DemandBrief.",
                        value="execute",
                    ),
                    UserPromptOption(
                        id="revise",
                        label="Revise demand",
                        description="Send feedback back to Clarify before execution.",
                        value="revise",
                        requires_input=True,
                        input_label="Revision feedback",
                    ),
                    UserPromptOption(
                        id="stop",
                        label="Stop",
                        description="Stop this guided run without executing the task.",
                        value="stop",
                    ),
                ),
            )
        )
        if result is None:
            return "stop"
        if result.selected_option_id == "revise":
            return result.custom_answer.strip() or "Revise the DemandBrief before execution."
        return result.value
    except (EOFError, KeyboardInterrupt):
        return "stop"


def _compose_guided_clarify_context(
    session_context_summary: str,
    previous_brief: DemandBrief | None,
    review_feedback: tuple[str, ...],
) -> str:
    parts = [session_context_summary.strip()] if session_context_summary.strip() else []
    if previous_brief is not None:
        parts.append(
            "Previous guided DemandBrief rejected by user:\n"
            f"{render_demand_brief(previous_brief)}"
        )
    if review_feedback:
        parts.append(
            "Guided review feedback:\n"
            + "\n".join(
                f"{index}. {feedback}"
                for index, feedback in enumerate(review_feedback, start=1)
            )
        )
    return "\n\n".join(parts)


def _render_items(items: tuple[str, ...]) -> list[str]:
    if not items:
        return ["- (none)"]
    return [f"- {item}" for item in items]
