from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Protocol

from OpenCAI.llm_adapter import FakeLLMAdapter, GeminiAdapter, LLMAdapter, LLMAdapterError, Message, ModelOutput
from OpenCAI.output_format import format_output_title
from OpenCAI.workflow import WorkflowPlan, build_inspect_handoff_workflow_plan
from OpenCAI.workflow.clarify import ClarifyResult


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PhaseDraft:
    id: str
    role: str


@dataclass(frozen=True)
class TaskDraft:
    id: str
    phase_id: str
    role: str
    instruction: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScriptOpDraft:
    type: str
    phase_id: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class WorkflowPlanDraft:
    selected_template: str
    rationale: str
    phases: tuple[PhaseDraft, ...]
    tasks: tuple[TaskDraft, ...]
    script_ops: tuple[ScriptOpDraft, ...]
    assumptions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()


class PlanningError(Exception):
    """Raised when a planner cannot produce a usable workflow draft."""


class PlanningAgent(Protocol):
    def plan(self, task: str) -> WorkflowPlanDraft:
        ...


class WorkflowPlanningAgent:
    """Draft workflow intent before deterministic compilation."""

    def plan(self, task: str) -> WorkflowPlanDraft:
        return WorkflowPlanDraft(
            selected_template="inspect_handoff",
            rationale="deterministic planner selected the built-in inspect_handoff template",
            phases=(
                PhaseDraft(id="inspect", role="inspector"),
                PhaseDraft(id="handoff", role="handoff"),
            ),
            tasks=(
                TaskDraft(
                    id="inspect_context",
                    phase_id="inspect",
                    role="inspector",
                    instruction=(
                        "Inspect the original task and identify the relevant context. "
                        "Do not modify files."
                    ),
                ),
                TaskDraft(
                    id="inspect_constraints",
                    phase_id="inspect",
                    role="inspector",
                    instruction=(
                        "Identify constraints, risks, and verification needs for the original task. "
                        "Do not modify files."
                    ),
                ),
                TaskDraft(
                    id="handoff_summary",
                    phase_id="handoff",
                    role="handoff",
                    instruction="Use the previous task results to produce the final answer.",
                    depends_on=("inspect_context", "inspect_constraints"),
                ),
            ),
            script_ops=(
                ScriptOpDraft(type="run_phase", phase_id="inspect"),
                ScriptOpDraft(type="run_phase", phase_id="handoff"),
                ScriptOpDraft(type="handoff", phase_id="handoff"),
            ),
            assumptions=("The task can be handled by the current built-in workflow template.",),
            risks=("Planner Agent is deterministic in this slice and does not yet inspect repo context.",),
        )


class LLMWorkflowPlanningAgent:
    """Use an LLMAdapter to draft workflow intent as structured JSON."""

    def __init__(
        self,
        *,
        adapter: LLMAdapter,
        current_repo_context_summary: str = "",
    ) -> None:
        self.adapter = adapter
        self.current_repo_context_summary = current_repo_context_summary

    def plan(self, task: str) -> WorkflowPlanDraft:
        output = self.adapter.call(self._messages(task), tools={})
        if output.get("type") != "final_answer":
            raise PlanningError("Workflow planner LLM must return a final_answer JSON draft.")

        answer = output.get("answer")
        if not isinstance(answer, str):
            raise PlanningError("Workflow planner final_answer must be a JSON string.")

        return workflow_plan_draft_from_json(answer)

    def _messages(self, task: str) -> list[Message]:
        context = self.current_repo_context_summary.strip() or "No extra repo context summary was provided."
        return [
            {
                "role": "system",
                "content": (
                    "You are the OpenCAI Workflow Planning Agent. "
                    "Return only JSON. Do not use markdown fences. "
                    "Draft workflow intent; do not claim the plan is executable. "
                    "The deterministic compiler and runner will validate it later. "
                    "Supported selected_template values: inspect_handoff. "
                    "Supported script op types in this slice: run_phase, handoff, stop. "
                    "The current inspect_handoff template uses phases inspect and handoff. "
                    "JSON shape: selected_template string, rationale string, phases array "
                    "of {id, role}, tasks array of {id, phase_id, role, instruction, depends_on}, "
                    "script_ops array of {type, phase_id, reason}, assumptions array, risks array."
                ),
            },
            {
                "role": "user",
                "content": (
                    "User task:\n"
                    f"{task}\n\n"
                    "Current repo context summary:\n"
                    f"{context}"
                ),
            },
        ]


class FakeWorkflowPlannerAdapter:
    """Fake planner model for isolated planner CLI checks."""

    def call(self, messages: list[Message], tools: dict[str, Any]) -> ModelOutput:
        draft = WorkflowPlanningAgent().plan(_last_user_task(messages))
        return {
            "type": "final_answer",
            "answer": workflow_plan_draft_to_json(draft),
        }


def workflow_plan_draft_from_json(text: str) -> WorkflowPlanDraft:
    try:
        raw = json.loads(_strip_json_wrapper(text))
    except json.JSONDecodeError as exc:
        raise PlanningError("Workflow planner returned invalid JSON.") from exc

    if not isinstance(raw, dict):
        raise PlanningError("Workflow planner JSON must be an object.")

    return workflow_plan_draft_from_mapping(raw)


def workflow_plan_draft_from_mapping(raw: dict[str, Any]) -> WorkflowPlanDraft:
    phases = tuple(
        PhaseDraft(
            id=_required_string(phase, "id", "phase"),
            role=_required_string(phase, "role", "phase"),
        )
        for phase in _required_list(raw, "phases")
    )
    tasks = tuple(
        TaskDraft(
            id=_required_string(task, "id", "task"),
            phase_id=_required_string(task, "phase_id", "task"),
            role=_required_string(task, "role", "task"),
            instruction=_required_string(task, "instruction", "task"),
            depends_on=_string_tuple(task.get("depends_on", ()), "task.depends_on"),
        )
        for task in _required_list(raw, "tasks")
    )
    script_ops = tuple(
        ScriptOpDraft(
            type=_required_string(op, "type", "script op"),
            phase_id=_optional_string(op.get("phase_id"), "script op phase_id"),
            reason=_optional_string(op.get("reason"), "script op reason"),
        )
        for op in _required_list(raw, "script_ops")
    )
    return WorkflowPlanDraft(
        selected_template=_required_string(raw, "selected_template", "workflow draft"),
        rationale=_required_string(raw, "rationale", "workflow draft"),
        phases=phases,
        tasks=tasks,
        script_ops=script_ops,
        assumptions=_string_tuple(raw.get("assumptions", ()), "assumptions"),
        risks=_string_tuple(raw.get("risks", ()), "risks"),
    )


def workflow_plan_draft_to_json(draft: WorkflowPlanDraft) -> str:
    payload = {
        "selected_template": draft.selected_template,
        "rationale": draft.rationale,
        "phases": [{"id": phase.id, "role": phase.role} for phase in draft.phases],
        "tasks": [
            {
                "id": task.id,
                "phase_id": task.phase_id,
                "role": task.role,
                "instruction": task.instruction,
                "depends_on": list(task.depends_on),
            }
            for task in draft.tasks
        ],
        "script_ops": [
            {
                "type": op.type,
                "phase_id": op.phase_id,
                "reason": op.reason,
            }
            for op in draft.script_ops
        ],
        "assumptions": list(draft.assumptions),
        "risks": list(draft.risks),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_workflow_plan_draft(draft: WorkflowPlanDraft) -> str:
    lines = [
        format_output_title(f"Workflow planner draft: {draft.selected_template}"),
        f"rationale: {draft.rationale}",
        "",
        format_output_title("Phases:"),
    ]
    for index, phase in enumerate(draft.phases, start=1):
        lines.append(f"{index}. {phase.id}")
        lines.append(f"   role: {phase.role}")

    lines.extend(["", format_output_title("Tasks:")])
    for index, task in enumerate(draft.tasks, start=1):
        depends_on = ", ".join(task.depends_on) if task.depends_on else "none"
        lines.append(f"{index}. {task.id}")
        lines.append(f"   phase: {task.phase_id}")
        lines.append(f"   role: {task.role}")
        lines.append(f"   depends_on: {depends_on}")
        lines.append(f"   instruction: {task.instruction}")

    lines.extend(["", format_output_title("Script ops:")])
    for index, op in enumerate(draft.script_ops, start=1):
        target = f" {op.phase_id}" if op.phase_id else ""
        reason = f" reason: {op.reason}" if op.reason else ""
        lines.append(f"{index}. {op.type}{target}{reason}")

    lines.extend(["", "assumptions:"])
    for assumption in draft.assumptions:
        lines.append(f"- {assumption}")

    lines.append("risks:")
    for risk in draft.risks:
        lines.append(f"- {risk}")

    return "\n".join(lines)


def compile_workflow(
    task: str,
    planning_agent: PlanningAgent | None = None,
    clarify_result: ClarifyResult | None = None,
) -> WorkflowPlan:
    agent = planning_agent or WorkflowPlanningAgent()
    planning_task = clarify_result.refined_task if clarify_result is not None else task
    draft = agent.plan(planning_task)
    if draft.selected_template != "inspect_handoff":
        raise ValueError(f"Unsupported workflow template: {draft.selected_template}")
    return build_inspect_handoff_workflow_plan()


def build_planning_agent(
    adapter_name: str,
    api_key: str | None,
    *,
    current_repo_context_summary: str = "",
) -> PlanningAgent:
    if adapter_name == "fake":
        return LLMWorkflowPlanningAgent(
            adapter=FakeWorkflowPlannerAdapter(),
            current_repo_context_summary=current_repo_context_summary,
        )
    if adapter_name == "gemini":
        return LLMWorkflowPlanningAgent(
            adapter=GeminiAdapter(api_key or ""),
            current_repo_context_summary=current_repo_context_summary,
        )
    if adapter_name == "deterministic":
        return WorkflowPlanningAgent()
    raise PlanningError(f"Unknown planner adapter: {adapter_name}")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m OpenCAI.workflow.planner",
        description="Plan an OpenCAI workflow without executing the runner.",
    )
    parser.add_argument("--task", required=True, help="Task to plan.")
    parser.add_argument(
        "--adapter",
        choices=["deterministic", "fake", "gemini"],
        default="gemini",
        help="Planner adapter. Gemini requires GEMINI_API_KEY.",
    )
    parser.add_argument(
        "--context-summary",
        default="",
        help="Optional concise repo context summary for the planner prompt.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw WorkflowPlanDraft JSON instead of a readable summary.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_env_file(PROJECT_ROOT / ".env")
    args = build_parser().parse_args(argv)

    try:
        agent = build_planning_agent(
            args.adapter,
            os.environ.get("GEMINI_API_KEY"),
            current_repo_context_summary=args.context_summary,
        )
        draft = agent.plan(args.task)
    except (PlanningError, LLMAdapterError) as exc:
        print(f"Workflow planner error: {exc}")
        return 1

    if args.json:
        print(workflow_plan_draft_to_json(draft))
    else:
        print(render_workflow_plan_draft(draft))
    return 0


def _strip_json_wrapper(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _required_list(raw: dict[str, Any], key: str) -> list[Any]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise PlanningError(f"Workflow planner JSON requires list field: {key}")
    return value


def _required_string(raw: object, key: str, label: str) -> str:
    if not isinstance(raw, dict):
        raise PlanningError(f"Workflow planner {label} must be an object.")
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PlanningError(f"Workflow planner {label} requires string field: {key}")
    return value.strip()


def _optional_string(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PlanningError(f"Workflow planner {label} must be a string when provided.")
    return value.strip() or None


def _string_tuple(value: object, label: str) -> tuple[str, ...]:
    if isinstance(value, tuple):
        items = value
    elif isinstance(value, list):
        items = tuple(value)
    else:
        raise PlanningError(f"Workflow planner {label} must be a list of strings.")

    strings = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise PlanningError(f"Workflow planner {label} must contain only strings.")
        strings.append(item.strip())
    return tuple(strings)


def _last_user_task(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content", "")
            if isinstance(content, str):
                return content
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
