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
        with patch("OpenCAI.__main__.render_task_summary") as render_summary:
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


if __name__ == "__main__":
    unittest.main()
