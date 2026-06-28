from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

try:
    from OpenCAI.events import Event
    from OpenCAI.runtime_commands import RUNTIME_COMMANDS
except ModuleNotFoundError as exc:
    if exc.name != "OpenCAI":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from OpenCAI.events import Event
    from OpenCAI.runtime_commands import RUNTIME_COMMANDS

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import CompleteStyle


console = Console()


class RuntimeCommandCompleter(Completer):
    def get_completions(self, document: Document, complete_event: object) -> Any:
        text = document.text_before_cursor
        if not text.startswith("/"):
            return

        parts = text.split()
        current_token = parts[-1] if parts else text
        command_name = parts[0] if parts else ""

        if " " not in text:
            for command in RUNTIME_COMMANDS:
                if command.name.startswith(current_token):
                    yield Completion(
                        command.name,
                        start_position=-len(current_token),
                        display=command.name,
                        display_meta=command.description,
                    )
            return

        command = next((item for item in RUNTIME_COMMANDS if item.name == command_name), None)
        if command is None or not command.choices:
            return

        choice_prefix = text.rsplit(" ", 1)[-1]
        for choice in command.choices:
            if choice.startswith(choice_prefix):
                yield Completion(
                    choice,
                    start_position=-len(choice_prefix),
                    display=choice,
                    display_meta=f"{command.name} {command.args_hint}",
                )


TASK_COMPLETER = RuntimeCommandCompleter()


def _truncate(value: str, limit: int = 600) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n... [truncated]"


def render_startup(
    mode: str = "Phase 0-5 / Fake Agent Loop",
    status: str = "Fake LLM adapter + read_file tool; no Gemini request and no file writes",
) -> None:
    cwd = Path.cwd()
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()
    table.add_row("Project", "OpenCAI")
    table.add_row("Mode", mode)
    table.add_row("CWD", str(cwd))
    table.add_row("Status", status)

    console.print()
    console.print(
        Panel(
            table,
            title="OpenCAI Coding Agent",
            subtitle="thin transcript renderer",
            border_style="cyan",
        ),
    )
    console.print()


def render_key_values(title: str, rows: dict[str, Any], border_style: str) -> None:
    body = Table.grid(padding=(0, 1))
    body.add_column(style="bold", no_wrap=True)
    body.add_column()
    for key, value in rows.items():
        body.add_row(key, repr(value) if isinstance(value, (dict, list)) else str(value))
    console.print(Panel(body, title=title, border_style=border_style))


def render_event(event: Event) -> None:
    event_type = event.get("type", "error")
    seq = event.get("seq", "?")
    message = event.get("message", "")
    data = event.get("data", {})

    if event_type == "tool_call":
        render_key_values(
            f"{seq} Tool call",
            {
                "tool": data.get("tool_name", "unknown"),
                "arguments": data.get("arguments", {}),
            },
            "magenta",
        )
        return

    if event_type == "tool_result":
        ok = data.get("ok", False)
        render_key_values(
            f"{seq} Tool result",
            {
                "tool": data.get("tool_name", "unknown"),
                "ok": ok,
                "result": data.get("result", {}),
            },
            "green" if ok else "red",
        )
        return

    if event_type == "verification":
        ok = data.get("ok", False)
        render_key_values(
            f"{seq} Verification",
            {
                "command": data.get("command", ""),
                "ok": ok,
                "exit_code": data.get("exit_code", ""),
                "stdout": _truncate(data.get("stdout", "")),
                "stderr": _truncate(data.get("stderr", "")),
            },
            "green" if ok else "red",
        )
        return

    border_styles = {
        "user_task": "green",
        "shell_command": "yellow",
        "patch_summary": "cyan",
        "assistant_step": "blue",
        "final_answer": "white",
        "error": "red",
    }
    titles = {
        "user_task": "User task",
        "shell_command": "Shell command",
        "assistant_step": "Assistant",
        "patch_summary": "Patch summary",
        "final_answer": "Final answer",
        "error": "Error",
    }
    title = f"{seq} {titles.get(event_type, 'Unknown event')}"
    body = Markdown(message or repr(data))
    console.print(Panel(body, title=title, border_style=border_styles.get(event_type, "red")))


def render_transcript(events: list[Event]) -> None:
    console.rule("[bold]Transcript")
    for event in events:
        render_event(event)
    console.rule()


def ask_task(default: str = "", label: str = "Task") -> str:
    if not sys.stdin.isatty():
        suffix = f" ({default})" if default else ""
        return input(f"{label}{suffix}: ")
    value = prompt(
        f"{label}> ",
        completer=TASK_COMPLETER,
        complete_while_typing=True,
        complete_style=CompleteStyle.COLUMN,
        reserve_space_for_menu=8,
    )
    return value


def main() -> None:
    render_startup(
        mode="Renderer / Input helper",
        status="Direct tui.py does not run the Agent Loop; Runtime owns execution.",
    )
    task = ask_task("Fix the failing toy project test")
    console.print(f"Task: {task}")


if __name__ == "__main__":
    main()
