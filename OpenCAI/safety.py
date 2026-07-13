"""Minimal safety policy for OpenCAI tool calls."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from OpenCAI.tools import ToolSpec
from OpenCAI.tooling.path_utils import resolve_child_path


class PermissionProfile(Enum):
    READ_ONLY = "read-only"
    ASK_APPROVAL = "ask-approval"
    APPROVE_SAFE = "approve-safe"
    FULL_ACCESS = "full-access"

    @classmethod
    def from_cli_value(cls, value: str) -> PermissionProfile:
        normalized = value.strip().lower()
        for profile in cls:
            if profile.value == normalized:
                return profile
        raise ValueError(f"Unknown permission profile: {value}")


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str | None = None


@dataclass(frozen=True)
class SafetyPolicy:
    profile: PermissionProfile = PermissionProfile.APPROVE_SAFE

    def check_tool_call(
        self,
        spec: ToolSpec,
        arguments: dict[str, Any],
        cwd: Path,
    ) -> PolicyDecision:
        if spec.name in COMMAND_TOOL_NAMES:
            return self._check_command(arguments, cwd)

        if not spec.read_only and not self._allows_write():
            return PolicyDecision(
                False,
                _approval_required_reason("write operations"),
            )

        paths = _path_arguments(spec.name, arguments)
        if not paths:
            return PolicyDecision(True)

        for path in paths:
            decision = _check_path_inside_cwd(path, cwd)
            if not decision.allowed:
                return decision
        return PolicyDecision(True)

    def _check_command(self, arguments: dict[str, Any], cwd: Path) -> PolicyDecision:
        if not self._allows_command():
            return PolicyDecision(
                False,
                _approval_required_reason("command execution"),
            )

        cwd_decision = _check_cwd_argument(arguments, cwd=cwd)
        if not cwd_decision.allowed:
            return cwd_decision

        command = arguments.get("command")
        if not isinstance(command, str):
            return PolicyDecision(True)

        return _check_dangerous_command(command)

    def check_user_command(self, command: str) -> PolicyDecision:
        return _check_dangerous_command(command)

    def _allows_write(self) -> bool:
        return self.profile in {
            PermissionProfile.APPROVE_SAFE,
            PermissionProfile.FULL_ACCESS,
        }

    def _allows_command(self) -> bool:
        return self.profile in {
            PermissionProfile.APPROVE_SAFE,
            PermissionProfile.FULL_ACCESS,
        }


def _approval_required_reason(operation: str) -> str:
    return (
        f"Approval required for {operation}, but interactive approval is not implemented yet. "
        "Use --permission approve-safe or --permission full-access to permit it."
    )


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


COMMAND_TOOL_NAMES = {
    "run_command",
    "start_command",
    "read_command",
    "write_stdin",
    "stop_command",
}


def _path_arguments(tool_name: str, arguments: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    path = arguments.get("path")
    if isinstance(path, str) and path:
        paths.append(path)
    source = arguments.get("source")
    if isinstance(source, str) and source:
        paths.append(source)
    destination = arguments.get("destination")
    if isinstance(destination, str) and destination:
        paths.append(destination)
    if tool_name in {"search_files", "list_files", "glob_files"} and not paths:
        paths.append(".")
    return paths


def _check_path_inside_cwd(path: str, cwd: Path) -> PolicyDecision:
    if resolve_child_path(cwd, path) is None:
        return PolicyDecision(False, f"Path escapes workspace: {path}")

    return PolicyDecision(True)


def _check_cwd_argument(arguments: dict[str, Any], cwd: Path) -> PolicyDecision:
    path = arguments.get("cwd")
    if not isinstance(path, str) or not path:
        return PolicyDecision(True)
    return _check_path_inside_cwd(path, cwd)


def _check_dangerous_command(command: str) -> PolicyDecision:
    normalized = command.lower()
    for blocked in DANGEROUS_COMMAND_PATTERNS:
        if blocked in normalized:
            return PolicyDecision(False, f"Blocked dangerous command: {blocked}")

    return PolicyDecision(True)
