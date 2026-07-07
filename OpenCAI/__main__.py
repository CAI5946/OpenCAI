from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path

from OpenCAI import __version__
from OpenCAI.adapter_factory import AdapterFactory, profile_from_adapter_name
from OpenCAI.agent_loop import iter_agent_loop
from OpenCAI.composer import (
    RuntimeCommandInput,
    ShellInput,
    SkillInvocationInput,
    WorkflowCommandInput,
    parse_user_input,
)
from OpenCAI.context import ContextComposer, ContextProvider
from OpenCAI.demand import DemandBrief
from OpenCAI.events import Event
from OpenCAI.guided import PendingGuidedReview, handle_pending_guided_review, start_guided_review
from OpenCAI.llm_adapter import LLMAdapter, LLMAdapterError
from OpenCAI.model_manager import ModelManager
from OpenCAI.model_registry import ModelProfile, ModelRegistryError
from OpenCAI.output_format import format_output_title
from OpenCAI.runtime_commands import handle_runtime_command
from OpenCAI.safety import PermissionProfile, SafetyPolicy
from OpenCAI.session_context import SessionContext
from OpenCAI.shell_mode import run_user_shell_command
from OpenCAI.workflow.commands import handle_workflow_command
from OpenCAI.tui import (
    INPUT_PROMPT_LABEL,
    ask_choice,
    ask_task,
    LiveProcessRenderer,
    render_startup,
    render_status_bar,
    render_task_summary,
    render_transcript,
)


DEFAULT_TASK = "Fix the failing toy project test"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PROFILE_NAMES = ("fake", "gemini", "openai", "anthropic", "ollama", "deepseek")


@dataclass
class RuntimeSession:
    cwd: Path
    adapter_name: str
    adapter: LLMAdapter
    max_steps: int
    permission_profile: PermissionProfile
    model_registry: ModelManager = field(default_factory=ModelManager)
    active_model_id: str = ""
    execution_mode: str = "agent"
    turn_count: int = 0
    task_history: list[str] = field(default_factory=list)
    last_task_events: list[Event] = field(default_factory=list)
    session_context: SessionContext = field(default_factory=SessionContext)
    pending_guided_review: PendingGuidedReview | None = None

    def __post_init__(self) -> None:
        if not self.active_model_id:
            self.active_model_id = self.adapter_name
        try:
            self.model_registry.profile(self.active_model_id)
        except ModelRegistryError:
            try:
                profile = profile_from_adapter_name(self.adapter_name)
                if profile.id != self.active_model_id:
                    profile = ModelProfile(
                        id=self.active_model_id,
                        provider=profile.provider,
                        model=profile.model,
                        label=profile.label,
                    )
            except LLMAdapterError:
                profile = ModelProfile(
                    id=self.active_model_id,
                    provider=self.adapter_name,
                    model=self.adapter_name,
                )
            self.model_registry.register(
                profile,
                self.adapter,
            )

    def build_policy(self) -> SafetyPolicy:
        return SafetyPolicy(profile=self.permission_profile)

    def resolve_active_adapter(self) -> LLMAdapter:
        return self.model_registry.resolve(self.active_model_id)


def build_adapter(adapter_name: str, api_key: str | None) -> LLMAdapter:
    return AdapterFactory().build(profile_from_adapter_name(adapter_name), None)


def build_runtime_model_manager(
    active_adapter_name: str,
    active_adapter: LLMAdapter,
    api_key: str | None,
) -> ModelManager:
    manager = ModelManager(api_key=None)
    active_profile = profile_from_adapter_name(active_adapter_name)
    for profile_name in DEFAULT_MODEL_PROFILE_NAMES:
        profile = profile_from_adapter_name(profile_name)
        if profile.id == active_profile.id:
            manager.register_adapter(profile, active_adapter)
        else:
            manager.register_profile(profile)
    return manager


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opencai",
        description="Interactive runtime for the OpenCAI learning agent.",
    )
    parser.add_argument(
        "--task",
        default="",
        help="Run one natural language task and exit. Omit to start interactive mode.",
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Workspace directory for the agent loop.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show resolved runtime inputs without running the loop.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"OpenCAI {__version__}",
    )
    parser.add_argument(
        "--adapter",
        choices=list(DEFAULT_MODEL_PROFILE_NAMES),
        default="gemini",
        help="Choose the model adapter. Gemini requires google-genai and GEMINI_API_KEY.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=8,
        help="Maximum model turns for one task. Kept as max_steps for CLI compatibility.",
    )
    parser.add_argument(
        "--permission",
        choices=[profile.value for profile in PermissionProfile],
        default=PermissionProfile.APPROVE_SAFE.value,
        help="Permission profile for model-initiated tools.",
    )
    return parser


def run_once(
    task: str,
    cwd: Path,
    adapter: LLMAdapter,
    max_steps: int,
    policy: SafetyPolicy,
    *,
    include_submitted_task: bool = False,
    adapter_name: str = "unknown",
    permission_profile: PermissionProfile | None = None,
    context_provider: ContextProvider | None = None,
    context_composer: ContextComposer | None = None,
    session_context: SessionContext | None = None,
    invoked_skill: SkillInvocationInput | None = None,
    demand_brief: DemandBrief | None = None,
) -> list[Event]:
    active_permission_profile = permission_profile or policy.profile
    provider = context_provider or ContextProvider()
    composer = context_composer or ContextComposer()
    snapshot = provider.collect(
        cwd=cwd,
        adapter_name=adapter_name,
        permission_profile=active_permission_profile.value,
        max_steps=max_steps,
    )
    initial_messages = composer.compose(
        snapshot,
        task,
        invoked_skill=invoked_skill,
        session_context=session_context,
        demand_brief=demand_brief,
    )

    events: list[Event] = []
    with LiveProcessRenderer() as live_process:
        for event in iter_agent_loop(
            task,
            cwd=cwd,
            adapter=adapter,
            max_steps=max_steps,
            policy=policy,
            initial_messages=initial_messages,
        ):
            events.append(event)
            live_process.update(list(events))
    render_task_summary(events, include_submitted_task=include_submitted_task)
    return events


def run_interactive(session: RuntimeSession, api_key: str | None) -> int:
    while True:
        if session.pending_guided_review is not None:
            pending, events = handle_pending_guided_review(
                session,
                session.pending_guided_review,
                execute_task=lambda refined_task, demand_brief: _execute_guided_task(
                    session,
                    refined_task,
                    demand_brief,
                ),
            )
            session.pending_guided_review = pending
            if events:
                session.last_task_events = events
                session.session_context.add_turn_events(events)
            continue

        raw_input = ask_task(
            label=INPUT_PROMPT_LABEL,
            status_bar=render_status_bar(session),
            history_entries=session.task_history,
            execution_mode=session.execution_mode,
        )
        parsed_input = parse_user_input(raw_input)
        if parsed_input is None:
            continue
        if isinstance(parsed_input, RuntimeCommandInput):
            if handle_runtime_command(session, parsed_input.text, api_key, build_adapter, ask_choice):
                return 0
            continue
        if isinstance(parsed_input, WorkflowCommandInput):
            handle_workflow_command(session, parsed_input.task)
            continue
        if isinstance(parsed_input, ShellInput):
            render_transcript(
                run_user_shell_command(
                    parsed_input.command,
                    session.cwd,
                    session.build_policy(),
                )
            )
            continue

        invoked_skill = parsed_input if isinstance(parsed_input, SkillInvocationInput) else None
        task = (
            (parsed_input.args or parsed_input.raw_text)
            if invoked_skill is not None
            else parsed_input.text
        )
        if invoked_skill is None and session.execution_mode == "workflow":
            session.task_history.append(task)
            handle_workflow_command(session, task)
            continue
        if invoked_skill is None and session.execution_mode == "guided":
            session.task_history.append(task)
            session.turn_count += 1
            session.pending_guided_review = start_guided_review(session, task)
            continue
        session.task_history.append(task)
        session.turn_count += 1
        session.last_task_events = run_once(
            task,
            session.cwd,
            session.resolve_active_adapter(),
            session.max_steps,
            session.build_policy(),
            adapter_name=session.active_model_id,
            permission_profile=session.permission_profile,
            session_context=session.session_context,
            invoked_skill=invoked_skill,
        )
        session.session_context.add_turn_events(session.last_task_events)


def _execute_guided_task(
    session: RuntimeSession,
    refined_task: str,
    demand_brief: DemandBrief,
) -> list[Event]:
    return run_once(
        refined_task,
        session.cwd,
        session.resolve_active_adapter(),
        session.max_steps,
        session.build_policy(),
        adapter_name=session.active_model_id,
        permission_profile=session.permission_profile,
        session_context=session.session_context,
        demand_brief=demand_brief,
    )


def main() -> int:
    load_env_file(PROJECT_ROOT / ".env")

    parser = build_parser()
    args = parser.parse_args()

    cwd = Path(args.cwd).resolve()
    permission_profile = PermissionProfile.from_cli_value(args.permission)
    if args.dry_run:
        print(format_output_title("OpenCAI runtime"))
        print(f"task: {args.task or '(interactive)'}")
        print(f"cwd: {cwd}")
        print(f"model: {args.adapter}")
        print(f"max_steps: {args.max_steps}")
        print(f"permission: {permission_profile.value}")
        print("dry_run: true")
        return 0

    try:
        adapter = build_adapter(args.adapter, os.environ.get("GEMINI_API_KEY"))
    except LLMAdapterError as exc:
        print(f"OpenCAI adapter error: {exc}")
        return 1

    render_startup(
        mode="Productized CLI",
        status=f"{type(adapter).__name__} + interactive task input",
    )

    policy = SafetyPolicy(profile=permission_profile)

    if args.task:
        run_once(
            args.task,
            cwd,
            adapter,
            args.max_steps,
            policy,
            include_submitted_task=True,
            adapter_name=args.adapter,
            permission_profile=permission_profile,
        )
        return 0

    session = RuntimeSession(
        cwd=cwd,
        adapter_name=args.adapter,
        adapter=adapter,
        max_steps=args.max_steps,
        permission_profile=permission_profile,
        model_registry=build_runtime_model_manager(
            args.adapter,
            adapter,
            os.environ.get("GEMINI_API_KEY"),
        ),
    )
    return run_interactive(session, os.environ.get("GEMINI_API_KEY"))


if __name__ == "__main__":
    raise SystemExit(main())
