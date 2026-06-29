"""Minimal event helpers for the learning-first Agent transcript model."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


EventType = Literal[
    "user_task",
    "shell_command",
    "assistant_step",
    "tool_call",
    "tool_result",
    "patch_summary",
    "verification",
    "final_answer",
    "stop",
    "error",
]


class Event(TypedDict):
    type: EventType
    seq: int
    message: str
    data: dict[str, Any]


def make_event(
    event_type: EventType,
    seq: int,
    message: str,
    data: dict[str, Any] | None = None,
) -> Event:
    return {
        "type": event_type,
        "seq": seq,
        "message": message,
        "data": data or {},
    }


def user_task(seq: int, task: str) -> Event:
    return make_event(
        "user_task",
        seq,
        task,
        {"task": task},
    )


def shell_command(seq: int, command: str) -> Event:
    return make_event(
        "shell_command",
        seq,
        command,
        {"command": command},
    )


def tool_call(seq: int, tool_name: str, arguments: dict[str, Any]) -> Event:
    return make_event(
        "tool_call",
        seq,
        f"Call tool {tool_name}",
        {
            "tool_name": tool_name,
            "arguments": arguments,
        },
    )


def tool_result(
    seq: int,
    tool_name: str,
    ok: bool,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> Event:
    status = "succeeded" if ok else "failed"
    return make_event(
        "tool_result",
        seq,
        f"Tool {tool_name} {status}",
        {
            "tool_name": tool_name,
            "ok": ok,
            "result": result or {},
            "error": error,
        },
    )


def verification(
    seq: int,
    command: str,
    exit_code: int,
    stdout: str = "",
    stderr: str = "",
) -> Event:
    ok = exit_code == 0
    status = "passed" if ok else "failed"
    return make_event(
        "verification",
        seq,
        f"Verification {status}: {command}",
        {
            "command": command,
            "ok": ok,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
        },
    )


def final_answer(seq: int, answer: str) -> Event:
    return make_event(
        "final_answer",
        seq,
        answer,
        {"answer": answer},
    )


def stop(seq: int, reason: str, data: dict[str, Any] | None = None) -> Event:
    return make_event(
        "stop",
        seq,
        f"Agent loop stopped: {reason}.",
        {
            "reason": reason,
            **(data or {}),
        },
    )


def mock_transcript(task: str) -> list[Event]:
    return [
        user_task(1, task),
        make_event(
            "assistant_step",
            2,
            "Plan the smallest observable transcript.",
            {"step": "plan"},
        ),
        tool_call(3, "read_file", {"path": "examples/toy_project/test_calculator.py"}),
        tool_result(
            4,
            "read_file",
            True,
            {"content_preview": "def test_add(): ..."},
        ),
        verification(
            5,
            "python -m unittest discover examples/toy_project",
            1,
            stderr="FAILED (failures=1)",
        ),
        final_answer(
            6,
            "Mock transcript complete. No real tools or files were changed.",
        ),
    ]
