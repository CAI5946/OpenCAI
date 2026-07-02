from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from OpenCAI.__main__ import RuntimeSession, run_interactive, run_once
from OpenCAI.context import ContextComposer, ContextProvider
from OpenCAI.events import Event, final_answer, tool_call, tool_result, user_task, verification
from OpenCAI.llm_adapter import FakeLLMAdapter, Message, ModelOutput
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


if __name__ == "__main__":
    unittest.main()
