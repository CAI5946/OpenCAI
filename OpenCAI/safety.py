"""Minimal safety policy for OpenCAI tool calls."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from OpenCAI.tools import ToolSpec


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str | None = None


@dataclass(frozen=True)
class SafetyPolicy:
    allow_write: bool = False
    allow_command: bool = False

    def check_tool_call(
        self,
        spec: ToolSpec,
        arguments: dict[str, Any],
        cwd: Path,
    ) -> PolicyDecision:
        if spec.name == "run_command":
            return self._check_command(arguments)

        if not spec.read_only and not self.allow_write:
            return PolicyDecision(
                False,
                "Write operations are disabled. Re-run with --allow-write to permit writes.",
            )

        path = _path_argument(spec.name, arguments)
        if path is None:
            return PolicyDecision(True)

        return _check_path_inside_cwd(path, cwd)

    def _check_command(self, arguments: dict[str, Any]) -> PolicyDecision:
        if not self.allow_command:
            return PolicyDecision(
                False,
                "Command execution is disabled. Re-run with --allow-command to permit commands.",
            )

        command = arguments.get("command")
        if not isinstance(command, str):
            return PolicyDecision(True)

        normalized = command.lower()
        for blocked in DANGEROUS_COMMAND_PATTERNS:
            if blocked in normalized:
                return PolicyDecision(False, f"Blocked dangerous command: {blocked}")

        return PolicyDecision(True)


DANGEROUS_COMMAND_PATTERNS = (
    "rm -rf",
    "remove-item",
    "del /s",
    "rmdir /s",
    "format ",
    "shutdown",
    "git reset --hard",
    "git clean -fd",
)


def _path_argument(tool_name: str, arguments: dict[str, Any]) -> str | None:
    path = arguments.get("path")
    if isinstance(path, str) and path:
        return path
    if tool_name == "search_files":
        return "."
    return None


def _check_path_inside_cwd(path: str, cwd: Path) -> PolicyDecision:
    resolved_cwd = cwd.resolve()
    resolved_target = (resolved_cwd / path).resolve()
    try:
        resolved_target.relative_to(resolved_cwd)
    except ValueError:
        return PolicyDecision(False, f"Path escapes workspace: {path}")

    return PolicyDecision(True)
