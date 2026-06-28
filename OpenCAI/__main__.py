from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path

from OpenCAI.agent_loop import run_agent_loop
from OpenCAI.llm_adapter import FakeLLMAdapter, GeminiAdapter, LLMAdapter, LLMAdapterError
from OpenCAI.safety import SafetyPolicy
from OpenCAI.tui import ask_task, render_startup, render_transcript


DEFAULT_TASK = "Fix the failing toy project test"
EXIT_COMMANDS = {"exit", "quit", ":q"}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ON_VALUES = {"on", "true", "yes", "1"}
OFF_VALUES = {"off", "false", "no", "0"}


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


def render_runtime_status(session: RuntimeSession) -> None:
    print("Runtime status")
    print(f"  cwd: {session.cwd}")
    print(f"  model: {session.adapter_name}")
    print(f"  max_steps: {session.max_steps}")
    print(f"  allow_write: {session.allow_write}")
    print(f"  allow_command: {session.allow_command}")
    print(f"  turns: {session.turn_count}")


def render_runtime_help() -> None:
    print("Runtime commands")
    print("  /help")
    print("  /status")
    print("  /model fake|gemini")
    print("  /max-steps N")
    print("  /allow-write on|off")
    print("  /allow-command on|off")
    print("  /exit")


def parse_on_off(value: str) -> bool | None:
    normalized = value.lower()
    if normalized in ON_VALUES:
        return True
    if normalized in OFF_VALUES:
        return False
    return None


def handle_runtime_command(session: RuntimeSession, raw_input: str, api_key: str | None) -> bool:
    parts = raw_input.split()
    command = parts[0].lower() if parts else ""

    if command == "/exit":
        return True
    if command == "/help":
        render_runtime_help()
        return False
    if command == "/status":
        render_runtime_status(session)
        return False

    if command == "/max-steps":
        if len(parts) != 2:
            print("Usage: /max-steps N")
            return False
        try:
            max_steps = int(parts[1])
        except ValueError:
            print("max_steps must be an integer.")
            return False
        if max_steps < 1:
            print("max_steps must be >= 1.")
            return False
        session.max_steps = max_steps
        print(f"max_steps: {session.max_steps}")
        return False

    if command in {"/allow-write", "/allow-command"}:
        if len(parts) != 2:
            print(f"Usage: {command} on|off")
            return False
        enabled = parse_on_off(parts[1])
        if enabled is None:
            print(f"Usage: {command} on|off")
            return False
        if command == "/allow-write":
            session.allow_write = enabled
            print(f"allow_write: {session.allow_write}")
        else:
            session.allow_command = enabled
            print(f"allow_command: {session.allow_command}")
        return False

    if command == "/model":
        if len(parts) != 2 or parts[1] not in {"fake", "gemini"}:
            print("Usage: /model fake|gemini")
            return False
        try:
            session.adapter = build_adapter(parts[1], api_key)
        except LLMAdapterError as exc:
            print(f"OpenCAI adapter error: {exc}")
            return False
        session.adapter_name = parts[1]
        print(f"model: {session.adapter_name}")
        return False

    print(f"Unknown runtime command: {raw_input}")
    print("Run /help to list commands.")
    return False


def run_interactive(session: RuntimeSession, api_key: str | None) -> int:
    while True:
        label = f"Task {session.turn_count + 1}"
        task = ask_task(DEFAULT_TASK, label=label).strip()
        if task.lower() in EXIT_COMMANDS:
            return 0
        if task.startswith("/"):
            if handle_runtime_command(session, task, api_key):
                return 0
            continue
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
