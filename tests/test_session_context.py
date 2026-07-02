from __future__ import annotations

import unittest

from OpenCAI.events import final_answer, tool_call, tool_result, user_task, verification
from OpenCAI.session_context import SessionContext, summarize_turn_events


class SessionContextTests(unittest.TestCase):
    def test_summarize_turn_events_keeps_only_compact_model_visible_facts(self) -> None:
        events = [
            user_task(1, "Read README"),
            tool_call(2, "read_file", {"path": "README.md"}),
            tool_result(3, "read_file", True, {"content": "x" * 5000}),
            tool_call(4, "invoke_skill", {"skill": "demo-skill"}),
            tool_result(5, "invoke_skill", True, {"skill": "demo-skill", "content": "secret"}),
            verification(4, "python -m unittest discover tests", 0, stdout="ok"),
            final_answer(5, "README was read."),
        ]

        summary = summarize_turn_events(events)

        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary.user_task, "Read README")
        self.assertEqual(summary.final_answer, "README was read.")
        self.assertEqual(summary.tool_calls, ("read_file", "invoke_skill"))
        self.assertEqual(summary.invoked_skills, ("demo-skill",))
        self.assertEqual(
            summary.verification_results,
            ("passed: python -m unittest discover tests",),
        )
        self.assertNotIn("x" * 100, summary.render())
        self.assertNotIn("secret", summary.render())

    def test_add_turn_events_compacts_old_turns_when_recent_turn_limit_is_exceeded(self) -> None:
        context = SessionContext(recent_turns_max=1)

        context.add_turn_events([user_task(1, "First"), final_answer(2, "first done")])
        context.add_turn_events([user_task(1, "Second"), final_answer(2, "second done")])

        rendered = context.render()
        self.assertEqual(context.compact_count, 1)
        self.assertEqual(len(context.recent_turns), 1)
        self.assertIn("First", context.running_summary)
        self.assertIn("Second", rendered)


if __name__ == "__main__":
    unittest.main()
