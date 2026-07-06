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
    from OpenCAI.output_format import format_output_title
except ModuleNotFoundError as exc:
    if exc.name != "OpenCAI":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from OpenCAI import __version__
    from OpenCAI.composer import ComposerState, build_suggestions
    from OpenCAI.events import Event
    from OpenCAI.output_format import format_output_title

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
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.containers import ConditionalContainer, Float, FloatContainer, HSplit, VSplit, Window
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea

if sys.platform == "win32":
    from prompt_toolkit.input.win32 import ConsoleInputReader
    from prompt_toolkit.key_binding.key_processor import KeyPress
else:
    ConsoleInputReader = None
    KeyPress = None


console = Console()

INPUT_PROMPT_LABEL = ""
INPUT_PLACEHOLDER = "Ask OpenCAI, type / for commands, or ! for shell"
INPUT_BORDER_CHAR = "─"
INPUT_MARKER_DEFAULT = ">"
INPUT_MARKER_COMMAND = ">"
INPUT_MARKER_SHELL = ">"
INPUT_MARKER_GUIDED = "?"
INPUT_MARKER_WORKFLOW = "◆"
DEFAULT_STATUS_BAR_ITEMS = ("execution_mode", "version", "model", "cwd", "permissions", "max_steps")
PROCESS_SHORTCUT_COMMAND = "/process"
MODEL_SHORTCUT_COMMAND = "/model"
EXIT_SHORTCUT_COMMAND = "/exit"
MODE_SHORTCUT_COMMANDS = ("/mode agent", "/mode guided", "/mode workflow")
TASK_PROMPT_STYLE_RULES = {
    "input-marker": "bold #3b82f6",
    "input-marker-command": "bold #7c3aed",
    "input-marker-shell": "bold #d97706",
    "input-marker-guided": "bold #16a34a",
    "input-marker-workflow": "bold #14b8a6",
    "placeholder": "#3f4652 italic",
    "input-border": "#4b5563",
    "input-status": "#8b949e",
    "input-status-guided": "bold #16a34a",
    "input-status-workflow": "bold #14b8a6",
    "completion-menu": "fg:default bg:default",
    "completion-menu.completion": "fg:default bg:default",
    "completion-menu.completion.current": "bold ansibrightcyan bg:default noreverse",
    "completion-menu.meta.completion": "ansibrightblack bg:default",
    "completion-menu.meta.completion.current": "bold ansibrightcyan bg:default noreverse",
}
DIVIDER_STYLE = "default"
TASK_PROMPT_STYLE = Style.from_dict(TASK_PROMPT_STYLE_RULES)
XTERM_SHIFT_ENTER_SEQUENCE = "\x1b[27;2;13~"
# prompt_toolkit maps this xterm Shift+Enter sequence to Enter by default.
ANSI_SEQUENCES[XTERM_SHIFT_ENTER_SEQUENCE] = Keys.ControlJ
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


def _install_windows_shift_enter_compat() -> None:
    if ConsoleInputReader is None or KeyPress is None:
        return
    if getattr(ConsoleInputReader, "_opencai_shift_enter_compat", False):
        return

    original_event_to_key_presses = ConsoleInputReader._event_to_key_presses

    def _event_to_key_presses_with_shift_enter(self: Any, ev: Any) -> list[Any]:
        key_presses = original_event_to_key_presses(self, ev)
        control_key_state = getattr(ev, "ControlKeyState", 0)
        shift_only = bool(control_key_state & self.SHIFT_PRESSED) and not bool(
            control_key_state
            & (self.LEFT_CTRL_PRESSED | self.RIGHT_CTRL_PRESSED | self.LEFT_ALT_PRESSED | self.RIGHT_ALT_PRESSED)
        )
        if shift_only and len(key_presses) == 1 and key_presses[0].key == Keys.ControlM:
            return [KeyPress(Keys.ControlJ, "\n")]
        return key_presses

    ConsoleInputReader._event_to_key_presses = _event_to_key_presses_with_shift_enter
    ConsoleInputReader._opencai_shift_enter_compat = True


_install_windows_shift_enter_compat()


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
    if text.startswith("$"):
        if " " not in text:
            return -len(text)
        return -len(text.rsplit(" ", 1)[-1])

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


def create_task_key_bindings(execution_mode: str | None = None) -> KeyBindings:
    bindings = KeyBindings()

    def composer_suggestions_visible() -> bool:
        app = get_app()
        return has_composer_suggestions(app.current_buffer.text)

    composer_suggestions_filter = Condition(composer_suggestions_visible)
    no_composer_suggestions_filter = ~composer_suggestions_filter

    @bindings.add("tab", eager=True)
    def _accept_or_cycle_completion(event: Any) -> None:
        if not _accept_composer_suggestion_for_buffer(event.current_buffer):
            event.current_buffer.complete_next()

    @bindings.add("enter", filter=composer_suggestions_filter, eager=True)
    def _accept_completion_before_submit(event: Any) -> None:
        _submit_if_exact_suggestion(event.current_buffer)

    @bindings.add("enter", filter=no_composer_suggestions_filter, eager=True)
    def _submit_input(event: Any) -> None:
        event.current_buffer.validate_and_handle()

    @bindings.add("c-j", eager=True)
    @bindings.add("escape", "[", "1", "3", ";", "2", "u", eager=True)
    def _insert_newline(event: Any) -> None:
        event.current_buffer.newline()

    @bindings.add("escape", filter=composer_suggestions_filter, eager=True)
    def _dismiss_completion(event: Any) -> None:
        _dismiss_composer_suggestions_for_buffer(event.current_buffer)

    @bindings.add("down", filter=composer_suggestions_filter, eager=True)
    def _select_next_completion(event: Any) -> None:
        event.current_buffer.complete_next()

    @bindings.add("up", filter=composer_suggestions_filter, eager=True)
    def _select_previous_completion(event: Any) -> None:
        event.current_buffer.complete_previous()

    @bindings.add("down", filter=no_composer_suggestions_filter, eager=True)
    def _select_next_history(event: Any) -> None:
        if not _history_forward_for_buffer(event.current_buffer):
            event.current_buffer.history_forward()

    @bindings.add("up", filter=no_composer_suggestions_filter, eager=True)
    def _select_previous_history(event: Any) -> None:
        if not _history_backward_for_buffer(event.current_buffer):
            event.current_buffer.history_backward()

    @bindings.add("c-r", eager=True)
    def _search_history(event: Any) -> None:
        if not _search_history_for_buffer(event.current_buffer):
            event.current_buffer.start_history_lines_completion()

    @bindings.add("c-d", eager=True)
    def _exit_interactive(event: Any) -> None:
        event.app.exit(result=EXIT_SHORTCUT_COMMAND)

    @bindings.add("c-c", eager=True)
    def _cancel_or_exit(event: Any) -> None:
        if event.current_buffer.text:
            event.current_buffer.reset()
            event.app.invalidate()
            return
        event.app.exit(result=EXIT_SHORTCUT_COMMAND)

    @bindings.add("c-l", eager=True)
    def _redraw(event: Any) -> None:
        event.app.invalidate()

    @bindings.add("c-o", eager=True)
    def _show_process(event: Any) -> None:
        event.app.exit(result=PROCESS_SHORTCUT_COMMAND)

    @bindings.add("escape", "p", eager=True)
    def _show_model_picker(event: Any) -> None:
        event.app.exit(result=MODEL_SHORTCUT_COMMAND)

    @bindings.add("s-tab", eager=True)
    def _cycle_execution_mode(event: Any) -> None:
        event.app.exit(result=_next_execution_mode_command(execution_mode))

    return bindings


TASK_KEY_BINDINGS = create_task_key_bindings()


def _next_execution_mode_command(execution_mode: str | None) -> str:
    modes = ("agent", "guided", "workflow")
    current = execution_mode if execution_mode in modes else "agent"
    current_index = modes.index(current)
    next_mode = modes[(current_index + 1) % len(modes)]
    return f"/mode {next_mode}"


def create_task_buffer(
    accept_handler: Any,
    *,
    history_entries: Iterable[str] | None = None,
) -> Buffer:
    entries = tuple(history_entries or ())
    buffer = Buffer(
        completer=TASK_COMPLETER,
        complete_while_typing=True,
        history=InMemoryHistory(entries),
        accept_handler=accept_handler,
        multiline=True,
        on_text_changed=_refresh_completions,
    )
    setattr(buffer, "_opencai_history_entries", entries)
    setattr(buffer, "_opencai_history_index", len(entries))
    return buffer


def _refresh_completions(buffer: Buffer) -> None:
    if has_composer_suggestions(buffer.text):
        buffer.start_completion()


def _history_entries_for_buffer(buffer: Buffer) -> tuple[str, ...]:
    entries = getattr(buffer, "_opencai_history_entries", ())
    return tuple(entry for entry in entries if entry)


def _set_buffer_text(buffer: Buffer, text: str) -> None:
    buffer.set_document(Document(text, cursor_position=len(text)))


def _history_backward_for_buffer(buffer: Buffer) -> bool:
    entries = _history_entries_for_buffer(buffer)
    if not entries:
        return False

    index = int(getattr(buffer, "_opencai_history_index", len(entries)))
    if index <= 0:
        return True
    index -= 1
    setattr(buffer, "_opencai_history_index", index)
    _set_buffer_text(buffer, entries[index])
    return True


def _history_forward_for_buffer(buffer: Buffer) -> bool:
    entries = _history_entries_for_buffer(buffer)
    if not entries:
        return False

    index = int(getattr(buffer, "_opencai_history_index", len(entries)))
    if index >= len(entries):
        return True
    index += 1
    setattr(buffer, "_opencai_history_index", index)
    _set_buffer_text(buffer, "" if index == len(entries) else entries[index])
    return True


def _search_history_for_buffer(buffer: Buffer) -> bool:
    entries = _history_entries_for_buffer(buffer)
    if not entries:
        return False

    query = buffer.text.strip().lower()
    for index in range(len(entries) - 1, -1, -1):
        entry = entries[index]
        if not query or query in entry.lower():
            setattr(buffer, "_opencai_history_index", index)
            _set_buffer_text(buffer, entry)
            return True
    return True


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
    if item == "execution_mode":
        return str(getattr(session, "execution_mode", "agent"))
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


def input_mode_for_text(text: str, execution_mode: str | None = None) -> str:
    if text.startswith("/"):
        return "command"
    if text.startswith("!"):
        return "shell"
    if execution_mode == "guided":
        return "guided"
    if execution_mode == "workflow":
        return "workflow"
    return "task"


def render_input_status_line(
    status_bar: str | None = None,
    input_text: str = "",
    execution_mode: str | None = None,
) -> AnyFormattedText:
    input_mode = input_mode_for_text(input_text, execution_mode)
    status_parts = [f"{input_mode} mode"]
    if status_bar:
        status_parts.append(status_bar)
    status = " · ".join(status_parts)
    if input_mode == "guided":
        style = "class:input-status-guided"
    elif input_mode == "workflow":
        style = "class:input-status-workflow"
    else:
        style = "class:input-status"

    return [(style, status)]


def render_submitted_input_line(input_text: str, execution_mode: str | None = None) -> str:
    submitted = input_text.strip()
    if not submitted:
        return ""

    return f"{format_output_title(f'Submitted {input_mode_for_text(submitted, execution_mode)}:')}\n{submitted}"


def render_submitted_input(input_text: str, execution_mode: str | None = None) -> None:
    submitted_line = render_submitted_input_line(input_text, execution_mode)
    if not submitted_line:
        return

    render_rule()
    console.print(submitted_line, style="dim")


def input_marker_for_text(text: str, execution_mode: str | None = None) -> tuple[str, str]:
    if text.startswith("/"):
        return INPUT_MARKER_COMMAND, "class:input-marker-command"
    if text.startswith("!"):
        return INPUT_MARKER_SHELL, "class:input-marker-shell"
    if execution_mode == "guided":
        return INPUT_MARKER_GUIDED, "class:input-marker-guided"
    if execution_mode == "workflow":
        return INPUT_MARKER_WORKFLOW, "class:input-marker-workflow"
    return INPUT_MARKER_DEFAULT, "class:input-marker"


def render_input_marker(buffer: Buffer, execution_mode: str | None = None) -> AnyFormattedText:
    marker, style = input_marker_for_text(buffer.text, execution_mode)
    return [(style, f"{marker} ")]


def create_task_input_layout(
    buffer: Buffer,
    status_bar: str | None = None,
    execution_mode: str | None = None,
) -> Layout:
    is_empty = Condition(lambda: not buffer.text)
    buffer_control = BufferControl(buffer=buffer)
    buffer_window = Window(
        buffer_control,
        height=Dimension(min=1, max=6),
        wrap_lines=True,
        dont_extend_height=True,
    )
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
                FormattedTextControl(lambda: render_input_marker(buffer, execution_mode)),
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
                FormattedTextControl(
                    lambda: render_input_status_line(
                        status_bar,
                        input_text=buffer.text,
                        execution_mode=execution_mode,
                    )
                ),
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
    console.rule(format_output_title(title), style=DIVIDER_STYLE)


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
        if data.get("tool_name") == "invoke_skill":
            render_key_values(
                f"{seq} Skill invoked",
                {
                    "skill": data.get("result", {}).get("skill", "unknown"),
                    "ok": ok,
                    "path": data.get("result", {}).get("path", ""),
                },
            )
            return
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
        console.print(format_output_title("Final answer:"))
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
            if data.get("tool_name") == "invoke_skill":
                skill = data.get("result", {}).get("skill", "unknown")
                label = f"{seq}. skill invoked: {skill} ({status})"
            else:
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

    lines = [format_output_title("Process"), ""]
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


def create_keymap_view_key_bindings() -> KeyBindings:
    bindings = KeyBindings()

    @bindings.add("escape")
    @bindings.add("enter")
    @bindings.add("q")
    @bindings.add("c-c")
    def _close(event: Any) -> None:
        event.app.exit()

    return bindings


def show_keymap_view() -> None:
    from OpenCAI.runtime_commands import render_keymap_text

    text = render_keymap_text()
    if not sys.stdin.isatty():
        print(text)
        return

    app: Application[None] = Application(
        layout=Layout(
            Window(
                FormattedTextControl(text),
                dont_extend_height=True,
                always_hide_cursor=True,
            )
        ),
        key_bindings=create_keymap_view_key_bindings(),
        full_screen=False,
        erase_when_done=True,
        style=SELECT_PROMPT_STYLE,
    )
    app.run()


def _event_text_lines(event: Event) -> list[str]:
    event_type = event.get("type", "error")
    seq = event.get("seq", "?")
    message = event.get("message", "")
    data = event.get("data", {})

    if event_type == "tool_call":
        return [
            format_output_title(f"{seq} Tool call"),
            f"tool: {data.get('tool_name', 'unknown')}",
            f"arguments: {_render_event_value(data.get('arguments', {}))}",
        ]
    if event_type == "tool_result":
        if data.get("tool_name") == "invoke_skill":
            result = data.get("result", {})
            return [
                format_output_title(f"{seq} Skill invoked"),
                f"skill: {result.get('skill', 'unknown')}",
                f"ok: {data.get('ok', False)}",
                f"path: {result.get('path', '')}",
            ]
        return [
            format_output_title(f"{seq} Tool result"),
            f"tool: {data.get('tool_name', 'unknown')}",
            f"ok: {data.get('ok', False)}",
            f"result: {_render_event_value(data.get('result', {}))}",
        ]
    if event_type == "verification":
        return [
            format_output_title(f"{seq} Verification"),
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
    return [format_output_title(f"{seq} {titles.get(event_type, 'Unknown event')}"), message or repr(data)]


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
    history_entries: Iterable[str] | None = None,
    execution_mode: str | None = None,
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

    buffer = create_task_buffer(accept_input, history_entries=history_entries)
    app = Application(
        layout=create_task_input_layout(buffer, status_bar, execution_mode),
        key_bindings=create_task_key_bindings(execution_mode),
        full_screen=False,
        erase_when_done=True,
        style=TASK_PROMPT_STYLE,
        cursor=CursorShape.BLINKING_BEAM,
    )
    submitted = app.run()
    if submitted != PROCESS_SHORTCUT_COMMAND:
        render_submitted_input(submitted, execution_mode)
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
