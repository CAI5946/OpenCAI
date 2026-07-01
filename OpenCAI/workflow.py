"""Minimal serial workflow runtime for OpenCAI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from OpenCAI.agent_loop import run_agent_loop
from OpenCAI.events import Event
from OpenCAI.llm_adapter import LLMAdapter
from OpenCAI.output_format import format_output_title
from OpenCAI.safety import SafetyPolicy


WorkflowStatus = Literal["pending", "running", "passed", "failed", "skipped"]

AgentLoopRunner = Callable[..., list[Event]]


@dataclass(frozen=True)
class WorkflowPhase:
    id: str
    role: str
    prompt_template: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowSpec:
    name: str
    phases: tuple[WorkflowPhase, ...]
    final_phase_id: str = "handoff"
    description: str = ""
    max_retries: int = 0


def build_inspect_handoff_workflow() -> WorkflowSpec:
    """Build the first reusable built-in workflow template."""
    return WorkflowSpec(
        name="inspect_handoff",
        description="Inspect a task, then produce a final handoff answer.",
        final_phase_id="handoff",
        phases=(
            WorkflowPhase(
                id="inspect",
                role="inspector",
                prompt_template=(
                    "Inspect the original task and identify the relevant context. "
                    "Do not modify files."
                ),
            ),
            WorkflowPhase(
                id="handoff",
                role="handoff",
                prompt_template=(
                    "Use the previous phase results to produce the final answer."
                ),
                depends_on=("inspect",),
            ),
        ),
    )


def render_workflow_plan(spec: WorkflowSpec) -> str:
    """Render a workflow spec as a human-checkable execution plan."""
    lines = [
        format_output_title(f"Workflow: {spec.name}"),
    ]
    if spec.description:
        lines.append(format_output_title(f"Description: {spec.description}"))
    lines.extend(
        [
            format_output_title(f"Final phase: {spec.final_phase_id}"),
            "",
            format_output_title("Phases:"),
        ]
    )

    for index, phase in enumerate(spec.phases, start=1):
        final_marker = " (final)" if phase.id == spec.final_phase_id else ""
        depends_on = ", ".join(phase.depends_on) if phase.depends_on else "none"
        lines.extend(
            [
                f"{index}. {phase.id}{final_marker}",
                f"   role: {phase.role}",
                f"   depends_on: {depends_on}",
                f"   instruction: {phase.prompt_template}",
            ]
        )

    return "\n".join(lines)


@dataclass
class PhaseResult:
    phase_id: str
    status: WorkflowStatus
    events: list[Event] = field(default_factory=list)
    final_answer: str | None = None
    error: str | None = None


@dataclass
class WorkflowRun:
    task: str
    status: WorkflowStatus = "pending"
    phase_results: list[PhaseResult] = field(default_factory=list)
    final_answer: str | None = None

    def result_for(self, phase_id: str) -> PhaseResult | None:
        for result in self.phase_results:
            if result.phase_id == phase_id:
                return result
        return None


def render_workflow_process(workflow_run: WorkflowRun) -> str:
    """Render a completed workflow run as a compact process summary."""
    lines = [
        format_output_title(f"Workflow status: {workflow_run.status}"),
        format_output_title("Workflow final answer:"),
        workflow_run.final_answer or "Workflow did not produce a final answer.",
        "",
        format_output_title("Workflow process:"),
    ]

    if not workflow_run.phase_results:
        lines.append("- no phase results")
        return "\n".join(lines)

    for result in workflow_run.phase_results:
        lines.append(f"- {result.phase_id}: {result.status}")
        lines.append(f"  events: {len(result.events)}")
        if result.final_answer:
            lines.append(f"  final_answer: {result.final_answer}")
        if result.error:
            lines.append(f"  error: {result.error}")

    return "\n".join(lines)


class SerialWorkflowRunner:
    """Run workflow phases one after another through the existing Agent Loop."""

    def __init__(
        self,
        *,
        agent_loop: AgentLoopRunner = run_agent_loop,
        cwd: Path | None = None,
        max_steps: int = 8,
        adapter: LLMAdapter | None = None,
        policy: SafetyPolicy | None = None,
    ) -> None:
        self.agent_loop = agent_loop
        self.cwd = cwd
        self.max_steps = max_steps
        self.adapter = adapter
        self.policy = policy

    def run(self, spec: WorkflowSpec, task: str) -> WorkflowRun:
        workflow_run = WorkflowRun(task=task, status="running")
        validation_errors = self.validate_spec(spec)
        if validation_errors:
            workflow_run.status = "failed"
            workflow_run.phase_results.append(
                PhaseResult(
                    phase_id="workflow",
                    status="failed",
                    error="Invalid workflow spec: " + "; ".join(validation_errors),
                )
            )
            return workflow_run

        for phase in spec.phases:
            result = self.run_phase(phase, workflow_run)
            workflow_run.phase_results.append(result)
            if result.status != "passed":
                workflow_run.status = "failed"
                return workflow_run

        final_result = workflow_run.result_for(spec.final_phase_id)
        if final_result is None or final_result.status != "passed":
            workflow_run.status = "failed"
            return workflow_run

        workflow_run.final_answer = final_result.final_answer
        workflow_run.status = "passed"
        return workflow_run

    def validate_spec(self, spec: WorkflowSpec) -> list[str]:
        phase_ids = [phase.id for phase in spec.phases]
        errors = []

        if not spec.phases:
            errors.append("Workflow must define at least one phase.")

        if spec.final_phase_id not in phase_ids:
            errors.append(f"final_phase_id does not match any phase: {spec.final_phase_id}")

        if phase_ids and spec.final_phase_id != phase_ids[-1]:
            errors.append("final_phase_id must point to the last phase in a serial workflow.")

        return errors

    def run_phase(self, phase: WorkflowPhase, workflow_run: WorkflowRun) -> PhaseResult:
        missing_dependencies = self._missing_passed_dependencies(phase, workflow_run)
        if missing_dependencies:
            return PhaseResult(
                phase_id=phase.id,
                status="skipped",
                error="Missing passed dependencies: " + ", ".join(missing_dependencies),
            )

        prompt = self.compose_phase_prompt(phase, workflow_run)
        events = self.agent_loop(
            prompt,
            cwd=self.cwd,
            max_steps=self.max_steps,
            adapter=self.adapter,
            policy=self.policy,
        )
        return self._result_from_events(phase.id, events)

    def compose_phase_prompt(self, phase: WorkflowPhase, workflow_run: WorkflowRun) -> str:
        previous_results = []
        for result in workflow_run.phase_results:
            summary = result.final_answer or result.error or ""
            previous_results.append(f"[{result.phase_id}] {result.status}: {summary}")

        previous_text = "\n".join(previous_results) if previous_results else "(none)"

        return (
            "Original task:\n"
            f"{workflow_run.task}\n\n"
            "Current phase:\n"
            f"{phase.id} ({phase.role})\n\n"
            "Instruction:\n"
            f"{phase.prompt_template}\n\n"
            "Previous phase results:\n"
            f"{previous_text}"
        )

    def _missing_passed_dependencies(
        self,
        phase: WorkflowPhase,
        workflow_run: WorkflowRun,
    ) -> list[str]:
        missing = []
        for dependency in phase.depends_on:
            result = workflow_run.result_for(dependency)
            if result is None or result.status != "passed":
                missing.append(dependency)
        return missing

    def _result_from_events(self, phase_id: str, events: list[Event]) -> PhaseResult:
        error = self._last_event_message(events, "error")
        final = self._last_final_answer(events)
        stop_reason = self._last_stop_reason(events)

        if error is not None:
            return PhaseResult(
                phase_id=phase_id,
                status="failed",
                events=events,
                final_answer=final,
                error=error,
            )

        if stop_reason is not None:
            return PhaseResult(
                phase_id=phase_id,
                status="failed",
                events=events,
                error=f"Phase stopped: {stop_reason}",
            )

        if final is None:
            return PhaseResult(
                phase_id=phase_id,
                status="failed",
                events=events,
                error="Phase ended without a final answer.",
            )

        return PhaseResult(
            phase_id=phase_id,
            status="passed",
            events=events,
            final_answer=final,
        )

    def _last_final_answer(self, events: list[Event]) -> str | None:
        for event in reversed(events):
            if event["type"] == "final_answer":
                answer = event["data"].get("answer")
                if isinstance(answer, str):
                    return answer
                return event["message"]
        return None

    def _last_stop_reason(self, events: list[Event]) -> str | None:
        for event in reversed(events):
            if event["type"] == "stop":
                reason = event["data"].get("reason")
                if isinstance(reason, str):
                    return reason
                return event["message"]
        return None

    def _last_event_message(self, events: list[Event], event_type: str) -> str | None:
        for event in reversed(events):
            if event["type"] == event_type:
                return event["message"]
        return None
