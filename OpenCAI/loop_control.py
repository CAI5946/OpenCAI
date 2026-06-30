"""Loop budget and stop-state helpers for the OpenCAI agent loop."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StopReason(str, Enum):
    MAX_STEPS_REACHED = "max_steps_reached"
    REPEATED_ACTION = "repeated_action"
    CONSECUTIVE_TOOL_FAILURES = "consecutive_tool_failures"


@dataclass(frozen=True)
class LoopBudget:
    max_model_turns: int = 8
    max_repeated_tool_calls: int = 2
    max_consecutive_tool_failures: int = 3


@dataclass
class LoopState:
    model_turns: int = 0
    consecutive_tool_failures: int = 0
    tool_call_history: list[tuple[str, str]] = field(default_factory=list)
    last_verification_ok: bool | None = None


def tool_call_signature(tool_name: str, arguments: dict[str, Any]) -> tuple[str, str]:
    try:
        serialized_arguments = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
    except TypeError:
        serialized_arguments = repr(sorted(arguments.items()))
    return (tool_name, serialized_arguments)


def consecutive_repeated_call_count(
    history: list[tuple[str, str]],
    signature: tuple[str, str],
) -> int:
    count = 0
    for item in reversed(history):
        if item != signature:
            break
        count += 1
    return count
