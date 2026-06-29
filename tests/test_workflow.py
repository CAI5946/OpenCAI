import unittest

from OpenCAI.events import Event, final_answer, make_event, user_task
from OpenCAI.workflow import (
    SerialWorkflowRunner,
    WorkflowPhase,
    WorkflowSpec,
    build_inspect_handoff_workflow,
    render_workflow_plan,
)


class RecordingAgentLoop:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, task: str, **kwargs: object) -> list[Event]:
        self.prompts.append(task)
        phase_number = len(self.prompts)
        return [
            user_task(1, task),
            final_answer(2, f"phase {phase_number} complete"),
        ]


class WorkflowTest(unittest.TestCase):
    def test_render_workflow_plan_shows_final_phase_and_dependencies(self) -> None:
        spec = build_inspect_handoff_workflow()

        plan = render_workflow_plan(spec)

        self.assertIn("Workflow: inspect_handoff", plan)
        self.assertIn("Final phase: handoff", plan)
        self.assertIn("1. inspect", plan)
        self.assertIn("depends_on: none", plan)
        self.assertIn("2. handoff (final)", plan)
        self.assertIn("depends_on: inspect", plan)

    def test_builtin_inspect_handoff_workflow_returns_final_answer(self) -> None:
        agent_loop = RecordingAgentLoop()
        runner = SerialWorkflowRunner(agent_loop=agent_loop)
        spec = build_inspect_handoff_workflow()

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("inspect_handoff", spec.name)
        self.assertEqual("handoff", spec.final_phase_id)
        self.assertEqual("passed", workflow_run.status)
        self.assertEqual("phase 2 complete", workflow_run.final_answer)
        self.assertEqual(["inspect", "handoff"], [r.phase_id for r in workflow_run.phase_results])
        self.assertIn("[inspect] passed: phase 1 complete", agent_loop.prompts[1])

    def test_runner_executes_two_phases_and_saves_results(self) -> None:
        agent_loop = RecordingAgentLoop()
        runner = SerialWorkflowRunner(agent_loop=agent_loop)
        spec = WorkflowSpec(
            name="inspect_summarize",
            final_phase_id="summarize",
            phases=(
                WorkflowPhase(
                    id="inspect",
                    role="inspector",
                    prompt_template="Inspect the task.",
                ),
                WorkflowPhase(
                    id="summarize",
                    role="summarizer",
                    prompt_template="Summarize the inspection.",
                    depends_on=("inspect",),
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("passed", workflow_run.status)
        self.assertEqual("phase 2 complete", workflow_run.final_answer)
        self.assertEqual(["inspect", "summarize"], [r.phase_id for r in workflow_run.phase_results])
        self.assertEqual(["passed", "passed"], [r.status for r in workflow_run.phase_results])
        self.assertEqual("phase 1 complete", workflow_run.phase_results[0].final_answer)
        self.assertEqual("phase 2 complete", workflow_run.phase_results[1].final_answer)
        self.assertIn("[inspect] passed: phase 1 complete", agent_loop.prompts[1])

    def test_phase_without_passed_dependency_is_skipped_and_workflow_fails(self) -> None:
        agent_loop = RecordingAgentLoop()
        runner = SerialWorkflowRunner(agent_loop=agent_loop)
        spec = WorkflowSpec(
            name="bad_dependency",
            final_phase_id="summarize",
            phases=(
                WorkflowPhase(
                    id="summarize",
                    role="summarizer",
                    prompt_template="Summarize missing work.",
                    depends_on=("inspect",),
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("failed", workflow_run.status)
        self.assertEqual("skipped", workflow_run.phase_results[0].status)
        self.assertIn("inspect", workflow_run.phase_results[0].error)
        self.assertEqual([], agent_loop.prompts)

    def test_error_event_marks_phase_and_workflow_failed(self) -> None:
        def failing_agent_loop(task: str, **kwargs: object) -> list[Event]:
            return [
                user_task(1, task),
                make_event("error", 2, "LLM adapter failed"),
            ]

        runner = SerialWorkflowRunner(agent_loop=failing_agent_loop)
        spec = WorkflowSpec(
            name="failing_workflow",
            phases=(
                WorkflowPhase(
                    id="execute",
                    role="executor",
                    prompt_template="Execute the task.",
                ),
                WorkflowPhase(
                    id="handoff",
                    role="handoff",
                    prompt_template="Report the task.",
                    depends_on=("execute",),
                ),
            ),
        )

        workflow_run = runner.run(spec, "Fix bug")

        self.assertEqual("failed", workflow_run.status)
        self.assertEqual(1, len(workflow_run.phase_results))
        self.assertEqual("failed", workflow_run.phase_results[0].status)
        self.assertEqual("LLM adapter failed", workflow_run.phase_results[0].error)

    def test_phase_without_final_answer_fails(self) -> None:
        def incomplete_agent_loop(task: str, **kwargs: object) -> list[Event]:
            return [user_task(1, task)]

        runner = SerialWorkflowRunner(agent_loop=incomplete_agent_loop)
        spec = WorkflowSpec(
            name="incomplete",
            final_phase_id="inspect",
            phases=(
                WorkflowPhase(
                    id="inspect",
                    role="inspector",
                    prompt_template="Inspect the task.",
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("failed", workflow_run.status)
        self.assertEqual("failed", workflow_run.phase_results[0].status)
        self.assertIn("without a final answer", workflow_run.phase_results[0].error)

    def test_missing_final_phase_id_fails_before_running_phases(self) -> None:
        agent_loop = RecordingAgentLoop()
        runner = SerialWorkflowRunner(agent_loop=agent_loop)
        spec = WorkflowSpec(
            name="missing_handoff",
            phases=(
                WorkflowPhase(
                    id="inspect",
                    role="inspector",
                    prompt_template="Inspect the task.",
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("failed", workflow_run.status)
        self.assertIsNone(workflow_run.final_answer)
        self.assertEqual("workflow", workflow_run.phase_results[0].phase_id)
        self.assertIn("final_phase_id", workflow_run.phase_results[0].error)
        self.assertEqual([], agent_loop.prompts)

    def test_final_phase_must_be_last_in_serial_workflow(self) -> None:
        agent_loop = RecordingAgentLoop()
        runner = SerialWorkflowRunner(agent_loop=agent_loop)
        spec = WorkflowSpec(
            name="bad_final_order",
            final_phase_id="inspect",
            phases=(
                WorkflowPhase(
                    id="inspect",
                    role="inspector",
                    prompt_template="Inspect the task.",
                ),
                WorkflowPhase(
                    id="summarize",
                    role="summarizer",
                    prompt_template="Summarize the task.",
                    depends_on=("inspect",),
                ),
            ),
        )

        workflow_run = runner.run(spec, "Read README")

        self.assertEqual("failed", workflow_run.status)
        self.assertIn("last phase", workflow_run.phase_results[0].error)
        self.assertEqual([], agent_loop.prompts)


if __name__ == "__main__":
    unittest.main()
