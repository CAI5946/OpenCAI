"""Stable contracts for OpenCAI tools."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypedDict


class ToolCall(TypedDict):
    tool_name: str
    arguments: dict[str, Any]


class ToolResult(TypedDict):
    tool_name: str
    ok: bool
    result: dict[str, Any]
    error: str | None


ToolFunction = Callable[[dict[str, Any], Path], ToolResult]


class ToolExposure(str, Enum):
    DIRECT = "direct"
    DEFERRED = "deferred"
    HIDDEN = "hidden"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    read_only: bool
    function: ToolFunction
    category: str = "general"
    exposure: ToolExposure = ToolExposure.DIRECT


def tool_result(
    tool_name: str,
    ok: bool,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> ToolResult:
    return {
        "tool_name": tool_name,
        "ok": ok,
        "result": result or {},
        "error": error,
    }
