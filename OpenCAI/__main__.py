from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path

from OpenCAI.agent_loop import run_agent_loop
from OpenCAI.composer import RuntimeCommandInput, ShellInput, parse_user_input
from OpenCAI.llm_adapter import FakeLLMAdapter, GeminiAdapter, LLMAdapter, LLMAdapterError
from OpenCAI.runtime_commands import handle_runtime_command
from OpenCAI.safety import SafetyPolicy
from OpenCAI.shell_mode import run_user_shell_command
from OpenCAI.tui import ask_task, render_startup, render_transcript


DEFAULT_TASK = "Fix the failing toy project test"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class RuntimeSession:
    cwd: Path
    adapter_name: str
    adapter: LLMAdapter
    max_steps: int
    allow_write: bool
    allow_command: bool
    turn_count: int = 0
    task_history: list[str] = field(default_factory=list)

    def build_policy(self) -> SafetyPolicy:
        return SafetyPolicy(
            allow_write=self.allow_write,
            allow_command=self.allow_command,
        )


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
        description="Interactive runtime for the OpenCAI learning agent.",
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
    parser.add_argument(
        "--max-steps",
        type=int,
        default=3,
        help="Maximum model/tool loop steps for one task.",
    )
    parser.add_argument(
        "--allow-write",
        action="store_true",
        help="Permit write tools such as apply_patch for this process.",
    )
    parser.add_argument(
        "--allow-command",
        action="store_true",
        help="Permit command execution for this process. Obvious destructive commands are still blocked.",
    )
    return parser


def run_once(
    task: str,
    cwd: Path,
    adapter: LLMAdapter,
    max_steps: int,
    policy: SafetyPolicy,
) -> None:
    render_transcript(
        run_agent_loop(task, cwd=cwd, adapter=adapter, max_steps=max_steps, policy=policy)
    )


def run_interactive(session: RuntimeSession, api_key: str | None) -> int:
    while True:
        label = f"Task {session.turn_count + 1}"
        raw_input = ask_task(label=label)
        parsed_input = parse_user_input(raw_input)
        if parsed_input is None:
            continue
        if isinstance(parsed_input, RuntimeCommandInput):
            if handle_runtime_command(session, parsed_input.text, api_key, build_adapter):
                return 0
            continue
        if isinstance(parsed_input, ShellInput):
            render_transcript(
                run_user_shell_command(
                    parsed_input.command,
                    session.cwd,
                    session.build_policy(),
                )
            )
            continue

        task = parsed_input.text
        session.task_history.append(task)
        session.turn_count += 1
        run_once(
            task,
            session.cwd,
            session.adapter,
            session.max_steps,
            session.build_policy(),
        )


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
        print(f"model: {args.adapter}")
        print(f"max_steps: {args.max_steps}")
        print(f"allow_write: {args.allow_write}")
        print(f"allow_command: {args.allow_command}")
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

    policy = SafetyPolicy(allow_write=args.allow_write, allow_command=args.allow_command)

    if args.task:
        run_once(args.task, cwd, adapter, args.max_steps, policy)
        return 0

    session = RuntimeSession(
        cwd=cwd,
        adapter_name=args.adapter,
        adapter=adapter,
        max_steps=args.max_steps,
        allow_write=args.allow_write,
        allow_command=args.allow_command,
    )
    return run_interactive(session, os.environ.get("GEMINI_API_KEY"))


if __name__ == "__main__":
    raise SystemExit(main())
