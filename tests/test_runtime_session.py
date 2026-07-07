from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from OpenCAI.__main__ import (
    RuntimeSession,
    build_parser,
    build_runtime_model_manager,
    merge_model_profiles,
    run_interactive,
    run_once,
)
from OpenCAI.composer import SkillInvocationInput
from OpenCAI.context import ContextComposer, ContextProvider
from OpenCAI.demand import DemandBrief
from OpenCAI.events import Event, final_answer, tool_call, tool_result, user_task, verification
from OpenCAI.guided import PendingGuidedReview
from OpenCAI.llm_adapter import FakeLLMAdapter, Message, ModelOutput
from OpenCAI.model_registry import ModelProfile, ModelRegistry
from OpenCAI.safety import PermissionProfile, SafetyPolicy
from OpenCAI.tools import ToolSpec


class RecordingFinalAnswerAdapter:
    def __init__(self) -> None:
        self.messages: list[Message] = []

    def call(
        self,
        messages: list[Message],
        tools: dict[str, ToolSpec],
    ) -> ModelOutput:
        self.messages = list(messages)
        return {"type": "final_answer", "answer": "done"}


class RuntimeSessionTests(unittest.TestCase):
    def test_runtime_model_manager_registers_default_profiles_and_caches_active_adapter(self) -> None:
        active_adapter = FakeLLMAdapter()
        manager = build_runtime_model_manager(
            "fake",
            active_adapter,
            api_key=None,
        )

        self.assertEqual(
            [profile.id for profile in manager.profiles()],
            [
                "fake/fake",
                "gemini/gemini-2.5-flash",
                "openai/gpt-4o-mini",
                "anthropic/claude-sonnet-4-5",
                "ollama/llama3.1",
                "deepseek/deepseek-chat",
            ],
        )
        self.assertIs(manager.resolve("fake/fake"), active_adapter)
        self.assertTrue(manager.has_adapter("fake/fake"))
        self.assertFalse(manager.has_adapter("gemini/gemini-2.5-flash"))

    def test_runtime_model_manager_registers_user_profiles(self) -> None:
        active_adapter = FakeLLMAdapter()
        manager = build_runtime_model_manager(
            "openai/gpt-4o-mini-fast",
            active_adapter,
            api_key=None,
            user_profiles=(
                ModelProfile(
                    id="openai/gpt-4o-mini-fast",
                    provider="openai",
                    model="gpt-4o-mini",
                    label="OpenAI fast",
                ),
            ),
        )

        self.assertIn("openai/gpt-4o-mini-fast", [profile.id for profile in manager.profiles()])
        self.assertIs(manager.resolve("openai/gpt-4o-mini-fast"), active_adapter)

    def test_user_profiles_override_default_profiles_by_id(self) -> None:
        profiles = merge_model_profiles(
            (
                ModelProfile(
                    id="openai/gpt-4o-mini",
                    provider="openai",
                    model="gpt-4.1-mini",
                    label="Custom OpenAI",
                ),
            )
        )

        openai_profile = next(profile for profile in profiles if profile.id == "openai/gpt-4o-mini")
        self.assertEqual(openai_profile.model, "gpt-4.1-mini")
        self.assertEqual(openai_profile.label, "Custom OpenAI")

    def test_adapter_parser_accepts_user_profile_ids(self) -> None:
        args = build_parser().parse_args(["--adapter", "openai/gpt-4o-mini-fast"])

        self.assertEqual(args.adapter, "openai/gpt-4o-mini-fast")

    def test_profile_lookup_accepts_legacy_adapter_alias(self) -> None:
        manager = build_runtime_model_manager(
            "gemini",
            FakeLLMAdapter(),
            api_key=None,
        )

        self.assertTrue(manager.has_adapter("gemini/gemini-2.5-flash"))

    def test_run_once_returns_events_and_renders_collapsed_summary(self) -> None:
        with (
            patch("OpenCAI.__main__.render_task_summary") as render_summary,
            patch("OpenCAI.__main__.LiveProcessRenderer") as renderer_class,
        ):
            events = run_once(
                "Read README",
                Path.cwd(),
                FakeLLMAdapter(),
                3,
                SafetyPolicy(),
            )

        self.assertEqual(events[0]["type"], "user_task")
        self.assertEqual(events[-1]["type"], "final_answer")
        render_summary.assert_called_once_with(events, include_submitted_task=False)
        renderer = renderer_class.return_value.__enter__.return_value
        self.assertEqual(
            [call.args[0][-1]["type"] for call in renderer.update.call_args_list],
            [event["type"] for event in events],
        )

    def test_run_once_composes_initial_context_messages(self) -> None:
        adapter = RecordingFinalAnswerAdapter()

        with (
            patch("OpenCAI.__main__.render_task_summary"),
            patch("OpenCAI.__main__.LiveProcessRenderer"),
        ):
            events = run_once(
                "Read README",
                Path.cwd(),
                adapter,
                3,
                SafetyPolicy(),
                adapter_name="fake",
                permission_profile=PermissionProfile.APPROVE_SAFE,
                context_provider=ContextProvider(user_skills_path=Path.cwd() / "missing-skills"),
                context_composer=ContextComposer(system_prompt="system rules"),
            )

        self.assertEqual(events[-1]["type"], "final_answer")
        self.assertEqual([message["role"] for message in adapter.messages[:6]], ["system", "user", "user", "user", "user", "user"])
        self.assertEqual(adapter.messages[0]["content"], "system rules")
        self.assertIn("<project_instructions", adapter.messages[1]["content"])
        self.assertIn("<global_instructions", adapter.messages[2]["content"])
        self.assertIn("<available_skills", adapter.messages[3]["content"])
        self.assertIn("<environment_context>", adapter.messages[4]["content"])
        self.assertEqual(adapter.messages[5]["content"], "Read README")

    def test_run_once_adds_explicit_skill_invocation_request(self) -> None:
        adapter = RecordingFinalAnswerAdapter()

        with (
            patch("OpenCAI.__main__.render_task_summary"),
            patch("OpenCAI.__main__.LiveProcessRenderer"),
        ):
            run_once(
                "continue workflow",
                Path.cwd(),
                adapter,
                3,
                SafetyPolicy(),
                adapter_name="fake",
                permission_profile=PermissionProfile.APPROVE_SAFE,
                context_provider=ContextProvider(user_skills_path=Path.cwd() / "missing-skills"),
                context_composer=ContextComposer(system_prompt="system rules"),
                invoked_skill=SkillInvocationInput(
                    skill_name="learn-with-dev",
                    args="continue workflow",
                    raw_text="$learn-with-dev continue workflow",
                ),
            )

        invocation_messages = [
            message for message in adapter.messages if message.get("kind") == "skill_invocation_request"
        ]
        self.assertEqual(len(invocation_messages), 1)
        self.assertIn("learn-with-dev", invocation_messages[0]["content"])
        self.assertIn("invoke_skill", invocation_messages[0]["content"])
        self.assertEqual(adapter.messages[-1]["content"], "continue workflow")

    def test_run_once_adds_demand_brief_before_current_task(self) -> None:
        adapter = RecordingFinalAnswerAdapter()
        brief = DemandBrief(
            original_task="Improve docs",
            refined_goal="Update README guided docs",
            success_criteria=("README mentions guided mode",),
        )

        with (
            patch("OpenCAI.__main__.render_task_summary"),
            patch("OpenCAI.__main__.LiveProcessRenderer"),
        ):
            run_once(
                "Update README guided docs",
                Path.cwd(),
                adapter,
                3,
                SafetyPolicy(),
                adapter_name="fake",
                permission_profile=PermissionProfile.APPROVE_SAFE,
                context_provider=ContextProvider(user_skills_path=Path.cwd() / "missing-skills"),
                context_composer=ContextComposer(system_prompt="system rules"),
                demand_brief=brief,
        )

        self.assertEqual(adapter.messages[-3]["kind"], "original_user_task")
        self.assertEqual(adapter.messages[-2]["kind"], "demand_brief")
        self.assertEqual(adapter.messages[-1]["kind"], "user_task")
        self.assertIn("Improve docs", adapter.messages[-3]["content"])
        self.assertIn("more restrictive instruction", adapter.messages[-3]["content"])
        self.assertIn("Refined goal:\nUpdate README guided docs", adapter.messages[-2]["content"])
        self.assertEqual(adapter.messages[-1]["content"], "Update README guided docs")

    def test_interactive_task_stores_last_task_events_for_process_expansion(self) -> None:
        last_events: list[Event] = [
            user_task(1, "Read README"),
            final_answer(2, "done"),
        ]
        session = RuntimeSession(
            cwd=Path.cwd(),
            adapter_name="fake",
            adapter=FakeLLMAdapter(),
            max_steps=3,
            permission_profile=PermissionProfile.APPROVE_SAFE,
        )

        with (
            patch("OpenCAI.__main__.ask_task", side_effect=["Read README", "/exit"]),
            patch("OpenCAI.__main__.run_once", return_value=last_events),
            patch("OpenCAI.__main__.handle_runtime_command", return_value=True),
        ):
            status = run_interactive(session, api_key=None)

        self.assertEqual(status, 0)
        self.assertEqual(session.last_task_events, last_events)

    def test_interactive_task_resolves_adapter_from_active_model_registry(self) -> None:
        last_events: list[Event] = [
            user_task(1, "Read README"),
            final_answer(2, "done"),
        ]
        registry = ModelRegistry()
        legacy_adapter = FakeLLMAdapter()
        active_adapter = RecordingFinalAnswerAdapter()
        registry.register(
            ModelProfile(id="legacy", provider="fake", model="fake"),
            legacy_adapter,
        )
        registry.register(
            ModelProfile(id="active", provider="fake", model="fake"),
            active_adapter,
        )
        session = RuntimeSession(
            cwd=Path.cwd(),
            adapter_name="legacy",
            adapter=legacy_adapter,
            max_steps=3,
            permission_profile=PermissionProfile.APPROVE_SAFE,
            model_registry=registry,
            active_model_id="active",
        )

        with (
            patch("OpenCAI.__main__.ask_task", side_effect=["Read README", "/exit"]),
            patch("OpenCAI.__main__.run_once", return_value=last_events) as run_once_mock,
            patch("OpenCAI.__main__.handle_runtime_command", return_value=True),
        ):
            status = run_interactive(session, api_key=None)

        self.assertEqual(status, 0)
        self.assertIs(run_once_mock.call_args.args[2], active_adapter)
        self.assertEqual(run_once_mock.call_args.kwargs["adapter_name"], "active")

    def test_interactive_skill_invocation_passes_skill_metadata_to_run_once(self) -> None:
        last_events: list[Event] = [
            user_task(1, "$learn-with-dev"),
            final_answer(2, "done"),
        ]
        session = RuntimeSession(
            cwd=Path.cwd(),
            adapter_name="fake",
            adapter=FakeLLMAdapter(),
            max_steps=3,
            permission_profile=PermissionProfile.APPROVE_SAFE,
        )

        with (
            patch("OpenCAI.__main__.ask_task", side_effect=["$learn-with-dev", "/exit"]),
            patch("OpenCAI.__main__.run_once", return_value=last_events) as run_once_mock,
            patch("OpenCAI.__main__.handle_runtime_command", return_value=True),
        ):
            status = run_interactive(session, api_key=None)

        self.assertEqual(status, 0)
        self.assertEqual(run_once_mock.call_args.args[0], "$learn-with-dev")
        self.assertEqual(run_once_mock.call_args.kwargs["invoked_skill"].skill_name, "learn-with-dev")

    def test_interactive_task_updates_session_context_summary(self) -> None:
        first_events: list[Event] = [
            user_task(1, "Read README"),
            tool_call(2, "read_file", {"path": "README.md"}),
            tool_result(
                3,
                "read_file",
                True,
                {"content": "x" * 5000, "path": "README.md"},
            ),
            verification(4, "python -m unittest discover tests", 0, stdout="ok"),
            final_answer(5, "README was read."),
        ]
        second_events: list[Event] = [
            user_task(1, "Continue"),
            final_answer(2, "continued"),
        ]
        session = RuntimeSession(
            cwd=Path.cwd(),
            adapter_name="fake",
            adapter=FakeLLMAdapter(),
            max_steps=3,
            permission_profile=PermissionProfile.APPROVE_SAFE,
        )

        with (
            patch("OpenCAI.__main__.ask_task", side_effect=["Read README", "Continue", "/exit"]),
            patch("OpenCAI.__main__.run_once", side_effect=[first_events, second_events]) as run_once_mock,
            patch("OpenCAI.__main__.handle_runtime_command", return_value=True),
        ):
            status = run_interactive(session, api_key=None)

        self.assertEqual(status, 0)
        self.assertEqual(session.session_context.recent_turns[-1].user_task, "Continue")
        self.assertEqual(session.session_context.recent_turns[0].final_answer, "README was read.")
        self.assertIn("read_file", session.session_context.recent_turns[0].tool_calls)
        self.assertNotIn("x" * 100, session.session_context.render())
        self.assertIs(run_once_mock.call_args_list[1].kwargs["session_context"], session.session_context)

    def test_interactive_process_shortcut_handoff_uses_runtime_command_path(self) -> None:
        session = RuntimeSession(
            cwd=Path.cwd(),
            adapter_name="fake",
            adapter=FakeLLMAdapter(),
            max_steps=3,
            permission_profile=PermissionProfile.APPROVE_SAFE,
        )

        with (
            patch("OpenCAI.__main__.ask_task", side_effect=["/process", "/exit"]),
            patch("OpenCAI.__main__.handle_runtime_command", side_effect=[False, True]) as handle_command,
        ):
            status = run_interactive(session, api_key=None)

        self.assertEqual(status, 0)
        self.assertEqual(handle_command.call_args_list[0].args[1], "/process")
        self.assertEqual(handle_command.call_args_list[1].args[1], "/exit")

    def test_interactive_workflow_command_uses_workflow_flow(self) -> None:
        session = RuntimeSession(
            cwd=Path.cwd(),
            adapter_name="fake",
            adapter=FakeLLMAdapter(),
            max_steps=3,
            permission_profile=PermissionProfile.APPROVE_SAFE,
        )

        with (
            patch("OpenCAI.__main__.ask_task", side_effect=["/workflow Read README", "/exit"]),
            patch("OpenCAI.__main__.handle_workflow_command") as handle_workflow,
            patch("OpenCAI.__main__.handle_runtime_command", return_value=True) as handle_command,
            patch("OpenCAI.__main__.run_once") as run_once_mock,
        ):
            status = run_interactive(session, api_key=None)

        self.assertEqual(status, 0)
        handle_workflow.assert_called_once_with(session, "Read README")
        run_once_mock.assert_not_called()
        self.assertEqual(handle_command.call_args.args[1], "/exit")

    def test_interactive_plain_task_uses_workflow_flow_in_workflow_mode(self) -> None:
        session = RuntimeSession(
            cwd=Path.cwd(),
            adapter_name="fake",
            adapter=FakeLLMAdapter(),
            max_steps=3,
            permission_profile=PermissionProfile.APPROVE_SAFE,
            execution_mode="workflow",
        )

        with (
            patch("OpenCAI.__main__.ask_task", side_effect=["Read README", "/exit"]) as ask_task,
            patch("OpenCAI.__main__.handle_workflow_command") as handle_workflow,
            patch("OpenCAI.__main__.handle_runtime_command", return_value=True),
            patch("OpenCAI.__main__.run_once") as run_once_mock,
        ):
            status = run_interactive(session, api_key=None)

        self.assertEqual(status, 0)
        self.assertEqual(ask_task.call_args.kwargs["execution_mode"], "workflow")
        handle_workflow.assert_called_once_with(session, "Read README")
        run_once_mock.assert_not_called()

    def test_interactive_plain_task_creates_and_handles_pending_guided_review(self) -> None:
        last_events: list[Event] = [
            user_task(1, "Read README"),
            final_answer(2, "done"),
        ]
        pending = PendingGuidedReview(
            original_task="Read README",
            demand_brief=DemandBrief(
                original_task="Read README",
                refined_goal="Read README",
                success_criteria=("README is read.",),
            ),
        )
        session = RuntimeSession(
            cwd=Path.cwd(),
            adapter_name="fake",
            adapter=FakeLLMAdapter(),
            max_steps=3,
            permission_profile=PermissionProfile.APPROVE_SAFE,
            execution_mode="guided",
        )

        with (
            patch("OpenCAI.__main__.ask_task", side_effect=["Read README", "/exit"]) as ask_task,
            patch("OpenCAI.__main__.start_guided_review", return_value=pending) as start_guided,
            patch("OpenCAI.__main__.handle_pending_guided_review", return_value=(None, last_events)) as handle_pending,
            patch("OpenCAI.__main__.handle_workflow_command") as handle_workflow,
            patch("OpenCAI.__main__.handle_runtime_command", return_value=True),
            patch("OpenCAI.__main__.run_once") as run_once_mock,
        ):
            status = run_interactive(session, api_key=None)

        self.assertEqual(status, 0)
        self.assertEqual(ask_task.call_args.kwargs["execution_mode"], "guided")
        self.assertEqual(session.last_task_events, last_events)
        self.assertIsNone(session.pending_guided_review)
        start_guided.assert_called_once_with(session, "Read README")
        handle_pending.assert_called_once()
        self.assertIs(handle_pending.call_args.args[1], pending)
        handle_workflow.assert_not_called()
        run_once_mock.assert_not_called()

    def test_interactive_pending_guided_review_is_handled_before_next_task_input(self) -> None:
        pending = PendingGuidedReview(
            original_task="Improve docs",
            demand_brief=DemandBrief(
                original_task="Improve docs",
                refined_goal="Update README",
                success_criteria=("README updated.",),
            ),
        )
        session = RuntimeSession(
            cwd=Path.cwd(),
            adapter_name="fake",
            adapter=FakeLLMAdapter(),
            max_steps=3,
            permission_profile=PermissionProfile.APPROVE_SAFE,
            execution_mode="guided",
            pending_guided_review=pending,
        )

        with (
            patch("OpenCAI.__main__.ask_task", side_effect=["/exit"]) as ask_task,
            patch("OpenCAI.__main__.handle_pending_guided_review", return_value=(None, [])) as handle_pending,
            patch("OpenCAI.__main__.handle_runtime_command", return_value=True),
        ):
            status = run_interactive(session, api_key=None)

        self.assertEqual(status, 0)
        handle_pending.assert_called_once()
        ask_task.assert_called_once()
        self.assertIsNone(session.pending_guided_review)

    def test_interactive_workflow_command_without_task_does_not_run_workflow(self) -> None:
        session = RuntimeSession(
            cwd=Path.cwd(),
            adapter_name="fake",
            adapter=FakeLLMAdapter(),
            max_steps=3,
            permission_profile=PermissionProfile.APPROVE_SAFE,
        )

        with (
            patch("OpenCAI.__main__.ask_task", side_effect=["/workflow", "/exit"]),
            patch("OpenCAI.__main__.handle_workflow_command") as handle_workflow,
            patch("OpenCAI.__main__.handle_runtime_command", return_value=True),
        ):
            status = run_interactive(session, api_key=None)

        self.assertEqual(status, 0)
        handle_workflow.assert_called_once_with(session, "")


if __name__ == "__main__":
    unittest.main()
