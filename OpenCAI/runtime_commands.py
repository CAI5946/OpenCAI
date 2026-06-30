from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from OpenCAI.llm_adapter import LLMAdapter, LLMAdapterError
from OpenCAI.safety import PermissionProfile
from OpenCAI.workflow import (
    SerialWorkflowRunner,
    build_inspect_handoff_workflow,
    render_workflow_plan,
    render_workflow_process,
)


AdapterFactory = Callable[[str, str | None], LLMAdapter]
ChoiceProvider = Callable[[str, tuple[str, ...], str | None], str | None]


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
    print("Runtime status")
    print(f"  cwd: {session.cwd}")
    print(f"  model: {session.adapter_name}")
    print(f"  max_steps: {session.max_steps}")
    print(f"  permission: {session.permission_profile.value}")
    print(f"  turns: {session.turn_count}")


def render_runtime_help() -> None:
    print("Runtime commands")
    for command in RUNTIME_COMMANDS:
        suffix = f" {command.args_hint}" if command.args_hint else ""
        print(f"  {command.name}{suffix} - {command.description}")
    print()
    print("Input modes")
    print("  plain text - send a task to the agent loop")
    print("  !command - run a user shell command and show stdout/stderr/exit code")


def handle_workflow_command(session: Any, task: str) -> None:
    spec = build_inspect_handoff_workflow()
    print(f"Workflow task: {task}")
    print(render_workflow_plan(spec))

    runner = SerialWorkflowRunner(
        cwd=session.cwd,
        adapter=session.adapter,
        max_steps=session.max_steps,
        policy=session.build_policy(),
    )
    workflow_run = runner.run(spec, task)

    print()
    print(render_workflow_process(workflow_run))


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
    if command == "/process":
        last_task_events = getattr(session, "last_task_events", [])
        if not last_task_events:
            print("No process transcript yet.")
            return False
        from OpenCAI.tui import show_process_view

        show_process_view(last_task_events)
        return False
    if command == "/workflow":
        if len(parts) < 2:
            print("Usage: /workflow TASK")
            return False
        task = raw_input.split(maxsplit=1)[1].strip()
        if not task:
            print("Usage: /workflow TASK")
            return False
        handle_workflow_command(session, task)
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
