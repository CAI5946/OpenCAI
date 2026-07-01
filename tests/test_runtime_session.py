from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from OpenCAI.__main__ import RuntimeSession, run_interactive, run_once
from OpenCAI.events import Event, final_answer, user_task
from OpenCAI.llm_adapter import FakeLLMAdapter
from OpenCAI.safety import PermissionProfile, SafetyPolicy


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
