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
    aggregation_policy: str = "all_must_pass"


@dataclass(frozen=True)
class WorkflowTask:
    id: str
    phase_id: str
    role: str
    prompt_template: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowSpec:
    name: str
    phases: tuple[WorkflowPhase, ...]
    tasks: tuple[WorkflowTask, ...]
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
            WorkflowPhase(id="inspect", role="inspector"),
            WorkflowPhase(id="handoff", role="handoff"),
        ),
        tasks=(
            WorkflowTask(
                id="inspect_context",
                phase_id="inspect",
                role="inspector",
                prompt_template=(
                    "Inspect the original task and identify the relevant context. "
                    "Do not modify files."
                ),
            ),
            WorkflowTask(
                id="inspect_constraints",
                phase_id="inspect",
                role="inspector",
                prompt_template=(
                    "Identify constraints, risks, and verification needs for the original task. "
                    "Do not modify files."
                ),
            ),
            WorkflowTask(
                id="handoff_summary",
                phase_id="handoff",
                role="handoff",
                prompt_template=(
                    "Use the previous task results to produce the final answer."
                ),
                depends_on=("inspect_context", "inspect_constraints"),
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
        lines.extend(
            [
                f"{index}. {phase.id}{final_marker}",
                f"   role: {phase.role}",
                f"   aggregation: {phase.aggregation_policy}",
            ]
        )

    lines.extend(["", format_output_title("Tasks:")])
    for index, task in enumerate(spec.tasks, start=1):
        final_marker = " (final phase)" if task.phase_id == spec.final_phase_id else ""
        depends_on = ", ".join(task.depends_on) if task.depends_on else "none"
        lines.extend(
            [
                f"{index}. {task.id}{final_marker}",
                f"   phase: {task.phase_id}",
                f"   role: {task.role}",
                f"   depends_on: {depends_on}",
                f"   instruction: {task.prompt_template}",
            ]
        )

    return "\n".join(lines)


@dataclass
class TaskResult:
    task_id: str
    phase_id: str
    status: WorkflowStatus
    events: list[Event] = field(default_factory=list)
    final_answer: str | None = None
    error: str | None = None


@dataclass
class PhaseResult:
    phase_id: str
    status: WorkflowStatus
    task_results: list[TaskResult] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    aggregate_summary: str | None = None
    final_answer: str | None = None
    error: str | None = None


@dataclass
class WorkflowRun:
    task: str
    status: WorkflowStatus = "pending"
    task_results: list[TaskResult] = field(default_factory=list)
    phase_results: list[PhaseResult] = field(default_factory=list)
    final_answer: str | None = None

    def result_for(self, phase_id: str) -> PhaseResult | None:
        for result in self.phase_results:
            if result.phase_id == phase_id:
                return result
        return None

    def task_result_for(self, task_id: str) -> TaskResult | None:
        for result in self.task_results:
            if result.task_id == task_id:
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
        lines.append(f"  tasks: {len(result.task_results)}")
        lines.append(f"  events: {len(result.events)}")
        if result.aggregate_summary:
            lines.append(f"  aggregate_summary: {result.aggregate_summary}")
        if result.final_answer:
            lines.append(f"  final_answer: {result.final_answer}")
        if result.error:
            lines.append(f"  error: {result.error}")
        for task_result in result.task_results:
            lines.append(f"  - {task_result.task_id}: {task_result.status}")
            if task_result.final_answer:
                lines.append(f"    final_answer: {task_result.final_answer}")
            if task_result.error:
                lines.append(f"    error: {task_result.error}")

    return "\n".join(lines)


class SerialWorkflowRunner:
    """Run workflow tasks one after another through the existing Agent Loop."""

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

        for workflow_task in spec.tasks:
            result = self.run_task(workflow_task, workflow_run)
            workflow_run.task_results.append(result)

        workflow_run.phase_results = self.aggregate_phase_results(spec, workflow_run.task_results)
        final_result = workflow_run.result_for(spec.final_phase_id)
        if final_result is None or final_result.status != "passed" or final_result.final_answer is None:
            workflow_run.status = "failed"
            return workflow_run

        if any(result.status != "passed" for result in workflow_run.task_results):
            workflow_run.status = "failed"
            return workflow_run

        workflow_run.final_answer = final_result.final_answer
        workflow_run.status = "passed"
        return workflow_run

    def validate_spec(self, spec: WorkflowSpec) -> list[str]:
        phase_ids = [phase.id for phase in spec.phases]
        task_ids = [task.id for task in spec.tasks]
        errors = []

        if not spec.phases:
            errors.append("Workflow must define at least one phase.")

        if not spec.tasks:
            errors.append("Workflow must define at least one task.")

        duplicate_phase_ids = sorted({phase_id for phase_id in phase_ids if phase_ids.count(phase_id) > 1})
        if duplicate_phase_ids:
            errors.append("Duplicate phase ids: " + ", ".join(duplicate_phase_ids))

        duplicate_task_ids = sorted({task_id for task_id in task_ids if task_ids.count(task_id) > 1})
        if duplicate_task_ids:
            errors.append("Duplicate task ids: " + ", ".join(duplicate_task_ids))

        if spec.final_phase_id not in phase_ids:
            errors.append(f"final_phase_id does not match any phase: {spec.final_phase_id}")

        if phase_ids and spec.final_phase_id != phase_ids[-1]:
            errors.append("final_phase_id must point to the last phase in a serial workflow.")

        tasks_by_phase = self._tasks_by_phase(spec)
        for phase_id in phase_ids:
            if not tasks_by_phase.get(phase_id):
                errors.append(f"Phase must contain at least one task: {phase_id}")

        final_phase_tasks = tasks_by_phase.get(spec.final_phase_id, [])
        if spec.final_phase_id in phase_ids and len(final_phase_tasks) != 1:
            errors.append("final_phase_id must contain exactly one task.")

        seen_task_ids: set[str] = set()
        all_task_ids = set(task_ids)
        all_phase_ids = set(phase_ids)
        for workflow_task in spec.tasks:
            if workflow_task.phase_id not in all_phase_ids:
                errors.append(
                    f"Task {workflow_task.id} references unknown phase_id: {workflow_task.phase_id}"
                )
            for dependency in workflow_task.depends_on:
                if dependency not in all_task_ids:
                    errors.append(
                        f"Task {workflow_task.id} depends on unknown task: {dependency}"
                    )
                elif dependency not in seen_task_ids:
                    errors.append(
                        f"Task {workflow_task.id} depends on a later task in serial order: {dependency}"
                    )
            seen_task_ids.add(workflow_task.id)

        return errors

    def run_task(self, workflow_task: WorkflowTask, workflow_run: WorkflowRun) -> TaskResult:
        missing_dependencies = self._missing_passed_task_dependencies(workflow_task, workflow_run)
        if missing_dependencies:
            return TaskResult(
                task_id=workflow_task.id,
                phase_id=workflow_task.phase_id,
                status="skipped",
                error="Missing passed dependencies: " + ", ".join(missing_dependencies),
            )

        prompt = self.compose_task_prompt(workflow_task, workflow_run)
        events = self.agent_loop(
            prompt,
            cwd=self.cwd,
            max_steps=self.max_steps,
            adapter=self.adapter,
            policy=self.policy,
        )
        return self._task_result_from_events(workflow_task, events)

    def compose_task_prompt(self, workflow_task: WorkflowTask, workflow_run: WorkflowRun) -> str:
        previous_results = []
        for result in workflow_run.task_results:
            summary = result.final_answer or result.error or ""
            previous_results.append(f"[{result.task_id}] {result.status}: {summary}")

        previous_text = "\n".join(previous_results) if previous_results else "(none)"

        return (
            "Original task:\n"
            f"{workflow_run.task}\n\n"
            "Current task:\n"
            f"{workflow_task.id} ({workflow_task.role})\n\n"
            "Phase:\n"
            f"{workflow_task.phase_id}\n\n"
            "Instruction:\n"
            f"{workflow_task.prompt_template}\n\n"
            "Previous task results:\n"
            f"{previous_text}"
        )

    def aggregate_phase_results(
        self,
        spec: WorkflowSpec,
        task_results: list[TaskResult],
    ) -> list[PhaseResult]:
        phase_results: list[PhaseResult] = []
        for phase in spec.phases:
            phase_task_results = [
                result for result in task_results if result.phase_id == phase.id
            ]
            if not phase_task_results:
                continue

            status: WorkflowStatus = "passed"
            if any(result.status != "passed" for result in phase_task_results):
                status = "failed"

            events = [
                event
                for task_result in phase_task_results
                for event in task_result.events
            ]
            summary_parts = []
            errors = []
            for task_result in phase_task_results:
                if task_result.final_answer:
                    summary_parts.append(f"{task_result.task_id}: {task_result.final_answer}")
                elif task_result.error:
                    summary_parts.append(f"{task_result.task_id}: {task_result.error}")
                    errors.append(task_result.error)
                else:
                    summary_parts.append(f"{task_result.task_id}: {task_result.status}")

            final_answer = (
                phase_task_results[0].final_answer
                if len(phase_task_results) == 1 and status == "passed"
                else None
            )
            phase_results.append(
                PhaseResult(
                    phase_id=phase.id,
                    status=status,
                    task_results=phase_task_results,
                    events=events,
                    aggregate_summary="; ".join(summary_parts),
                    final_answer=final_answer,
                    error="; ".join(errors) if errors else None,
                )
            )

        return phase_results

    def _tasks_by_phase(self, spec: WorkflowSpec) -> dict[str, list[WorkflowTask]]:
        tasks_by_phase: dict[str, list[WorkflowTask]] = {}
        for workflow_task in spec.tasks:
            tasks_by_phase.setdefault(workflow_task.phase_id, []).append(workflow_task)
        return tasks_by_phase

    def _missing_passed_task_dependencies(
        self,
        workflow_task: WorkflowTask,
        workflow_run: WorkflowRun,
    ) -> list[str]:
        missing = []
        for dependency in workflow_task.depends_on:
            result = workflow_run.task_result_for(dependency)
            if result is None or result.status != "passed":
                missing.append(dependency)
        return missing

    def _task_result_from_events(
        self,
        workflow_task: WorkflowTask,
        events: list[Event],
    ) -> TaskResult:
        error = self._last_event_message(events, "error")
        final = self._last_final_answer(events)
        stop_reason = self._last_stop_reason(events)

        if error is not None:
            return TaskResult(
                task_id=workflow_task.id,
                phase_id=workflow_task.phase_id,
                status="failed",
                events=events,
                final_answer=final,
                error=error,
            )

        if stop_reason is not None:
            return TaskResult(
                task_id=workflow_task.id,
                phase_id=workflow_task.phase_id,
                status="failed",
                events=events,
                error=f"Task stopped: {stop_reason}",
            )

        if final is None:
            return TaskResult(
                task_id=workflow_task.id,
                phase_id=workflow_task.phase_id,
                status="failed",
                events=events,
                error="Task ended without a final answer.",
            )

        return TaskResult(
            task_id=workflow_task.id,
            phase_id=workflow_task.phase_id,
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
