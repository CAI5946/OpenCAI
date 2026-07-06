from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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


@dataclass(frozen=True)
class PendingGuidedReview:
    original_task: str
    demand_brief: DemandBrief
    base_session_context_summary: str = ""
    review_feedback: tuple[str, ...] = ()
    max_review_rounds: int = DEFAULT_MAX_REVIEW_ROUNDS


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
    ask_review = review_provider or _prompt_for_guided_review
    pending = start_guided_review(
        session,
        task,
        max_review_rounds=max_review_rounds,
    )

    while pending is not None:
        pending, events = handle_pending_guided_review(
            session,
            pending,
            execute_task=execute_task,
            review_provider=ask_review,
        )
        if events:
            return events
    return []


def start_guided_review(
    session: Any,
    task: str,
    *,
    base_session_context_summary: str | None = None,
    previous_brief: DemandBrief | None = None,
    review_feedback: tuple[str, ...] = (),
    max_review_rounds: int = DEFAULT_MAX_REVIEW_ROUNDS,
) -> PendingGuidedReview | None:
    session_context = getattr(session, "session_context", None)
    base_context = (
        base_session_context_summary
        if base_session_context_summary is not None
        else session_context.render() if session_context else ""
    )
    clarify_run = run_clarify_for_session(
        session,
        task,
        session_context_summary=_compose_guided_clarify_context(
            base_context,
            previous_brief,
            review_feedback,
        ),
    )
    print(render_clarify_run(clarify_run))
    if clarify_run.status == "blocked" or clarify_run.result is None:
        return None

    demand_brief = demand_brief_from_clarify_result(clarify_run.result)
    print(render_guided_demand_brief(demand_brief))
    return PendingGuidedReview(
        original_task=task,
        demand_brief=demand_brief,
        base_session_context_summary=base_context,
        review_feedback=review_feedback,
        max_review_rounds=max_review_rounds,
    )


def handle_pending_guided_review(
    session: Any,
    pending: PendingGuidedReview,
    *,
    execute_task: ExecuteGuidedTask,
    review_provider: GuidedReviewProvider | None = None,
) -> tuple[PendingGuidedReview | None, list[Event]]:
    ask_review = review_provider or _prompt_for_guided_review
    review_input = ask_review(pending.demand_brief).strip()
    normalized_review = review_input.lower()

    if normalized_review in GUIDED_EXECUTE_RESPONSES:
        return None, execute_task(pending.demand_brief.refined_goal, pending.demand_brief)

    if normalized_review in GUIDED_STOP_RESPONSES:
        print("Guided task stopped before execution.")
        return None, []

    if not review_input:
        print('Empty guided review response. Type "execute", "stop", or describe changes.')
        return pending, []

    review_feedback = pending.review_feedback + (review_input,)
    if len(review_feedback) > pending.max_review_rounds:
        print("Guided task stopped before execution: maximum review rounds reached.")
        return None, []

    next_pending = start_guided_review(
        session,
        pending.original_task,
        base_session_context_summary=pending.base_session_context_summary,
        previous_brief=pending.demand_brief,
        review_feedback=review_feedback,
        max_review_rounds=pending.max_review_rounds,
    )
    return next_pending, []


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
        if result is None or result.cancelled:
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
