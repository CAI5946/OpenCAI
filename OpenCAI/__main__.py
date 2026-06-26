from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path

from OpenCAI.agent_loop import run_fake_loop
from OpenCAI.llm_adapter import FakeLLMAdapter, GeminiAdapter, LLMAdapter, LLMAdapterError
from OpenCAI.tui import ask_task, render_startup, render_transcript


DEFAULT_TASK = "Fix the failing toy project test"
EXIT_COMMANDS = {"exit", "quit", ":q"}
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class RuntimeSession:
    turn_count: int = 0
    task_history: list[str] = field(default_factory=list)


def build_adapter(adapter_name: str, api_key: str | None) -> LLMAdapter:
    if adapter_name == "fake":
        return FakeLLMAdapter()
    if adapter_name == "gemini":
        return GeminiAdapter(api_key or "")

    raise LLMAdapterError(f"Unknown adapter: {adapter_name}")


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
        prog="opencai",
        description="Phase 8 interactive runtime for the OpenCAI learning agent.",
    )
    parser.add_argument(
        "--task",
        default="",
        help="Run one natural language task and exit. Omit to start interactive mode.",
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Workspace directory for the agent loop.",
    )
    parser.add_argument(
        "--verify",
        default="",
        help="Verification command to run after a patch.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show resolved Phase runtime inputs without running the loop.",
    )
    parser.add_argument(
        "--adapter",
        choices=["fake", "gemini"],
        default="fake",
        help="Choose the model adapter. Gemini requires google-genai and GEMINI_API_KEY.",
    )
    return parser


def run_once(task: str, cwd: Path, adapter: LLMAdapter) -> None:
    render_transcript(run_fake_loop(task, cwd=cwd, adapter=adapter))


def run_interactive(cwd: Path, adapter: LLMAdapter) -> int:
    session = RuntimeSession()
    while True:
        label = f"Task {session.turn_count + 1}"
        task = ask_task(DEFAULT_TASK, label=label).strip()
        if task.lower() in EXIT_COMMANDS:
            return 0
        session.task_history.append(task)
        session.turn_count += 1
        run_once(task, cwd, adapter)


def main() -> int:
    load_env_file(PROJECT_ROOT / ".env")

    parser = build_parser()
    args = parser.parse_args()

    cwd = Path(args.cwd).resolve()
    if args.dry_run:
        print("OpenCAI Phase runtime")
        print(f"task: {args.task or '(interactive)'}")
        print(f"cwd: {cwd}")
        print(f"verify: {args.verify or '(not set)'}")
        print(f"adapter: {args.adapter}")
        print("dry_run: true")
        return 0

    try:
        adapter = build_adapter(args.adapter, os.environ.get("GEMINI_API_KEY"))
    except LLMAdapterError as exc:
        print(f"OpenCAI adapter error: {exc}")
        return 1

    render_startup(
        mode="Phase 8 / Interactive Runtime",
        status=f"{type(adapter).__name__} + interactive task input",
    )

    if args.task:
        run_once(args.task, cwd, adapter)
        return 0

    return run_interactive(cwd, adapter)


if __name__ == "__main__":
    raise SystemExit(main())
