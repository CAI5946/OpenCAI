from __future__ import annotations

import argparse
import os
from pathlib import Path

from OpenCAI.agent_loop import run_fake_loop
from OpenCAI.llm_adapter import FakeLLMAdapter, LLMAdapter
from OpenCAI.tui import render_startup, render_transcript


DEFAULT_TASK = "Fix the failing toy project test"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_adapter(dry_run: bool, api_key: str | None) -> LLMAdapter:
    return FakeLLMAdapter()


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
        description="Phase 0-5 runtime for the OpenCAI learning agent.",
    )
    parser.add_argument(
        "--task",
        default=DEFAULT_TASK,
        help="Natural language task for the agent.",
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
    return parser


def main() -> int:
    load_env_file(PROJECT_ROOT / ".env")

    parser = build_parser()
    args = parser.parse_args()

    cwd = Path(args.cwd).resolve()
    adapter = build_adapter(args.dry_run, os.environ.get("GEMINI_API_KEY"))
    if args.dry_run:
        print("OpenCAI Phase runtime")
        print(f"task: {args.task}")
        print(f"cwd: {cwd}")
        print(f"verify: {args.verify or '(not set)'}")
        print(f"adapter: {type(adapter).__name__}")
        print("dry_run: true")
        return 0

    render_startup(
        mode="Phase 0-5 / Fake Agent Loop",
        status="Fake LLM adapter + read_file tool; no Gemini request and no file writes",
    )
    render_transcript(run_fake_loop(args.task, cwd=cwd, adapter=adapter))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
