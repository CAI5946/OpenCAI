from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

try:
    from OpenCAI import __version__
    from OpenCAI.composer import ComposerState, build_suggestions
    from OpenCAI.events import Event
except ModuleNotFoundError as exc:
    if exc.name != "OpenCAI":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from OpenCAI import __version__
    from OpenCAI.composer import ComposerState, build_suggestions
    from OpenCAI.events import Event

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.containers import ConditionalContainer, Float, FloatContainer, HSplit, VSplit, Window
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea


console = Console()

INPUT_PROMPT_LABEL = ""
INPUT_PLACEHOLDER = "Ask OpenCAI, type / for commands, or ! for shell"
INPUT_BORDER_CHAR = "─"
INPUT_MARKER_DEFAULT = ">"
INPUT_MARKER_COMMAND = ">"
INPUT_MARKER_SHELL = ">"
DEFAULT_STATUS_BAR_ITEMS = ("version", "model", "cwd", "permissions", "max_steps")
PROCESS_SHORTCUT_COMMAND = "/process"
TASK_PROMPT_STYLE_RULES = {
    "input-marker": "bold #3b82f6",
    "input-marker-command": "bold #7c3aed",
    "input-marker-shell": "bold #d97706",
    "placeholder": "#3f4652 italic",
    "input-border": "#4b5563",
    "input-status": "#8b949e",
    "completion-menu": "fg:default bg:default",
    "completion-menu.completion": "fg:default bg:default",
    "completion-menu.completion.current": "bold ansibrightcyan bg:default noreverse",
    "completion-menu.meta.completion": "ansibrightblack bg:default",
    "completion-menu.meta.completion.current": "bold ansibrightcyan bg:default noreverse",
}
DIVIDER_STYLE = "default"
TASK_PROMPT_STYLE = Style.from_dict(TASK_PROMPT_STYLE_RULES)
SELECT_PROMPT_STYLE_RULES = {
    "title": "bold fg:default bg:default",
    "hint": "ansibrightblack bg:default",
    "item": "fg:default bg:default",
    "opencai-selected": "bold ansibrightcyan bg:default noreverse",
    "description": "ansibrightblack bg:default",
    "opencai-selected-description": "bold ansibrightcyan bg:default noreverse",
    "disabled": "ansibrightblack bg:default",
}
SELECT_PROMPT_STYLE = Style.from_dict(SELECT_PROMPT_STYLE_RULES)


class RuntimeCommandCompleter(Completer):
    def get_completions(self, document: Document, complete_event: object) -> Any:
        text = document.text_before_cursor
        start_position = _completion_start_position(text)
        for suggestion in build_suggestions(text):
            completion_text = suggestion.value
            if " " not in text and suggestion.value == text:
                completion_text = f"{suggestion.value} "
            yield Completion(
                completion_text,
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
    has_suggestions = has_composer_suggestions(buffer.text)
    updated = accept_composer_suggestion(buffer.text)
    if updated == buffer.text:
        return has_suggestions

    buffer.set_document(Document(updated, cursor_position=len(updated)))
    return True


def _submit_if_exact_suggestion(buffer: Buffer) -> bool:
    text = buffer.text
    if not _accept_composer_suggestion_for_buffer(buffer):
        return False
    if buffer.text == text:
        buffer.validate_and_handle()
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
        _submit_if_exact_suggestion(event.current_buffer)

    @bindings.add("escape", filter=composer_suggestions_filter, eager=True)
    def _dismiss_completion(event: Any) -> None:
        _dismiss_composer_suggestions_for_buffer(event.current_buffer)

    @bindings.add("down", filter=composer_suggestions_filter, eager=True)
    def _select_next_completion(event: Any) -> None:
        event.current_buffer.complete_next()

    @bindings.add("up", filter=composer_suggestions_filter, eager=True)
    def _select_previous_completion(event: Any) -> None:
        event.current_buffer.complete_previous()

    @bindings.add("c-o", eager=True)
    def _show_process(event: Any) -> None:
        event.app.exit(result=PROCESS_SHORTCUT_COMMAND)

    return bindings


TASK_KEY_BINDINGS = create_task_key_bindings()


@dataclass(frozen=True)
class SelectItem:
    value: str
    label: str
    description: str = ""
    current: bool = False
    disabled: bool = False


@dataclass(frozen=True)
class TaskSummary:
    task: str | None = None
    final_answer: str | None = None
    stop_message: str | None = None
    error_message: str | None = None


def ask_select(
    title: str,
    items: tuple[SelectItem, ...],
    *,
    hint: str = "Use ↑/↓, 1-9, Enter, Esc",
) -> str | None:
    if not items:
        return None

    selected_index = _first_enabled_select_index(items)

    def move_selection(delta: int) -> None:
        nonlocal selected_index
        if all(item.disabled for item in items):
            return

        candidate = selected_index
        for _ in items:
            candidate = (candidate + delta) % len(items)
            if not items[candidate].disabled:
                selected_index = candidate
                return

    def render_select() -> AnyFormattedText:
        rows: list[tuple[str, str]] = [
            ("", "\n"),
            ("class:title", f"{title}\n"),
            ("class:hint", f"{hint}\n"),
        ]
        label_texts = tuple(_select_label_text(index, item, index == selected_index) for index, item in enumerate(items))
        description_column = max(len(label_text) for label_text in label_texts) + 2
        for index, item in enumerate(items):
            is_selected = index == selected_index
            style = "class:opencai-selected" if is_selected else "class:disabled" if item.disabled else "class:item"
            label_text = label_texts[index]
            rows.append((style, label_text))
            rows.append(("", " " * max(1, description_column - len(label_text))))
            if item.description:
                rows.append(("class:opencai-selected-description" if is_selected else "class:description", item.description))
            rows.append(("", "\n"))
        return rows

    bindings = KeyBindings()

    @bindings.add("down")
    @bindings.add("c-n")
    def _select_next(event: Any) -> None:
        move_selection(1)
        event.app.invalidate()

    @bindings.add("up")
    @bindings.add("c-p")
    def _select_previous(event: Any) -> None:
        move_selection(-1)
        event.app.invalidate()

    @bindings.add("enter")
    def _accept_selected(event: Any) -> None:
        item = items[selected_index]
        event.app.exit(result=None if item.disabled else item.value)

    @bindings.add("escape")
    @bindings.add("c-c")
    def _cancel(event: Any) -> None:
        event.app.exit(result=None)

    for key_index in range(min(len(items), 9)):
        key = str(key_index + 1)

        @bindings.add(key)
        def _accept_number(event: Any, index: int = key_index) -> None:
            item = items[index]
            event.app.exit(result=None if item.disabled else item.value)

    app: Application[str | None] = Application(
        layout=Layout(
            Window(
                FormattedTextControl(render_select),
                dont_extend_height=True,
                always_hide_cursor=True,
            )
        ),
        key_bindings=bindings,
        full_screen=False,
        erase_when_done=True,
        style=SELECT_PROMPT_STYLE,
    )
    return app.run()


def _first_enabled_select_index(items: tuple[SelectItem, ...]) -> int:
    for index, item in enumerate(items):
        if item.current and not item.disabled:
            return index
    for index, item in enumerate(items):
        if not item.disabled:
            return index
    return 0


def _select_label_text(index: int, item: SelectItem, is_selected: bool) -> str:
    marker = "›" if is_selected else " "
    current = " (current)" if item.current else ""
    number = f"{index + 1}."
    return f"{marker} {number} {item.label}{current}"


def _truncate(value: str, limit: int = 600) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n... [truncated]"


def render_status_bar(
    session: Any,
    items: tuple[str, ...] = DEFAULT_STATUS_BAR_ITEMS,
) -> str:
    values = [_status_bar_item_value(session, item) for item in items]
    return " · ".join(value for value in values if value)


def _status_bar_item_value(session: Any, item: str) -> str:
    if item == "version":
        return __version__
    if item == "model":
        return str(getattr(session, "adapter_name", "unknown"))
    if item == "cwd":
        cwd = Path(getattr(session, "cwd", Path.cwd()))
        return cwd.name or str(cwd)
    if item == "max_steps":
        return f"step {getattr(session, 'max_steps', 'unknown')}"
    if item == "permissions":
        return _status_bar_permissions(session)
    return ""


def _status_bar_permissions(session: Any) -> str:
    permission_profile = getattr(session, "permission_profile", None)
    if permission_profile is not None:
        return str(getattr(permission_profile, "value", permission_profile))
    return "read-only"


def render_input_border(width: int | None = None) -> str:
    resolved_width = width or console.width
    return INPUT_BORDER_CHAR * max(20, resolved_width)


def input_mode_for_text(text: str) -> str:
    if text.startswith("/"):
        return "command"
    if text.startswith("!"):
        return "shell"
    return "task"


def render_input_status_line(status_bar: str | None = None, input_text: str = "") -> AnyFormattedText:
    status_parts = [f"{input_mode_for_text(input_text)} mode"]
    if status_bar:
        status_parts.append(status_bar)
    status = " · ".join(status_parts)

    return [("class:input-status", status)]


def render_submitted_input_line(input_text: str) -> str:
    submitted = input_text.strip()
    if not submitted:
        return ""

    return f"Submitted {input_mode_for_text(submitted)}:\n{submitted}"


def render_submitted_input(input_text: str) -> None:
    submitted_line = render_submitted_input_line(input_text)
    if not submitted_line:
        return

    render_rule()
    console.print(submitted_line, style="dim")


def input_marker_for_text(text: str) -> tuple[str, str]:
    if text.startswith("/"):
        return INPUT_MARKER_COMMAND, "class:input-marker-command"
    if text.startswith("!"):
        return INPUT_MARKER_SHELL, "class:input-marker-shell"
    return INPUT_MARKER_DEFAULT, "class:input-marker"


def render_input_marker(buffer: Buffer) -> AnyFormattedText:
    marker, style = input_marker_for_text(buffer.text)
    return [(style, f"{marker} ")]


def create_task_input_layout(buffer: Buffer, status_bar: str | None = None) -> Layout:
    is_empty = Condition(lambda: not buffer.text)
    buffer_control = BufferControl(buffer=buffer)
    buffer_window = Window(buffer_control, height=1, wrap_lines=False)
    input_field = FloatContainer(
        content=buffer_window,
        floats=[
            Float(
                left=1,
                top=0,
                content=ConditionalContainer(
                    Window(
                        FormattedTextControl([("class:placeholder", INPUT_PLACEHOLDER)]),
                        height=1,
                        dont_extend_width=True,
                    ),
                    filter=is_empty,
                ),
                transparent=True,
            )
        ],
    )
    input_row = VSplit(
        [
            Window(
                FormattedTextControl(lambda: render_input_marker(buffer)),
                width=2,
                dont_extend_width=True,
            ),
            input_field,
        ]
    )
    root = HSplit(
        [
            Window(
                FormattedTextControl(lambda: [("class:input-border", render_input_border())]),
                height=1,
            ),
            input_row,
            Window(
                FormattedTextControl(lambda: [("class:input-border", render_input_border())]),
                height=1,
            ),
            Window(
                FormattedTextControl(lambda: render_input_status_line(status_bar, input_text=buffer.text)),
                height=1,
            ),
            CompletionsMenu(max_height=8),
        ]
    )
    return Layout(root, focused_element=buffer_control)


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


def render_key_values(title: str, rows: dict[str, Any], border_style: str = "white") -> None:
    render_rule(title)
    for key, value in rows.items():
        console.print(f"[bold]{key}[/]: {_render_event_value(value)}")


def render_rule(title: str = "") -> None:
    console.rule(title, style=DIVIDER_STYLE)


def _render_event_value(value: Any) -> str:
    rendered_value = repr(value) if isinstance(value, (dict, list)) else str(value)
    return _truncate(rendered_value)


def render_event(event: Event) -> None:
    event_type = event.get("type", "error")
    seq = event.get("seq", "?")
    message = event.get("message", "")
    data = event.get("data", {})

    if event_type == "user_task":
        return

    if event_type == "tool_call":
        render_key_values(
            f"{seq} Tool call",
            {
                "tool": data.get("tool_name", "unknown"),
                "arguments": data.get("arguments", {}),
            },
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
        )
        return

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
    render_rule(title)
    console.print(body)


def render_transcript(events: list[Event]) -> None:
    render_event_process(events)


def render_event_stream(events: Iterable[Event]) -> None:
    render_rule("Transcript")
    for event in events:
        render_event(event)
    render_rule()


def process_events(events: Iterable[Event], *, skip_user_task: bool = True) -> list[Event]:
    return [
        event
        for event in events
        if not (skip_user_task and event.get("type") == "user_task")
    ]


def extract_task_summary(events: Iterable[Event]) -> TaskSummary:
    task: str | None = None
    final: str | None = None
    stop_message: str | None = None
    error_message: str | None = None

    for event in events:
        event_type = event.get("type")
        if event_type == "user_task":
            task = event.get("data", {}).get("task") or event.get("message") or task
        elif event_type == "final_answer":
            final = event.get("data", {}).get("answer") or event.get("message") or final
        elif event_type == "stop":
            stop_message = event.get("message") or stop_message
        elif event_type == "error":
            error_message = event.get("message") or error_message

    return TaskSummary(
        task=task,
        final_answer=final,
        stop_message=stop_message,
        error_message=error_message,
    )


def render_task_summary(events: Iterable[Event], *, include_submitted_task: bool = False) -> None:
    event_list = list(events)
    summary = extract_task_summary(event_list)

    if include_submitted_task and summary.task:
        render_submitted_input(summary.task)

    if summary.final_answer:
        render_rule()
        console.print("Final answer:")
        console.print(Markdown(summary.final_answer))
    elif summary.error_message:
        render_rule("Error")
        console.print(summary.error_message)
    elif summary.stop_message:
        render_rule("Stop")
        console.print(summary.stop_message)
    else:
        render_rule("No final answer")

    if process_events(event_list):
        console.print("Process collapsed. Press Ctrl+O or run /process to expand.", style="dim")


def live_process_text(events: Iterable[Event], *, skip_user_task: bool = True, limit: int = 6) -> Text:
    process = process_events(events, skip_user_task=skip_user_task)
    text = Text()
    if not process:
        text.append("Process: waiting for events", style="dim")
        return text

    text.append("Process running. Ctrl+O after completion expands details.\n", style="dim")
    for event in process[-limit:]:
        event_type = event.get("type", "event")
        seq = event.get("seq", "?")
        message = event.get("message", "")
        data = event.get("data", {})
        if event_type == "tool_call":
            label = f"{seq}. tool call: {data.get('tool_name', 'unknown')}"
        elif event_type == "tool_result":
            status = "ok" if data.get("ok", False) else "failed"
            label = f"{seq}. tool result: {data.get('tool_name', 'unknown')} ({status})"
        elif event_type == "final_answer":
            label = f"{seq}. final answer ready"
        else:
            label = f"{seq}. {event_type.replace('_', ' ')}"
        if message and event_type not in {"tool_call", "tool_result"}:
            label = f"{label}: {message}"
        text.append(label)
        text.append("\n")
    text.rstrip()
    return text


class LiveProcessRenderer:
    def __init__(self) -> None:
        self._live: Live | None = None

    def __enter__(self) -> "LiveProcessRenderer":
        self._live = Live(
            live_process_text([]),
            console=console,
            transient=True,
            refresh_per_second=8,
        )
        self._live.__enter__()
        return self

    def update(self, events: Iterable[Event]) -> None:
        if self._live is None:
            return
        self._live.update(live_process_text(events))

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._live is None:
            return
        self._live.__exit__(exc_type, exc, traceback)
        self._live = None


def render_event_process(events: Iterable[Event], *, skip_user_task: bool = True) -> None:
    process = process_events(events, skip_user_task=skip_user_task)
    if not process:
        console.print("No process transcript yet.")
        return

    render_rule("Process")
    for event in process:
        render_event(event)
    render_rule()


def process_view_text(events: Iterable[Event], *, skip_user_task: bool = True) -> str:
    process = process_events(events, skip_user_task=skip_user_task)
    if not process:
        return "No process transcript yet."

    lines = ["Process", ""]
    for event in process:
        lines.extend(_event_text_lines(event))
        lines.append("")
    lines.append("Press Ctrl+O, Esc, Enter, or q to collapse.")
    return "\n".join(lines).rstrip()


def create_process_view_key_bindings() -> KeyBindings:
    bindings = KeyBindings()

    @bindings.add("c-o")
    @bindings.add("escape")
    @bindings.add("enter")
    @bindings.add("q")
    @bindings.add("c-c")
    def _collapse(event: Any) -> None:
        event.app.exit()

    return bindings


def _event_text_lines(event: Event) -> list[str]:
    event_type = event.get("type", "error")
    seq = event.get("seq", "?")
    message = event.get("message", "")
    data = event.get("data", {})

    if event_type == "tool_call":
        return [
            f"{seq} Tool call",
            f"tool: {data.get('tool_name', 'unknown')}",
            f"arguments: {_render_event_value(data.get('arguments', {}))}",
        ]
    if event_type == "tool_result":
        return [
            f"{seq} Tool result",
            f"tool: {data.get('tool_name', 'unknown')}",
            f"ok: {data.get('ok', False)}",
            f"result: {_render_event_value(data.get('result', {}))}",
        ]
    if event_type == "verification":
        return [
            f"{seq} Verification",
            f"command: {data.get('command', '')}",
            f"ok: {data.get('ok', False)}",
            f"exit_code: {data.get('exit_code', '')}",
            f"stdout: {_truncate(data.get('stdout', ''))}",
            f"stderr: {_truncate(data.get('stderr', ''))}",
        ]

    titles = {
        "shell_command": "Shell command",
        "assistant_step": "Assistant",
        "patch_summary": "Patch summary",
        "final_answer": "Final answer",
        "stop": "Stop",
        "error": "Error",
    }
    return [f"{seq} {titles.get(event_type, 'Unknown event')}", message or repr(data)]


def show_process_view(events: Iterable[Event], *, skip_user_task: bool = True) -> None:
    if not sys.stdin.isatty():
        render_event_process(events, skip_user_task=skip_user_task)
        return

    text_area = TextArea(
        text=process_view_text(events, skip_user_task=skip_user_task),
        read_only=True,
        scrollbar=True,
        wrap_lines=True,
    )
    app: Application[None] = Application(
        layout=Layout(text_area),
        key_bindings=create_process_view_key_bindings(),
        full_screen=True,
        erase_when_done=True,
    )
    app.run()


def ask_task(
    default: str = "",
    label: str = "Task",
    status_bar: str | None = None,
) -> str:
    if not sys.stdin.isatty():
        suffix = f" ({default})" if default else ""
        prompt_label = f"{label}{suffix}: " if label else "> "
        return input(prompt_label)

    app: Application[str] | None = None

    def accept_input(buffer: Buffer) -> bool:
        if app is not None:
            app.exit(result=buffer.text)
        return True

    def refresh_completions(buffer: Buffer) -> None:
        if has_composer_suggestions(buffer.text):
            buffer.start_completion()

    buffer = Buffer(
        completer=TASK_COMPLETER,
        complete_while_typing=True,
        accept_handler=accept_input,
        multiline=False,
        on_text_changed=refresh_completions,
    )
    app = Application(
        layout=create_task_input_layout(buffer, status_bar),
        key_bindings=create_task_key_bindings(),
        full_screen=False,
        erase_when_done=True,
        style=TASK_PROMPT_STYLE,
        cursor=CursorShape.BLINKING_BEAM,
    )
    submitted = app.run()
    if submitted != PROCESS_SHORTCUT_COMMAND:
        render_submitted_input(submitted)
    return submitted


def ask_choice(label: str, choices: tuple[str, ...], current: str | None = None) -> str | None:
    if not sys.stdin.isatty():
        try:
            value = input(f"{label} ({'/'.join(choices)}): ").strip()
        except EOFError:
            return None
        return value if value in choices else None

    return ask_select(
        f"Select {label}",
        _choice_items(label, choices, current),
    )


def _choice_items(label: str, choices: tuple[str, ...], current: str | None = None) -> tuple[SelectItem, ...]:
    return tuple(
        SelectItem(
            value=value,
            label=_choice_label(label, value),
            description=_choice_description(label, value),
            current=value == current,
        )
        for value in choices
    )


def _choice_label(label: str, value: str) -> str:
    if label == "Model" and value == "gemini":
        return "Gemini 2.5 Flash"
    if label == "Model" and value == "fake":
        return "Fake"
    return value


def _choice_description(label: str, value: str) -> str:
    if label == "Model" and value == "gemini":
        return "Real Gemini adapter for tool-calling smoke tests."
    if label == "Model" and value == "fake":
        return "Local deterministic adapter for testing."
    return ""


def main() -> None:
    render_startup(
        mode="Renderer / Input helper",
        status="Direct tui.py does not run the Agent Loop; Runtime owns execution.",
    )
    task = ask_task("Fix the failing toy project test")
    console.print(f"Task: {task}")


if __name__ == "__main__":
    main()
