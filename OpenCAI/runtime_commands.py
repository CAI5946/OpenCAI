from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from OpenCAI.llm_adapter import LLMAdapter, LLMAdapterError
from OpenCAI.output_format import format_output_title
from OpenCAI.safety import PermissionProfile
from OpenCAI.workflow_commands import handle_workflow_command


AdapterFactory = Callable[[str, str | None], LLMAdapter]
ChoiceProvider = Callable[[str, tuple[str, ...], str | None], str | None]
EXECUTION_MODES = ("agent", "workflow")


@dataclass(frozen=True)
class RuntimeCommand:
    name: str
    description: str
    args_hint: str = ""
    choices: tuple[str, ...] = ()
    inline_choices: bool = True


RUNTIME_COMMANDS: tuple[RuntimeCommand, ...] = (
    RuntimeCommand("/help", "Show available runtime commands."),
    RuntimeCommand("/status", "Show current runtime session settings."),
    RuntimeCommand("/model", "Switch the model adapter for new turns.", choices=("fake", "gemini"), inline_choices=False),
    RuntimeCommand("/keymap", "Show keyboard shortcuts."),
    RuntimeCommand("/mode", "Switch the default execution mode.", choices=EXECUTION_MODES, inline_choices=False),
    RuntimeCommand("/max-steps", "Set the max model-turn fallback budget for one task.", "N"),
    RuntimeCommand(
        "/permission",
        "Set the permission profile for model-initiated tools.",
        "",
        tuple(profile.value for profile in PermissionProfile),
        inline_choices=False,
    ),
    RuntimeCommand("/process", "Expand the last task process."),
    RuntimeCommand("/workflow", "Run the built-in workflow for a task.", "TASK"),
    RuntimeCommand("/exit", "Exit interactive mode."),
)


KEYMAP_SECTIONS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "Session",
        (
            ("Ctrl+D", "Exit interactive mode"),
            ("Ctrl+L", "Redraw the input screen"),
            ("Ctrl+O", "Open the last task process view"),
            ("Ctrl+C", "Interrupt or cancel the active view"),
        ),
    ),
    (
        "Input editing",
        (
            ("Home / End", "Move to the start or end of input"),
            ("Ctrl+A / Ctrl+E", "Move to the start or end of the current line"),
            ("Ctrl+K / Ctrl+U", "Delete to line end or line start"),
            ("Ctrl+W / Ctrl+Y", "Delete previous word or paste deleted text"),
            ("Alt+B / Alt+F", "Move back or forward by word"),
            ("Left / Right", "Move cursor left or right"),
        ),
    ),
    (
        "Completion and history",
        (
            ("Tab", "Accept a visible suggestion"),
            ("Enter", "Accept an exact suggestion or submit input"),
            ("Esc", "Dismiss suggestions"),
            ("Up / Down", "Navigate suggestions, or history when suggestions are hidden"),
            ("Ctrl+R", "Search prompt history"),
        ),
    ),
    (
        "Multiline",
        (
            ("Ctrl+J", "Insert a newline without submitting"),
            ("Shift+Enter", "Insert newline when terminal sends a distinguishable modified Enter"),
        ),
    ),
    (
        "Quick entries",
        (
            ("/", "Open runtime command suggestions"),
            ("!", "Run shell mode"),
            ("$", "Invoke a skill"),
            ("Alt+P", "Open model selection"),
            ("Shift+Tab", "Cycle execution mode"),
        ),
    ),
    (
        "Process view",
        (
            ("Ctrl+O / Esc / Enter / q / Ctrl+C", "Close process view"),
            ("PageUp / PageDown", "Scroll process view"),
            ("Home / End", "Jump to start or end of process view"),
        ),
    ),
)


def render_keymap_text() -> str:
    lines = [format_output_title("Keyboard shortcuts"), ""]
    for title, shortcuts in KEYMAP_SECTIONS:
        lines.append(title)
        for key, description in shortcuts:
            lines.append(f"  {key} - {description}")
        lines.append("")
    return "\n".join(lines).rstrip()


def runtime_command_completion_tree() -> dict[str, Any]:
    tree: dict[str, Any] = {}
    for command in RUNTIME_COMMANDS:
        tree[command.name] = (
            {choice: None for choice in command.choices}
            if command.choices and command.inline_choices
            else None
        )
    return tree


def render_runtime_status(session: Any) -> None:
    print(format_output_title("Runtime status"))
    print(f"  cwd: {session.cwd}")
    print(f"  model: {session.adapter_name}")
    print(f"  mode: {getattr(session, 'execution_mode', 'agent')}")
    print(f"  max_steps: {session.max_steps}")
    print(f"  permission: {session.permission_profile.value}")
    print(f"  turns: {session.turn_count}")


def render_runtime_help() -> None:
    print(format_output_title("Runtime commands"))
    for command in RUNTIME_COMMANDS:
        suffix = f" {command.args_hint}" if command.args_hint else ""
        print(f"  {command.name}{suffix} - {command.description}")
    print()
    print(format_output_title("Input modes"))
    print("  plain text - send a task to the current execution mode")
    print("  !command - run a user shell command and show stdout/stderr/exit code")


def handle_runtime_command(
    session: Any,
    raw_input: str,
    api_key: str | None,
    adapter_factory: AdapterFactory,
    choice_provider: ChoiceProvider | None = None,
) -> bool:
    parts = raw_input.split()
    command = parts[0].lower() if parts else ""

    if command == "/exit":
        return True
    if command == "/help":
        render_runtime_help()
        return False
    if command == "/status":
        render_runtime_status(session)
        return False
    if command == "/keymap":
        if len(parts) != 1:
            print("Usage: /keymap")
            return False
        from OpenCAI import tui

        if tui.sys.stdin.isatty():
            tui.show_keymap_view()
        else:
            print(render_keymap_text())
        return False
    if command == "/process":
        last_task_events = getattr(session, "last_task_events", [])
        if not last_task_events:
            print("No process transcript yet.")
            return False
        from OpenCAI.tui import show_process_view

        show_process_view(last_task_events)
        return False
    if command == "/workflow":
        task = raw_input.split(maxsplit=1)[1].strip() if len(parts) >= 2 else ""
        handle_workflow_command(session, task)
        return False

    if command == "/mode":
        current_mode = str(getattr(session, "execution_mode", "agent"))
        if len(parts) == 1:
            if choice_provider is None:
                print("Usage: /mode [agent|workflow]")
                return False
            selected_mode = choice_provider("Mode", EXECUTION_MODES, current_mode)
            if selected_mode not in EXECUTION_MODES:
                print("mode selection cancelled.")
                return False
        elif len(parts) == 2 and parts[1] in EXECUTION_MODES:
            selected_mode = parts[1]
        else:
            print("Usage: /mode [agent|workflow]")
            return False
        session.execution_mode = selected_mode
        print(f"Mode changed to {session.execution_mode}")
        return False

    if command == "/max-steps":
        if len(parts) != 2:
            print("Usage: /max-steps N")
            return False
        try:
            max_steps = int(parts[1])
        except ValueError:
            print("max_steps must be an integer.")
            return False
        if max_steps < 1:
            print("max_steps must be >= 1.")
            return False
        session.max_steps = max_steps
        print(f"max_steps: {session.max_steps}")
        return False

    if command == "/permission":
        profile_choices = tuple(profile.value for profile in PermissionProfile)
        if len(parts) == 1:
            if choice_provider is None:
                print("Usage: /permission [PROFILE]")
                return False
            selected_profile = choice_provider("Permission", profile_choices, session.permission_profile.value)
            if selected_profile not in profile_choices:
                print("permission selection cancelled.")
                return False
        elif len(parts) == 2:
            selected_profile = parts[1]
        else:
            print("Usage: /permission [PROFILE]")
            return False
        try:
            session.permission_profile = PermissionProfile.from_cli_value(selected_profile)
        except ValueError:
            print("Usage: /permission [PROFILE]")
            return False
        print(f"Permission changed to {session.permission_profile.value}")
        return False

    if command == "/model":
        model_choices = ("fake", "gemini")
        if len(parts) == 1:
            if choice_provider is None:
                print("Usage: /model [fake|gemini]")
                return False
            selected_model = choice_provider("Model", model_choices, session.adapter_name)
            if selected_model not in model_choices:
                print("model selection cancelled.")
                return False
        elif len(parts) == 2 and parts[1] in model_choices:
            selected_model = parts[1]
        else:
            print("Usage: /model [fake|gemini]")
            return False
        try:
            session.adapter = adapter_factory(selected_model, api_key)
        except LLMAdapterError as exc:
            print(f"OpenCAI adapter error: {exc}")
            return False
        session.adapter_name = selected_model
        print(f"Model changed to {session.adapter_name}")
        return False

    print(f"Unknown runtime command: {raw_input}")
    print("Run /help to list commands.")
    return False
