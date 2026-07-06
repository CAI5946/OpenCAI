from __future__ import annotations

from dataclasses import dataclass
from html import escape


DEFAULT_SUCCESS_CRITERION = "Complete the refined goal without expanding scope."
DEFAULT_SUCCESS_CRITERION_ASSUMPTION = (
    "Success criteria were not provided; using the default completion criterion."
)


@dataclass(frozen=True)
class DemandBrief:
    original_task: str
    refined_goal: str
    success_criteria: tuple[str, ...]
    scope: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        original_task = self.original_task.strip()
        refined_goal = self.refined_goal.strip()
        if not original_task:
            raise ValueError("DemandBrief requires original_task.")
        if not refined_goal:
            raise ValueError("DemandBrief requires refined_goal.")

        criteria = _clean_items(self.success_criteria)
        assumptions = _clean_items(self.assumptions)
        if not criteria:
            criteria = (DEFAULT_SUCCESS_CRITERION,)
            assumptions = assumptions + (DEFAULT_SUCCESS_CRITERION_ASSUMPTION,)

        object.__setattr__(self, "original_task", original_task)
        object.__setattr__(self, "refined_goal", refined_goal)
        object.__setattr__(self, "success_criteria", criteria)
        object.__setattr__(self, "scope", _clean_items(self.scope))
        object.__setattr__(self, "constraints", _clean_items(self.constraints))
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(self, "open_questions", _clean_items(self.open_questions))


def render_demand_brief(brief: DemandBrief) -> str:
    lines = [
        "<demand_brief>",
        "Original task:",
        _render_text(brief.original_task),
        "",
        "Refined goal:",
        _render_text(brief.refined_goal),
        "",
        "Success criteria:",
        *_render_list(brief.success_criteria),
        "",
        "Scope:",
        *_render_list(brief.scope),
        "",
        "Constraints:",
        *_render_list(brief.constraints),
        "",
        "Assumptions:",
        *_render_list(brief.assumptions),
        "",
        "Open questions:",
        *_render_list(brief.open_questions),
        "</demand_brief>",
    ]
    return "\n".join(lines)


def _clean_items(items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(item.strip() for item in items if item.strip())


def _render_text(value: str) -> str:
    return escape(value, quote=False)


def _render_list(items: tuple[str, ...]) -> list[str]:
    if not items:
        return ["- (none)"]
    return [f"- {_render_text(item)}" for item in items]
