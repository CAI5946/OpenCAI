from __future__ import annotations

import argparse
import os
from pathlib import Path


DEFAULT_TASK = "Fix the failing toy project test"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
        description="Stage 1 bootstrap for the OpenCAI learning agent.",
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
        help="Show resolved Stage 1 inputs without requiring Gemini.",
    )
    return parser


def main() -> int:
    load_env_file(PROJECT_ROOT / ".env")

    parser = build_parser()
    args = parser.parse_args()

    cwd = Path(args.cwd).resolve()
    if args.dry_run:
        print("OpenCAI Stage 1 bootstrap")
        print(f"task: {args.task}")
        print(f"cwd: {cwd}")
        print(f"verify: {args.verify or '(not set)'}")
        print("dry_run: true")
        return 0

    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "GEMINI_API_KEY is required before Stage 1 can call Gemini. "
            "No request was sent."
        )
        return 2

    print("Stage 1 Agent Loop is not implemented yet.")
    print(f"task: {args.task}")
    print(f"cwd: {cwd}")
    print(f"verify: {args.verify or '(not set)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
