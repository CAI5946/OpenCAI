"""Command tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import threading
import time
from typing import Any
from uuid import uuid4

from OpenCAI.tooling.contracts import ToolResult, ToolSpec, tool_result


DEFAULT_COMMAND_TIMEOUT_SECONDS = 30
MAX_COMMAND_TIMEOUT_SECONDS = 600
DEFAULT_OUTPUT_MAX_CHARS = 30000
MAX_OUTPUT_MAX_CHARS = 150000


@dataclass
class CommandSession:
    command_id: str
    command: str
    cwd: Path
    process: subprocess.Popen[str]
    started_at: float
    stdout: list[str] = field(default_factory=list)
    stderr: list[str] = field(default_factory=list)
    stdout_offset: int = 0
    stderr_offset: int = 0
    reader_threads: list[threading.Thread] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


COMMAND_SESSIONS: dict[str, CommandSession] = {}


def _cleanup_session(command_id: str, session: CommandSession) -> None:
    COMMAND_SESSIONS.pop(command_id, None)
    for stream in (session.process.stdin, session.process.stdout, session.process.stderr):
        if stream is None:
            continue
        try:
            stream.close()
        except OSError:
            pass


def _bounded_int(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int,
    name: str,
) -> tuple[int | None, str | None]:
    if value is None:
        return default, None
    if isinstance(value, bool):
        return None, f"{name} must be an integer"
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, f"{name} must be an integer"
    if parsed < minimum or parsed > maximum:
        return None, f"{name} must be between {minimum} and {maximum}"
    return parsed, None


def _resolve_command_cwd(arguments: dict[str, Any], cwd: Path) -> tuple[Path | None, str | None]:
    raw_cwd = arguments.get("cwd")
    if raw_cwd is None or raw_cwd == "":
        return cwd, None
    if not isinstance(raw_cwd, str):
        return None, "cwd must be a string"

    resolved_root = cwd.resolve()
    candidate = (resolved_root / raw_cwd).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        return None, f"cwd escapes workspace: {raw_cwd}"
    if not candidate.exists():
        return None, f"cwd does not exist: {raw_cwd}"
    if not candidate.is_dir():
        return None, f"cwd is not a directory: {raw_cwd}"
    return candidate, None


def _truncate_output(value: str, max_chars: int) -> tuple[str, bool, int]:
    original_chars = len(value)
    if original_chars <= max_chars:
        return value, False, original_chars
    return value[-max_chars:], True, original_chars


def _append_stream(session: CommandSession, stream_name: str) -> None:
    stream = getattr(session.process, stream_name)
    if stream is None:
        return
    while True:
        chunk = stream.read(1)
        if chunk == "":
            break
        with session.lock:
            getattr(session, stream_name).append(chunk)


def run_command(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    command = arguments.get("command")
    if not isinstance(command, str) or not command:
        return tool_result("run_command", False, error="Missing required string argument: command")

    command_cwd, cwd_error = _resolve_command_cwd(arguments, cwd)
    if cwd_error is not None:
        return tool_result("run_command", False, error=cwd_error)

    timeout, timeout_error = _bounded_int(
        arguments.get("timeout"),
        default=DEFAULT_COMMAND_TIMEOUT_SECONDS,
        minimum=1,
        maximum=MAX_COMMAND_TIMEOUT_SECONDS,
        name="timeout",
    )
    if timeout_error is not None or timeout is None:
        return tool_result("run_command", False, error=timeout_error)

    max_output_chars, output_error = _bounded_int(
        arguments.get("max_output_chars"),
        default=DEFAULT_OUTPUT_MAX_CHARS,
        minimum=1,
        maximum=MAX_OUTPUT_MAX_CHARS,
        name="max_output_chars",
    )
    if output_error is not None or max_output_chars is None:
        return tool_result("run_command", False, error=output_error)

    try:
        completed = subprocess.run(
            command,
            cwd=command_cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        stdout, stdout_truncated, stdout_chars = _truncate_output(str(stdout), max_output_chars)
        stderr, stderr_truncated, stderr_chars = _truncate_output(str(stderr), max_output_chars)
        return tool_result(
            "run_command",
            False,
            {
                "command": command,
                "cwd": str(command_cwd),
                "exit_code": None,
                "stdout": stdout,
                "stderr": stderr,
                "timed_out": True,
                "timeout": timeout,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
                "stdout_chars": stdout_chars,
                "stderr_chars": stderr_chars,
            },
            error=f"Command timed out after {timeout} seconds",
        )
    except OSError as exc:
        return tool_result("run_command", False, error=f"Command failed: {exc}")

    stdout, stdout_truncated, stdout_chars = _truncate_output(completed.stdout, max_output_chars)
    stderr, stderr_truncated, stderr_chars = _truncate_output(completed.stderr, max_output_chars)
    return tool_result(
        "run_command",
        True,
        {
            "command": command,
            "cwd": str(command_cwd),
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": False,
            "timeout": timeout,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "stdout_chars": stdout_chars,
            "stderr_chars": stderr_chars,
        },
    )


def start_command(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    command = arguments.get("command")
    if not isinstance(command, str) or not command:
        return tool_result("start_command", False, error="Missing required string argument: command")

    command_cwd, cwd_error = _resolve_command_cwd(arguments, cwd)
    if cwd_error is not None:
        return tool_result("start_command", False, error=cwd_error)

    try:
        process = subprocess.Popen(
            command,
            cwd=command_cwd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        return tool_result("start_command", False, error=f"Command failed: {exc}")

    command_id = uuid4().hex
    session = CommandSession(
        command_id=command_id,
        command=command,
        cwd=command_cwd,
        process=process,
        started_at=time.time(),
    )
    COMMAND_SESSIONS[command_id] = session
    for stream_name in ("stdout", "stderr"):
        thread = threading.Thread(target=_append_stream, args=(session, stream_name), daemon=True)
        thread.start()
        session.reader_threads.append(thread)

    return tool_result(
        "start_command",
        True,
        {
            "command_id": command_id,
            "command": command,
            "cwd": str(command_cwd),
            "pid": process.pid,
            "running": process.poll() is None,
        },
    )


def read_command(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    command_id = arguments.get("command_id")
    if not isinstance(command_id, str) or not command_id:
        return tool_result("read_command", False, error="Missing required string argument: command_id")
    session = COMMAND_SESSIONS.get(command_id)
    if session is None:
        return tool_result("read_command", False, error=f"Unknown command session: {command_id}")

    max_output_chars, output_error = _bounded_int(
        arguments.get("max_output_chars"),
        default=DEFAULT_OUTPUT_MAX_CHARS,
        minimum=1,
        maximum=MAX_OUTPUT_MAX_CHARS,
        name="max_output_chars",
    )
    if output_error is not None or max_output_chars is None:
        return tool_result("read_command", False, error=output_error)

    exit_code = session.process.poll()
    running = exit_code is None
    if not running:
        for thread in session.reader_threads:
            thread.join(timeout=0.2)

    with session.lock:
        stdout = "".join(session.stdout[session.stdout_offset:])
        stderr = "".join(session.stderr[session.stderr_offset:])
        session.stdout_offset = len(session.stdout)
        session.stderr_offset = len(session.stderr)

    stdout, stdout_truncated, stdout_chars = _truncate_output(stdout, max_output_chars)
    stderr, stderr_truncated, stderr_chars = _truncate_output(stderr, max_output_chars)
    if not running:
        _cleanup_session(command_id, session)

    return tool_result(
        "read_command",
        True,
        {
            "command_id": command_id,
            "command": session.command,
            "running": running,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "stdout_chars": stdout_chars,
            "stderr_chars": stderr_chars,
        },
    )


def write_stdin(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    command_id = arguments.get("command_id")
    text = arguments.get("text")
    if not isinstance(command_id, str) or not command_id:
        return tool_result("write_stdin", False, error="Missing required string argument: command_id")
    if not isinstance(text, str):
        return tool_result("write_stdin", False, error="Missing required string argument: text")

    session = COMMAND_SESSIONS.get(command_id)
    if session is None:
        return tool_result("write_stdin", False, error=f"Unknown command session: {command_id}")
    if session.process.poll() is not None or session.process.stdin is None:
        return tool_result("write_stdin", False, error=f"Command session is not running: {command_id}")

    try:
        session.process.stdin.write(text)
        session.process.stdin.flush()
    except OSError as exc:
        return tool_result("write_stdin", False, error=f"Failed to write stdin: {exc}")

    return tool_result(
        "write_stdin",
        True,
        {
            "command_id": command_id,
            "chars_written": len(text),
        },
    )


def stop_command(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    command_id = arguments.get("command_id")
    if not isinstance(command_id, str) or not command_id:
        return tool_result("stop_command", False, error="Missing required string argument: command_id")

    session = COMMAND_SESSIONS.get(command_id)
    if session is None:
        return tool_result("stop_command", False, error=f"Unknown command session: {command_id}")

    if session.process.poll() is None:
        session.process.terminate()
        try:
            session.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            session.process.kill()
            session.process.wait(timeout=5)
    for thread in session.reader_threads:
        thread.join(timeout=0.2)

    _cleanup_session(command_id, session)
    return tool_result(
        "stop_command",
        True,
        {
            "command_id": command_id,
            "exit_code": session.process.returncode,
            "stopped": True,
        },
    )


COMMAND_TOOLS: dict[str, ToolSpec] = {
    "run_command": ToolSpec(
        name="run_command",
        description="Run a shell command with bounded timeout/output and return exit code, stdout, and stderr.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
                "timeout": {"type": "integer", "minimum": 1, "maximum": MAX_COMMAND_TIMEOUT_SECONDS},
                "max_output_chars": {"type": "integer", "minimum": 1, "maximum": MAX_OUTPUT_MAX_CHARS},
            },
            "required": ["command"],
        },
        read_only=False,
        function=run_command,
    ),
    "start_command": ToolSpec(
        name="start_command",
        description="Start a long-running shell command and return a command session id.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
            },
            "required": ["command"],
        },
        read_only=False,
        function=start_command,
    ),
    "read_command": ToolSpec(
        name="read_command",
        description="Read new stdout/stderr from a running command session.",
        input_schema={
            "type": "object",
            "properties": {
                "command_id": {"type": "string"},
                "max_output_chars": {"type": "integer", "minimum": 1, "maximum": MAX_OUTPUT_MAX_CHARS},
            },
            "required": ["command_id"],
        },
        read_only=False,
        function=read_command,
    ),
    "write_stdin": ToolSpec(
        name="write_stdin",
        description="Write text to a running command session stdin.",
        input_schema={
            "type": "object",
            "properties": {
                "command_id": {"type": "string"},
                "text": {"type": "string"},
            },
            "required": ["command_id", "text"],
        },
        read_only=False,
        function=write_stdin,
    ),
    "stop_command": ToolSpec(
        name="stop_command",
        description="Stop a running command session.",
        input_schema={
            "type": "object",
            "properties": {
                "command_id": {"type": "string"},
            },
            "required": ["command_id"],
        },
        read_only=False,
        function=stop_command,
    ),
}
