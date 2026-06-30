from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS_DIR = PROJECT_ROOT / "benchmarks" / "tasks"
DEFAULT_RUNS_DIR = PROJECT_ROOT / "benchmarks" / "runs"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "benchmarks" / "results"


@dataclass(frozen=True)
class BenchmarkTask:
    id: str
    title: str
    fixture: Path
    task: str
    verification_command: str
    max_steps: int
    tags: tuple[str, ...]


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Task field must be a non-empty string: {key}")
    return value


def load_task(path: Path) -> BenchmarkTask:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Task file must contain a JSON object: {path}")

    tags = data.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ValueError("Task field must be a list of strings: tags")

    max_steps = data.get("max_steps", 8)
    if not isinstance(max_steps, int) or max_steps < 1:
        raise ValueError("Task field must be a positive integer: max_steps")

    return BenchmarkTask(
        id=_require_string(data, "id"),
        title=_require_string(data, "title"),
        fixture=Path(_require_string(data, "fixture")),
        task=_require_string(data, "task"),
        verification_command=_require_string(data, "verification_command"),
        max_steps=max_steps,
        tags=tuple(tags),
    )


def load_tasks(tasks_dir: Path = DEFAULT_TASKS_DIR) -> list[BenchmarkTask]:
    return [load_task(path) for path in sorted(tasks_dir.glob("*.json"))]


def prepare_workspace(task: BenchmarkTask, runs_dir: Path) -> Path:
    source = task.fixture
    if not source.is_absolute():
        source = PROJECT_ROOT / "benchmarks" / source
    if not source.exists() or not source.is_dir():
        raise FileNotFoundError(f"Fixture directory does not exist: {source}")

    workspace = runs_dir / task.id / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, workspace)
    return workspace


def _run_command(command: list[str] | str, cwd: Path, timeout_seconds: int) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=isinstance(command, str),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return CommandResult(
            exit_code=124,
            stdout=stdout,
            stderr=f"Command timed out after {timeout_seconds} seconds.\n{stderr}",
        )

    return CommandResult(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_verification(command: str, workspace: Path, timeout_seconds: int = 60) -> CommandResult:
    return _run_command(command, workspace, timeout_seconds)


def snapshot_files(workspace: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in workspace.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            relative = str(path.relative_to(workspace))
            try:
                snapshot[relative] = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                snapshot[relative] = "<binary>"
    return snapshot


def changed_files(before: dict[str, str], after: dict[str, str]) -> list[str]:
    paths = sorted(set(before) | set(after))
    return [path for path in paths if before.get(path) != after.get(path)]


def build_agent_command(task: BenchmarkTask, adapter: str, workspace: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "OpenCAI",
        "--cwd",
        str(workspace),
        "--adapter",
        adapter,
        "--allow-write",
        "--allow-command",
        "--max-steps",
        str(task.max_steps),
        "--task",
        task.task,
    ]


def build_result(
    task_id: str,
    workspace: Path,
    agent_exit_code: int,
    agent_stdout: str,
    agent_stderr: str,
    verification_exit_code: int,
    verification_stdout: str,
    verification_stderr: str,
    changed_files: list[str],
) -> dict[str, Any]:
    status = "passed" if agent_exit_code == 0 and verification_exit_code == 0 else "failed"
    return {
        "task_id": task_id,
        "status": status,
        "workspace": str(workspace),
        "agent": {
            "exit_code": agent_exit_code,
            "stdout": agent_stdout,
            "stderr": agent_stderr,
        },
        "verification": {
            "exit_code": verification_exit_code,
            "stdout": verification_stdout,
            "stderr": verification_stderr,
        },
        "changed_files": changed_files,
    }


def run_task(task: BenchmarkTask, runs_dir: Path, adapter: str, timeout_seconds: int) -> dict[str, Any]:
    workspace = prepare_workspace(task, runs_dir)
    before = snapshot_files(workspace)
    agent = _run_command(build_agent_command(task, adapter, workspace), PROJECT_ROOT, timeout_seconds)
    verification = run_verification(task.verification_command, workspace, timeout_seconds)
    after = snapshot_files(workspace)
    return build_result(
        task_id=task.id,
        workspace=workspace,
        agent_exit_code=agent.exit_code,
        agent_stdout=agent.stdout,
        agent_stderr=agent.stderr,
        verification_exit_code=verification.exit_code,
        verification_stdout=verification.stdout,
        verification_stderr=verification.stderr,
        changed_files=changed_files(before, after),
    )


def write_report(results: list[dict[str, Any]], results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = results_dir / f"benchmark-{timestamp}.json"
    summary = {
        "total": len(results),
        "passed": sum(1 for result in results if result["status"] == "passed"),
        "failed": sum(1 for result in results if result["status"] == "failed"),
    }
    report_path.write_text(
        json.dumps({"summary": summary, "results": results}, indent=2),
        encoding="utf-8",
    )
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OpenCAI local benchmark tasks.")
    parser.add_argument("--task", default="all", help="Task id to run, or 'all'.")
    parser.add_argument("--adapter", choices=["fake", "gemini"], default="fake")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per command in seconds.")
    parser.add_argument("--tasks-dir", type=Path, default=DEFAULT_TASKS_DIR)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tasks = load_tasks(args.tasks_dir)
    if args.task != "all":
        tasks = [task for task in tasks if task.id == args.task]
    if not tasks:
        print(f"No benchmark tasks matched: {args.task}")
        return 1

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    runs_dir = args.runs_dir / run_id
    results = [run_task(task, runs_dir, args.adapter, args.timeout) for task in tasks]
    report_path = write_report(results, args.results_dir)

    passed = sum(1 for result in results if result["status"] == "passed")
    print(f"Benchmark complete: {passed}/{len(results)} passed")
    print(f"Report: {report_path}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
