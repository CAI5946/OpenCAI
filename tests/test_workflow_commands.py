from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from OpenCAI.llm_adapter import FakeLLMAdapter, LLMAdapter
from OpenCAI.safety import PermissionProfile, SafetyPolicy
from OpenCAI.workflow import build_inspect_handoff_workflow_plan
from OpenCAI.workflow.clarify import ClarifyResult, ClarifyRun
from OpenCAI.workflow.commands import handle_workflow_command


@dataclass
class DummySession:
    cwd: Path
    adapter: LLMAdapter | None = None
    max_steps: int = 8
    permission_profile: PermissionProfile = PermissionProfile.APPROVE_SAFE

    def build_policy(self) -> SafetyPolicy:
        return SafetyPolicy(profile=self.permission_profile)


class WorkflowCommandTests(unittest.TestCase):
    def test_workflow_command_without_task_stops_before_runner(self) -> None:
        session = DummySession(cwd=Path.cwd(), adapter=FakeLLMAdapter())
        output = io.StringIO()

        with redirect_stdout(output), patch("OpenCAI.workflow.commands.SerialWorkflowRunner") as runner:
            handle_workflow_command(session, "")

        self.assertIn("No task for workflow. Usage: /workflow TASK", output.getvalue())
        runner.assert_not_called()

    def test_workflow_command_runs_builtin_workflow(self) -> None:
        session = DummySession(cwd=Path.cwd(), adapter=FakeLLMAdapter())
        output = io.StringIO()

        with redirect_stdout(output):
            handle_workflow_command(session, "Read README")

        text = output.getvalue()
        self.assertIn("• Clarify status: complete", text)
        self.assertIn("• Workflow task: Read README", text)
        self.assertIn("• Workflow: inspect_handoff", text)
        self.assertIn("• Workflow status: passed", text)
        self.assertIn("Fake loop observed README.md and stopped.", text)

    def test_workflow_command_compiles_spec_before_running(self) -> None:
        session = DummySession(cwd=Path.cwd(), adapter=FakeLLMAdapter())

        with patch("OpenCAI.workflow.commands.compile_workflow") as compile_workflow:
            compile_workflow.return_value = build_inspect_handoff_workflow_plan()
            with redirect_stdout(io.StringIO()):
                handle_workflow_command(session, "Read README")

        self.assertEqual(compile_workflow.call_args.args[0], "Read README")
        self.assertIsInstance(compile_workflow.call_args.kwargs["clarify_result"], ClarifyResult)

    def test_workflow_command_stops_when_clarify_blocks(self) -> None:
        session = DummySession(cwd=Path.cwd(), adapter=FakeLLMAdapter())
        blocked_run = ClarifyRun(
            original_task="Read README",
            status="blocked",
            repo_context_summary="repo",
            blocked_reason="Need human decision.",
        )
        output = io.StringIO()

        with (
            patch("OpenCAI.workflow.commands.run_clarify_for_session", return_value=blocked_run),
            patch("OpenCAI.workflow.commands.compile_workflow") as compile_workflow,
            patch("OpenCAI.workflow.commands.SerialWorkflowRunner") as runner,
            redirect_stdout(output),
        ):
            handle_workflow_command(session, "Read README")

        self.assertIn("• Clarify status: blocked", output.getvalue())
        self.assertIn("Need human decision.", output.getvalue())
        compile_workflow.assert_not_called()
        runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
