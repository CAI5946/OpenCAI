from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from OpenCAI.adapter_factory import profile_from_adapter_name
from OpenCAI.llm_config import save_env_value, save_model_profile
from OpenCAI.llm_adapter import LLMAdapter, LLMAdapterError
from OpenCAI.model_discovery import list_provider_models
from OpenCAI.model_setup import MODEL_ADD_PROVIDER_CHOICES, PROVIDER_DEFAULTS, build_default_model_profile
from OpenCAI.model_smoke import run_model_smoke
from OpenCAI.model_registry import ModelProfile, ModelRegistryError
from OpenCAI.output_format import format_output_title
from OpenCAI.safety import PermissionProfile
from OpenCAI.workflow.commands import handle_workflow_command


AdapterFactory = Callable[[str, str | None], LLMAdapter]
ChoiceProvider = Callable[[str, tuple[str, ...], str | None], str | None]
TextProvider = Callable[[str, str, str], str | None]
EXECUTION_MODES = ("agent", "guided", "workflow")
EXECUTION_MODE_USAGE = "[agent|guided|workflow]"

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
    RuntimeCommand("/model", "Switch the model adapter for new turns.", inline_choices=False),
    RuntimeCommand("/model-add", "Add a model profile from provider discovery.", "[PROVIDER] [MODEL]"),
    RuntimeCommand("/model-test", "Run a no-tool smoke check for the active model."),
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
    print(f"  model: {_current_model_id(session)}")
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
    text_provider: TextProvider | None = None,
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
    if command == "/model-test":
        if len(parts) != 1:
            print("Usage: /model-test")
            return False
        try:
            adapter = _resolve_current_adapter(session)
        except (LLMAdapterError, ModelRegistryError) as exc:
            print(f"Model smoke failed for {_current_model_id(session)}: {exc}")
            return False
        result = run_model_smoke(adapter)
        if result.ok:
            print(f"Model smoke passed for {_current_model_id(session)} ({result.output_type}).")
        else:
            print(f"Model smoke failed for {_current_model_id(session)}: {result.error}")
        return False
    if command == "/model-add":
        return _handle_model_add(session, parts, choice_provider, text_provider)
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
                print(f"Usage: /mode {EXECUTION_MODE_USAGE}")
                return False
            selected_mode = choice_provider("Mode", EXECUTION_MODES, current_mode)
            if selected_mode not in EXECUTION_MODES:
                print("mode selection cancelled.")
                return False
        elif len(parts) == 2 and parts[1] in EXECUTION_MODES:
            selected_mode = parts[1]
        else:
            print(f"Usage: /mode {EXECUTION_MODE_USAGE}")
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
        model_choices = _model_choices(session)
        if len(parts) == 1:
            if choice_provider is None:
                print(f"Usage: /model [{_format_choices(model_choices)}]")
                return False
            selected_model = choice_provider("Model", model_choices, _current_model_id(session))
            if selected_model not in model_choices:
                print("model selection cancelled.")
                return False
        elif len(parts) == 2:
            selected_model = _resolve_model_choice(parts[1], model_choices)
            if selected_model is None:
                print(f"Usage: /model [{_format_choices(model_choices)}]")
                return False
        else:
            print(f"Usage: /model [{_format_choices(model_choices)}]")
            return False
        model_registry = getattr(session, "model_registry", None)
        if model_registry is not None:
            try:
                selected_adapter = model_registry.resolve(selected_model)
            except LLMAdapterError as exc:
                print(f"OpenCAI adapter error: {exc}")
                return False
            except ModelRegistryError:
                try:
                    selected_adapter = adapter_factory(selected_model, api_key)
                except LLMAdapterError as exc:
                    print(f"OpenCAI adapter error: {exc}")
                    return False
                try:
                    profile = profile_from_adapter_name(selected_model)
                    model_registry.register(
                        profile,
                        selected_adapter,
                    )
                except (LLMAdapterError, ModelRegistryError) as exc:
                    print(f"OpenCAI model registry error: {exc}")
                    return False
        else:
            try:
                selected_adapter = adapter_factory(selected_model, api_key)
            except LLMAdapterError as exc:
                print(f"OpenCAI adapter error: {exc}")
                return False
        session.adapter_name = selected_model
        session.adapter = selected_adapter
        if hasattr(session, "active_model_id"):
            session.active_model_id = selected_model
        print(f"Model changed to {selected_model}")
        return False

    print(f"Unknown runtime command: {raw_input}")
    print("Run /help to list commands.")
    return False


def _current_model_id(session: Any) -> str:
    return str(getattr(session, "active_model_id", "") or getattr(session, "adapter_name", "unknown"))


def _model_choices(session: Any) -> tuple[str, ...]:
    choices: list[str] = []
    model_registry = getattr(session, "model_registry", None)
    if model_registry is not None:
        choices.extend(profile.id for profile in model_registry.profiles())
    return tuple(choices)


def _format_choices(choices: tuple[str, ...]) -> str:
    return "|".join(choices) if choices else "MODEL"


def _resolve_model_choice(raw_model: str, choices: tuple[str, ...]) -> str | None:
    if raw_model in choices:
        return raw_model
    try:
        legacy_profile = profile_from_adapter_name(raw_model)
    except LLMAdapterError:
        return None
    return legacy_profile.id if legacy_profile.id in choices else None


def _resolve_current_adapter(session: Any) -> LLMAdapter:
    model_registry = getattr(session, "model_registry", None)
    if model_registry is not None:
        return model_registry.resolve(_current_model_id(session))
    adapter = getattr(session, "adapter", None)
    if adapter is None:
        raise LLMAdapterError("No active adapter.")
    return adapter


def _handle_model_add(
    session: Any,
    parts: list[str],
    choice_provider: ChoiceProvider | None,
    text_provider: TextProvider | None,
) -> bool:
    if len(parts) > 3:
        print(f"Usage: /model-add [{_format_choices(MODEL_ADD_PROVIDER_CHOICES)}] [MODEL]")
        return False

    provider = parts[1] if len(parts) >= 2 else ""
    selected_model = parts[2] if len(parts) == 3 else ""
    if not provider:
        if choice_provider is None:
            print(f"Usage: /model-add [{_format_choices(MODEL_ADD_PROVIDER_CHOICES)}] [MODEL]")
            return False
        provider = choice_provider("Provider", MODEL_ADD_PROVIDER_CHOICES, None) or ""
    if provider not in MODEL_ADD_PROVIDER_CHOICES:
        print(f"Usage: /model-add [{_format_choices(MODEL_ADD_PROVIDER_CHOICES)}] [MODEL]")
        return False

    defaults = PROVIDER_DEFAULTS[provider]
    base_url = defaults.base_url
    if provider == "openai-compatible":
        if text_provider is None:
            print("openai-compatible requires model and base_url input.")
            return False
        base_url = (text_provider("Base URL", "Base URL for the OpenAI-compatible endpoint", "") or "").strip()
        if not selected_model:
            selected_model = (text_provider("Model", "Model name for the OpenAI-compatible endpoint", "") or "").strip()

    api_key = ""
    if defaults.api_key_env:
        api_key = os.environ.get(defaults.api_key_env, "")
        if not api_key:
            if text_provider is None:
                print(f"{provider} requires API key input.")
                return False
            api_key = (text_provider("API key", f"API key for {provider}", "") or "").strip()
            if not api_key:
                print(f"{provider} API key setup cancelled.")
                return False
            save_env_value(_env_file_path(session), defaults.api_key_env, api_key)
            os.environ[defaults.api_key_env] = api_key

    if not selected_model:
        selected_model = _select_discovered_model(provider, api_key, base_url, choice_provider, text_provider)
        if not selected_model:
            print("model selection cancelled.")
            return False

    try:
        profile = build_default_model_profile(
            provider,
            _existing_model_ids(session),
            model=selected_model,
            base_url=base_url,
        )
        save_model_profile(_model_config_path(session), profile)
        _register_profile(session, profile)
    except ModelRegistryError as exc:
        print(f"OpenCAI model registry error: {exc}")
        return False

    print(f"Model profile added: {profile.id} ({profile.provider} {profile.model})")
    print(f"Config: {_model_config_path(session)}")
    print(f"Run /model {profile.id} then /model-test.")
    return False


def _select_discovered_model(
    provider: str,
    api_key: str,
    base_url: str,
    choice_provider: ChoiceProvider | None,
    text_provider: TextProvider | None,
) -> str | None:
    model_choices: tuple[str, ...] = ()
    try:
        discovered = list_provider_models(provider, api_key=api_key, base_url=base_url)
        model_choices = tuple(model.id for model in discovered)
    except LLMAdapterError as exc:
        print(f"Could not fetch models for {provider}: {exc}")

    if model_choices and choice_provider is not None:
        selected = choice_provider("Model", model_choices + ("custom",), None)
        if selected and selected != "custom":
            return selected

    if text_provider is None:
        return None
    return (text_provider("Model", f"Model name for {provider}", "") or "").strip() or None


def _existing_model_ids(session: Any) -> tuple[str, ...]:
    return _model_choices(session)


def _model_config_path(session: Any) -> Path:
    return Path(getattr(session, "model_config_path", Path(".opencai") / "models.json"))


def _env_file_path(session: Any) -> Path:
    return Path(getattr(session, "env_file_path", Path(".env")))


def _register_profile(session: Any, profile: ModelProfile) -> None:
    model_registry = getattr(session, "model_registry", None)
    if model_registry is None:
        return
    if hasattr(model_registry, "register_profile"):
        model_registry.register_profile(profile)
