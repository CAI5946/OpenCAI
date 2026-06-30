from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.runner import (
    BenchmarkTask,
    build_agent_command,
    build_result,
    load_task,
    prepare_workspace,
    run_verification,
)


class BenchmarkRunnerTests(unittest.TestCase):
    def test_load_task_reads_json_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "task.json"
            task_path.write_text(
                json.dumps(
                    {
                        "id": "sample",
                        "title": "Sample task",
                        "fixture": "fixtures/sample",
                        "task": "Fix the sample.",
                        "verification_command": "python -m unittest",
                        "max_steps": 8,
                        "tags": ["micro", "bugfix"],
                    }
                ),
                encoding="utf-8",
            )

            task = load_task(task_path)

        self.assertEqual("sample", task.id)
        self.assertEqual("Sample task", task.title)
        self.assertEqual(Path("fixtures/sample"), task.fixture)
        self.assertEqual("Fix the sample.", task.task)
        self.assertEqual("python -m unittest", task.verification_command)
        self.assertEqual(8, task.max_steps)
        self.assertEqual(("micro", "bugfix"), task.tags)

    def test_prepare_workspace_copies_fixture_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fixture = root / "fixture"
            fixture.mkdir()
            (fixture / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            task = BenchmarkTask(
                id="copy_fixture",
                title="Copy fixture",
                fixture=fixture,
                task="Read app.py",
                verification_command="python -m py_compile app.py",
                max_steps=3,
                tags=(),
            )

            workspace = prepare_workspace(task, root / "runs")

            self.assertTrue((workspace / "app.py").exists())
            self.assertEqual("VALUE = 1\n", (workspace / "app.py").read_text(encoding="utf-8"))

    def test_run_verification_returns_command_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            result = run_verification(
                "python -c \"print('verified')\"",
                workspace,
                timeout_seconds=10,
            )

        self.assertEqual(0, result.exit_code)
        self.assertIn("verified", result.stdout)
        self.assertEqual("", result.stderr)

    def test_run_verification_reports_timeout_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            result = run_verification(
                "python -c \"import time; time.sleep(2)\"",
                workspace,
                timeout_seconds=1,
            )

        self.assertEqual(124, result.exit_code)
        self.assertIn("Command timed out", result.stderr)

    def test_build_result_marks_passed_only_when_agent_and_verification_pass(self) -> None:
        result = build_result(
            task_id="sample",
            workspace=Path("runs/sample/workspace"),
            agent_exit_code=0,
            agent_stdout="agent ok",
            agent_stderr="",
            verification_exit_code=0,
            verification_stdout="tests ok",
            verification_stderr="",
            changed_files=["app.py"],
        )

        self.assertEqual("passed", result["status"])
        self.assertEqual("sample", result["task_id"])
        self.assertEqual(["app.py"], result["changed_files"])

    def test_build_result_marks_failed_when_verification_fails(self) -> None:
        result = build_result(
            task_id="sample",
            workspace=Path("runs/sample/workspace"),
            agent_exit_code=0,
            agent_stdout="agent ok",
            agent_stderr="",
            verification_exit_code=1,
            verification_stdout="",
            verification_stderr="test failed",
            changed_files=["app.py"],
        )

        self.assertEqual("failed", result["status"])

    def test_build_agent_command_runs_opencai_inside_task_workspace(self) -> None:
        task = BenchmarkTask(
            id="workspace_task",
            title="Workspace task",
            fixture=Path("fixtures/workspace_task"),
            task="Fix this workspace.",
            verification_command="python -m unittest",
            max_steps=5,
            tags=(),
        )

        command = build_agent_command(task, "fake", Path("runs/workspace_task/workspace"))

        self.assertIn("--cwd", command)
        self.assertIn(str(Path("runs/workspace_task/workspace")), command)


if __name__ == "__main__":
    unittest.main()
