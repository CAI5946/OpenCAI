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
    run_task,
    run_verification,
    snapshot_files,
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
                        "category": "bugfix",
                        "fixture": "fixtures/sample",
                        "task": "Fix the sample.",
                        "verification_command": "python -m unittest",
                        "expected_changed_files": ["app.py"],
                        "primary_capability": "verify_first",
                        "failure_tags": ["verification_not_run", "patch_failed"],
                        "max_steps": 8,
                        "tags": ["micro", "bugfix"],
                    }
                ),
                encoding="utf-8",
            )

            task = load_task(task_path)

        self.assertEqual("sample", task.id)
        self.assertEqual("Sample task", task.title)
        self.assertEqual("bugfix", task.category)
        self.assertEqual(Path("fixtures/sample"), task.fixture)
        self.assertEqual("Fix the sample.", task.task)
        self.assertEqual("python -m unittest", task.verification_command)
        self.assertEqual(("app.py",), task.expected_changed_files)
        self.assertEqual("verify_first", task.primary_capability)
        self.assertEqual(("verification_not_run", "patch_failed"), task.failure_tags)
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
                category="smoke",
                fixture=fixture,
                task="Read app.py",
                verification_command="python -m py_compile app.py",
                expected_changed_files=("app.py",),
                primary_capability="workspace_isolation",
                failure_tags=(),
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

    def test_snapshot_files_uses_posix_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            nested = workspace / "package"
            nested.mkdir()
            (nested / "module.py").write_text("VALUE = 1\n", encoding="utf-8")

            snapshot = snapshot_files(workspace)

        self.assertIn("package/module.py", snapshot)

    def test_snapshot_files_ignores_runtime_cache_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            cache = workspace / ".pytest_cache" / "v" / "cache"
            cache.mkdir(parents=True)
            (cache / "nodeids").write_text("[]\n", encoding="utf-8")

            snapshot = snapshot_files(workspace)

        self.assertEqual({}, snapshot)

    def test_build_result_marks_passed_only_when_diagnostics_pass(self) -> None:
        result = build_result(
            task=BenchmarkTask(
                id="sample",
                title="Sample",
                category="bugfix",
                fixture=Path("fixtures/sample"),
                task="Fix sample.",
                verification_command="python -m unittest",
                expected_changed_files=("app.py",),
                primary_capability="verify_first",
                failure_tags=("patch_failed",),
                max_steps=8,
                tags=("micro",),
            ),
            workspace=Path("runs/sample/workspace"),
            initial_verification_exit_code=1,
            initial_verification_stdout="failing test",
            initial_verification_stderr="",
            agent_exit_code=0,
            agent_stdout="agent ok",
            agent_stderr="",
            final_verification_exit_code=0,
            final_verification_stdout="tests ok",
            final_verification_stderr="",
            changed_files=["app.py"],
        )

        self.assertEqual("passed", result["status"])
        self.assertEqual("sample", result["task_id"])
        self.assertEqual("bugfix", result["category"])
        self.assertEqual("verify_first", result["primary_capability"])
        self.assertEqual(["app.py"], result["changed_files"])
        self.assertEqual(["app.py"], result["expected_changed_files"])

    def test_build_result_marks_invalid_when_initial_verification_passes(self) -> None:
        result = build_result(
            task=BenchmarkTask(
                id="sample",
                title="Sample",
                category="bugfix",
                fixture=Path("fixtures/sample"),
                task="Fix sample.",
                verification_command="python -m unittest",
                expected_changed_files=("app.py",),
                primary_capability="verify_first",
                failure_tags=("invalid_fixture",),
                max_steps=8,
                tags=("micro",),
            ),
            workspace=Path("runs/sample/workspace"),
            initial_verification_exit_code=0,
            initial_verification_stdout="already passing",
            initial_verification_stderr="",
            agent_exit_code=0,
            agent_stdout="agent ok",
            agent_stderr="",
            final_verification_exit_code=0,
            final_verification_stdout="tests ok",
            final_verification_stderr="",
            changed_files=["app.py"],
        )

        self.assertEqual("invalid_task", result["status"])

    def test_build_result_marks_failed_when_changed_files_do_not_match_expected(self) -> None:
        result = build_result(
            task=BenchmarkTask(
                id="sample",
                title="Sample",
                category="bugfix",
                fixture=Path("fixtures/sample"),
                task="Fix sample.",
                verification_command="python -m unittest",
                expected_changed_files=("app.py",),
                primary_capability="verify_first",
                failure_tags=("wrong_changed_files",),
                max_steps=8,
                tags=("micro",),
            ),
            workspace=Path("runs/sample/workspace"),
            initial_verification_exit_code=1,
            initial_verification_stdout="failing test",
            initial_verification_stderr="",
            agent_exit_code=0,
            agent_stdout="agent ok",
            agent_stderr="",
            final_verification_exit_code=0,
            final_verification_stdout="tests ok",
            final_verification_stderr="",
            changed_files=["app.py", "test_app.py"],
        )

        self.assertEqual("failed_changed_files", result["status"])

    def test_run_task_records_initial_verification_before_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fixture = root / "fixture"
            fixture.mkdir()
            (fixture / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            task = BenchmarkTask(
                id="invalid_fixture",
                title="Invalid fixture",
                category="bugfix",
                fixture=fixture,
                task="This should not need a fix.",
                verification_command="python -m py_compile app.py",
                expected_changed_files=("app.py",),
                primary_capability="verify_first",
                failure_tags=("invalid_fixture",),
                max_steps=3,
                tags=(),
            )

            result = run_task(task, root / "runs", "fake", timeout_seconds=10)

        self.assertEqual("invalid_task", result["status"])
        self.assertEqual(0, result["initial_verification"]["exit_code"])

    def test_build_agent_command_runs_opencai_inside_task_workspace(self) -> None:
        task = BenchmarkTask(
            id="workspace_task",
            title="Workspace task",
            category="smoke",
            fixture=Path("fixtures/workspace_task"),
            task="Fix this workspace.",
            verification_command="python -m unittest",
            expected_changed_files=("app.py",),
            primary_capability="workspace_isolation",
            failure_tags=(),
            max_steps=5,
            tags=(),
        )

        command = build_agent_command(task, "fake", Path("runs/workspace_task/workspace"))

        self.assertIn("--cwd", command)
        self.assertIn(str(Path("runs/workspace_task/workspace")), command)


if __name__ == "__main__":
    unittest.main()
