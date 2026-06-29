from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

try:
    from OpenCAI.composer import ComposerState, build_suggestions
    from OpenCAI.events import Event
except ModuleNotFoundError as exc:
    if exc.name != "OpenCAI":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from OpenCAI.composer import ComposerState, build_suggestions
    from OpenCAI.events import Event

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from prompt_toolkit import prompt
from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import CompleteStyle


console = Console()


class RuntimeCommandCompleter(Completer):
    def get_completions(self, document: Document, complete_event: object) -> Any:
        text = document.text_before_cursor
        start_position = _completion_start_position(text)
        for suggestion in build_suggestions(text):
            yield Completion(
                suggestion.value,
                start_position=start_position,
                display=suggestion.value,
                display_meta=suggestion.description,
            )


def _completion_start_position(text: str) -> int:
    if not text.startswith("/"):
        return 0
    if " " not in text:
        return -len(text)
    return -len(text.rsplit(" ", 1)[-1])


TASK_COMPLETER = RuntimeCommandCompleter()


def accept_composer_suggestion(text: str) -> str:
    state = ComposerState()
    state.update_text(text)
    return state.accept_suggestion()


def has_composer_suggestions(text: str) -> bool:
    return bool(build_suggestions(text))


def _accept_composer_suggestion_for_buffer(buffer: Buffer) -> bool:
    updated = accept_composer_suggestion(buffer.text)
    if updated == buffer.text:
        return False

    buffer.set_document(Document(updated, cursor_position=len(updated)))
    return True


def _dismiss_composer_suggestions_for_buffer(buffer: Buffer) -> bool:
    if not has_composer_suggestions(buffer.text):
        return False

    buffer.cancel_completion()
    return True


def create_task_key_bindings() -> KeyBindings:
    bindings = KeyBindings()

    def composer_suggestions_visible() -> bool:
        app = get_app()
        return has_composer_suggestions(app.current_buffer.text)

    composer_suggestions_filter = Condition(composer_suggestions_visible)

    @bindings.add("tab", eager=True)
    def _accept_or_cycle_completion(event: Any) -> None:
        if not _accept_composer_suggestion_for_buffer(event.current_buffer):
            event.current_buffer.complete_next()

    @bindings.add("enter", filter=composer_suggestions_filter, eager=True)
    def _accept_completion_before_submit(event: Any) -> None:
        _accept_composer_suggestion_for_buffer(event.current_buffer)

    @bindings.add("escape", filter=composer_suggestions_filter, eager=True)
    def _dismiss_completion(event: Any) -> None:
        _dismiss_composer_suggestions_for_buffer(event.current_buffer)

    @bindings.add("down", filter=composer_suggestions_filter, eager=True)
    def _select_next_completion(event: Any) -> None:
        event.current_buffer.complete_next()

    @bindings.add("up", filter=composer_suggestions_filter, eager=True)
    def _select_previous_completion(event: Any) -> None:
        event.current_buffer.complete_previous()

    return bindings


TASK_KEY_BINDINGS = create_task_key_bindings()


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
        "stop": "yellow",
        "error": "red",
    }
    titles = {
        "user_task": "User task",
        "shell_command": "Shell command",
        "assistant_step": "Assistant",
        "patch_summary": "Patch summary",
        "final_answer": "Final answer",
        "stop": "Stop",
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
        key_bindings=TASK_KEY_BINDINGS,
        complete_while_typing=True,
        complete_style=CompleteStyle.COLUMN,
        reserve_space_for_menu=8,
    )
    return value


def ask_choice(label: str, choices: tuple[str, ...]) -> str | None:
    if not sys.stdin.isatty():
        try:
            value = input(f"{label} ({'/'.join(choices)}): ").strip()
        except EOFError:
            return None
        return value if value in choices else None

    value = prompt(
        f"{label}> ",
        completer=WordCompleter(choices),
        complete_while_typing=True,
        complete_style=CompleteStyle.COLUMN,
        reserve_space_for_menu=8,
    ).strip()
    return value if value in choices else None


def main() -> None:
    render_startup(
        mode="Renderer / Input helper",
        status="Direct tui.py does not run the Agent Loop; Runtime owns execution.",
    )
    task = ask_task("Fix the failing toy project test")
    console.print(f"Task: {task}")


if __name__ == "__main__":
    main()
