from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from OpenCAI.llm_adapter import FakeLLMAdapter, LLMAdapter
from OpenCAI.safety import PermissionProfile, SafetyPolicy
from OpenCAI.workflow_commands import handle_workflow_command


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

        with redirect_stdout(output), patch("OpenCAI.workflow_commands.SerialWorkflowRunner") as runner:
            handle_workflow_command(session, "")

        self.assertIn("No task for workflow. Usage: /workflow TASK", output.getvalue())
        runner.assert_not_called()

    def test_workflow_command_runs_builtin_workflow(self) -> None:
        session = DummySession(cwd=Path.cwd(), adapter=FakeLLMAdapter())
        output = io.StringIO()

        with redirect_stdout(output):
            handle_workflow_command(session, "Read README")

        text = output.getvalue()
        self.assertIn("• Workflow task: Read README", text)
        self.assertIn("• Workflow: inspect_handoff", text)
        self.assertIn("• Workflow status: passed", text)
        self.assertIn("Fake loop observed README.md and stopped.", text)


if __name__ == "__main__":
    unittest.main()
