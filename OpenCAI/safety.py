"""Minimal safety policy for OpenCAI tool calls."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from OpenCAI.tools import ToolSpec


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
        if spec.name == "run_command":
            return self._check_command(arguments)

        if not spec.read_only and not self._allows_write():
            return PolicyDecision(
                False,
                _approval_required_reason("write operations"),
            )

        path = _path_argument(spec.name, arguments)
        if path is None:
            return PolicyDecision(True)

        return _check_path_inside_cwd(path, cwd)

    def _check_command(self, arguments: dict[str, Any]) -> PolicyDecision:
        if not self._allows_command():
            return PolicyDecision(
                False,
                _approval_required_reason("command execution"),
            )

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


def _check_dangerous_command(command: str) -> PolicyDecision:
    normalized = command.lower()
    for blocked in DANGEROUS_COMMAND_PATTERNS:
        if blocked in normalized:
            return PolicyDecision(False, f"Blocked dangerous command: {blocked}")

    return PolicyDecision(True)
