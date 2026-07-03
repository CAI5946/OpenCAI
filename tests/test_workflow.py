import unittest

from OpenCAI.events import Event, final_answer, make_event, stop, user_task
from OpenCAI.workflow import (
    SerialWorkflowRunner,
    WorkflowPhase,
    WorkflowSpec,
    WorkflowTask,
    build_inspect_handoff_workflow,
    render_workflow_plan,
    render_workflow_process,
)


class RecordingAgentLoop:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, task: str, **kwargs: object) -> list[Event]:
        self.prompts.append(task)
        task_number = len(self.prompts)
        return [
            user_task(1, task),
            final_answer(2, f"task {task_number} complete"),
        ]


class WorkflowTest(unittest.TestCase):
    def test_render_workflow_process_shows_final_answer_phase_and_task_summary(self) -> None:
        agent_loop = RecordingAgentLoop()
        runner = SerialWorkflowRunner(agent_loop=agent_loop)

        workflow_run = runner.run(build_inspect_handoff_workflow(), "Read README")
        process = render_workflow_process(workflow_run)

        self.assertIn("• Workflow status: passed", process)
        self.assertIn("• Workflow final answer:", process)
        self.assertIn("task 3 complete", process)
        self.assertIn("• Workflow process:", process)
        self.assertIn("- inspect: passed", process)
        self.assertIn("  tasks: 2", process)
        self.assertIn("  - inspect_context: passed", process)
        self.assertIn("  - inspect_constraints: passed", process)
        self.assertIn("- handoff: passed", process)
        self.assertIn("  - handoff_summary: passed", process)

    def test_render_workflow_plan_shows_phases_tasks_and_dependencies(self) -> None:
        spec = build_inspect_handoff_workflow()

        plan = render_workflow_plan(spec)

        self.assertIn("• Workflow: inspect_handoff", plan)
        self.assertIn("• Final phase: handoff", plan)
        self.assertIn("• Phases:", plan)
        self.assertIn("1. inspect", plan)
        self.assertIn("2. handoff (final)", plan)
        self.assertIn("• Tasks:", plan)
        self.assertIn("1. inspect_context", plan)
        self.assertIn("phase: inspect", plan)
        self.assertIn("depends_on: none", plan)
        self.assertIn("3. handoff_summary (final phase)", plan)
        self.assertIn("depends_on: inspect_context, inspect_constraints", plan)

    def test_builtin_inspect_handoff_workflow_returns_final_answer_from_final_phase_task(self) -> None:
        agent_loop = RecordingAgentLoop()
        runner = SerialWorkflowRunner(agent_loop=agent_loop)
        spec = build_inspect_handoff_workflow()

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("inspect_handoff", spec.name)
        self.assertEqual("handoff", spec.final_phase_id)
        self.assertEqual(["inspect", "handoff"], [phase.id for phase in spec.phases])
        self.assertEqual(
            ["inspect_context", "inspect_constraints", "handoff_summary"],
            [task.id for task in spec.tasks],
        )
        self.assertEqual("passed", workflow_run.status)
        self.assertEqual("task 3 complete", workflow_run.final_answer)
        self.assertEqual(
            ["inspect_context", "inspect_constraints", "handoff_summary"],
            [result.task_id for result in workflow_run.task_results],
        )
        self.assertEqual(["inspect", "handoff"], [r.phase_id for r in workflow_run.phase_results])
        self.assertEqual(2, len(workflow_run.phase_results[0].task_results))
        self.assertEqual(1, len(workflow_run.phase_results[1].task_results))
        self.assertIn("[inspect_context] passed: task 1 complete", agent_loop.prompts[2])
        self.assertIn("[inspect_constraints] passed: task 2 complete", agent_loop.prompts[2])

    def test_runner_executes_tasks_and_aggregates_phase_results(self) -> None:
        agent_loop = RecordingAgentLoop()
        runner = SerialWorkflowRunner(agent_loop=agent_loop)
        spec = WorkflowSpec(
            name="collect_handoff",
            final_phase_id="handoff",
            phases=(
                WorkflowPhase(id="collect", role="collector"),
                WorkflowPhase(id="handoff", role="handoff"),
            ),
            tasks=(
                WorkflowTask(
                    id="inspect_code",
                    phase_id="collect",
                    role="inspector",
                    prompt_template="Inspect code.",
                ),
                WorkflowTask(
                    id="inspect_tests",
                    phase_id="collect",
                    role="inspector",
                    prompt_template="Inspect tests.",
                ),
                WorkflowTask(
                    id="handoff_summary",
                    phase_id="handoff",
                    role="handoff",
                    prompt_template="Summarize work.",
                    depends_on=("inspect_code", "inspect_tests"),
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("passed", workflow_run.status)
        self.assertEqual("task 3 complete", workflow_run.final_answer)
        self.assertEqual(["passed", "passed", "passed"], [r.status for r in workflow_run.task_results])
        self.assertEqual(["passed", "passed"], [r.status for r in workflow_run.phase_results])
        self.assertIn("inspect_code: task 1 complete", workflow_run.phase_results[0].aggregate_summary or "")
        self.assertIn("inspect_tests: task 2 complete", workflow_run.phase_results[0].aggregate_summary or "")
        self.assertEqual("task 3 complete", workflow_run.phase_results[1].final_answer)

    def test_failed_task_marks_phase_failed_and_skips_dependent_task(self) -> None:
        def failing_first_task(task: str, **kwargs: object) -> list[Event]:
            if "inspect_code" in task:
                return [user_task(1, task), make_event("error", 2, "inspection failed")]
            return [user_task(1, task), final_answer(2, "unexpected")]

        runner = SerialWorkflowRunner(agent_loop=failing_first_task)
        spec = WorkflowSpec(
            name="failed_dependency",
            final_phase_id="handoff",
            phases=(
                WorkflowPhase(id="inspect", role="inspector"),
                WorkflowPhase(id="handoff", role="handoff"),
            ),
            tasks=(
                WorkflowTask(
                    id="inspect_code",
                    phase_id="inspect",
                    role="inspector",
                    prompt_template="Inspect code.",
                ),
                WorkflowTask(
                    id="handoff_summary",
                    phase_id="handoff",
                    role="handoff",
                    prompt_template="Summarize.",
                    depends_on=("inspect_code",),
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("failed", workflow_run.status)
        self.assertEqual(["failed", "skipped"], [r.status for r in workflow_run.task_results])
        self.assertEqual(["failed", "failed"], [r.status for r in workflow_run.phase_results])
        self.assertIn("inspection failed", workflow_run.phase_results[0].error or "")
        self.assertIn("inspect_code", workflow_run.phase_results[1].error or "")

    def test_task_without_final_answer_fails(self) -> None:
        def incomplete_agent_loop(task: str, **kwargs: object) -> list[Event]:
            return [user_task(1, task)]

        runner = SerialWorkflowRunner(agent_loop=incomplete_agent_loop)
        spec = WorkflowSpec(
            name="incomplete",
            final_phase_id="inspect",
            phases=(WorkflowPhase(id="inspect", role="inspector"),),
            tasks=(
                WorkflowTask(
                    id="inspect_context",
                    phase_id="inspect",
                    role="inspector",
                    prompt_template="Inspect the task.",
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("failed", workflow_run.status)
        self.assertEqual("failed", workflow_run.task_results[0].status)
        self.assertIn("without a final answer", workflow_run.task_results[0].error or "")

    def test_stop_event_marks_task_failed(self) -> None:
        def stopped_agent_loop(task: str, **kwargs: object) -> list[Event]:
            return [
                user_task(1, task),
                stop(2, "max_steps_reached", {"max_steps": 1}),
            ]

        runner = SerialWorkflowRunner(agent_loop=stopped_agent_loop)
        spec = WorkflowSpec(
            name="stopped",
            final_phase_id="inspect",
            phases=(WorkflowPhase(id="inspect", role="inspector"),),
            tasks=(
                WorkflowTask(
                    id="inspect_context",
                    phase_id="inspect",
                    role="inspector",
                    prompt_template="Inspect the task.",
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("failed", workflow_run.status)
        self.assertEqual("failed", workflow_run.task_results[0].status)
        self.assertIn("max_steps_reached", workflow_run.task_results[0].error or "")

    def test_missing_final_phase_id_fails_before_running_tasks(self) -> None:
        agent_loop = RecordingAgentLoop()
        runner = SerialWorkflowRunner(agent_loop=agent_loop)
        spec = WorkflowSpec(
            name="missing_handoff",
            phases=(WorkflowPhase(id="inspect", role="inspector"),),
            tasks=(
                WorkflowTask(
                    id="inspect_context",
                    phase_id="inspect",
                    role="inspector",
                    prompt_template="Inspect.",
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("failed", workflow_run.status)
        self.assertIsNone(workflow_run.final_answer)
        self.assertEqual("workflow", workflow_run.phase_results[0].phase_id)
        self.assertIn("final_phase_id", workflow_run.phase_results[0].error or "")
        self.assertEqual([], agent_loop.prompts)

    def test_final_phase_must_be_last_in_serial_workflow(self) -> None:
        agent_loop = RecordingAgentLoop()
        runner = SerialWorkflowRunner(agent_loop=agent_loop)
        spec = WorkflowSpec(
            name="bad_final_order",
            final_phase_id="inspect",
            phases=(
                WorkflowPhase(id="inspect", role="inspector"),
                WorkflowPhase(id="handoff", role="handoff"),
            ),
            tasks=(
                WorkflowTask(
                    id="inspect_context",
                    phase_id="inspect",
                    role="inspector",
                    prompt_template="Inspect.",
                ),
                WorkflowTask(
                    id="handoff_summary",
                    phase_id="handoff",
                    role="handoff",
                    prompt_template="Summarize.",
                    depends_on=("inspect_context",),
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("failed", workflow_run.status)
        self.assertIn("last phase", workflow_run.phase_results[0].error or "")
        self.assertEqual([], agent_loop.prompts)

    def test_final_phase_must_have_one_task_without_final_task_id(self) -> None:
        agent_loop = RecordingAgentLoop()
        runner = SerialWorkflowRunner(agent_loop=agent_loop)
        spec = WorkflowSpec(
            name="multi_task_final",
            final_phase_id="handoff",
            phases=(WorkflowPhase(id="handoff", role="handoff"),),
            tasks=(
                WorkflowTask(
                    id="summarize_changes",
                    phase_id="handoff",
                    role="handoff",
                    prompt_template="Summarize changes.",
                ),
                WorkflowTask(
                    id="summarize_tests",
                    phase_id="handoff",
                    role="handoff",
                    prompt_template="Summarize tests.",
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("failed", workflow_run.status)
        self.assertIn("final_phase_id must contain exactly one task", workflow_run.phase_results[0].error or "")
        self.assertEqual([], agent_loop.prompts)

    def test_task_with_unknown_phase_fails_validation(self) -> None:
        runner = SerialWorkflowRunner(agent_loop=RecordingAgentLoop())
        spec = WorkflowSpec(
            name="unknown_phase",
            final_phase_id="handoff",
            phases=(WorkflowPhase(id="handoff", role="handoff"),),
            tasks=(
                WorkflowTask(
                    id="orphan",
                    phase_id="inspect",
                    role="inspector",
                    prompt_template="Inspect.",
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("failed", workflow_run.status)
        self.assertIn("unknown phase_id", workflow_run.phase_results[0].error or "")


if __name__ == "__main__":
    unittest.main()
