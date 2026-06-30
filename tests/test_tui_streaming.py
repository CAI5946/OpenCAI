from __future__ import annotations

import unittest
from unittest.mock import patch

from OpenCAI.events import final_answer, make_event, tool_call, tool_result, user_task
from OpenCAI.tui import (
    DIVIDER_STYLE,
    extract_task_summary,
    process_events,
    process_view_text,
    render_event_process,
    render_event_stream,
    render_rule,
    render_task_summary,
    show_process_view,
)


class TuiStreamingTests(unittest.TestCase):
    def test_render_event_stream_consumes_events_in_iteration_order(self) -> None:
        consumed_types: list[str] = []

        def event_source():
            yield user_task(1, "Read README")
            yield final_answer(2, "done")

        with patch("OpenCAI.tui.console.rule"), patch("OpenCAI.tui.render_event") as render_event:
            render_event.side_effect = lambda event: consumed_types.append(event["type"])
            render_event_stream(event_source())

        self.assertEqual(consumed_types, ["user_task", "final_answer"])

    def test_process_events_skip_user_task_by_default(self) -> None:
        events = [
            user_task(1, "Read README"),
            tool_call(2, "read_file", {"path": "README.md"}),
            final_answer(3, "done"),
        ]

        self.assertEqual(
            [event["type"] for event in process_events(events)],
            ["tool_call", "final_answer"],
        )

    def test_task_summary_uses_submitted_task_and_final_answer(self) -> None:
        summary = extract_task_summary(
            [
                user_task(1, "Read README"),
                tool_call(2, "read_file", {"path": "README.md"}),
                final_answer(3, "done"),
            ]
        )

        self.assertEqual(summary.task, "Read README")
        self.assertEqual(summary.final_answer, "done")
        self.assertIsNone(summary.stop_message)
        self.assertIsNone(summary.error_message)

    def test_task_summary_falls_back_to_stop_or_error_without_final_answer(self) -> None:
        stopped = extract_task_summary(
            [
                user_task(1, "Loop"),
                make_event("stop", 2, "Agent loop stopped: max_steps_reached."),
            ]
        )
        failed = extract_task_summary(
            [
                user_task(1, "Loop"),
                make_event("error", 2, "LLM adapter failed."),
            ]
        )

        self.assertEqual(stopped.stop_message, "Agent loop stopped: max_steps_reached.")
        self.assertEqual(failed.error_message, "LLM adapter failed.")

    def test_render_event_process_uses_plain_rules_not_panels(self) -> None:
        events = [
            user_task(1, "Read README"),
            tool_call(2, "read_file", {"path": "README.md"}),
            tool_result(3, "read_file", True, {"content_preview": "hello"}),
        ]

        with (
            patch("OpenCAI.tui.console.rule") as rule,
            patch("OpenCAI.tui.console.print"),
            patch("OpenCAI.tui.Panel") as panel,
        ):
            render_event_process(events)

        rule_titles = [str(call.args[0]) for call in rule.call_args_list if call.args]
        self.assertGreaterEqual(rule.call_count, 3)
        self.assertIn("Process", rule_titles)
        self.assertFalse(any("[" in title or "]" in title for title in rule_titles))
        self.assertFalse(any("User task" in title for title in rule_titles))
        self.assertTrue(all(call.kwargs.get("style") == DIVIDER_STYLE for call in rule.call_args_list))
        panel.assert_not_called()

    def test_task_summary_uses_input_border_rule_style(self) -> None:
        with patch("OpenCAI.tui.console.rule") as rule, patch("OpenCAI.tui.console.print"):
            render_task_summary([user_task(1, "Read README"), final_answer(2, "done")])

        self.assertEqual(rule.call_args_list[0].args[0], "Final answer")
        self.assertEqual(rule.call_args_list[0].kwargs["style"], DIVIDER_STYLE)

    def test_render_rule_reuses_input_border_style(self) -> None:
        with patch("OpenCAI.tui.console.rule") as rule:
            render_rule("Final answer")

        rule.assert_called_once_with("Final answer", style=DIVIDER_STYLE)

    def test_process_view_text_includes_collapse_hint_without_user_task(self) -> None:
        text = process_view_text(
            [
                user_task(1, "Read README"),
                tool_call(2, "read_file", {"path": "README.md"}),
            ]
        )

        self.assertIn("Press Esc, Enter, or q to collapse.", text)
        self.assertIn("2 Tool call", text)
        self.assertNotIn("User task", text)

    def test_show_process_view_prints_process_for_non_tty(self) -> None:
        events = [user_task(1, "Read README"), final_answer(2, "done")]

        with patch("OpenCAI.tui.sys.stdin.isatty", return_value=False), patch("OpenCAI.tui.render_event_process") as render_process:
            show_process_view(events)

        render_process.assert_called_once_with(events, skip_user_task=True)

    def test_show_process_view_uses_temporary_full_screen_app_for_tty(self) -> None:
        events = [user_task(1, "Read README"), final_answer(2, "done")]

        with (
            patch("OpenCAI.tui.sys.stdin.isatty", return_value=True),
            patch("OpenCAI.tui.Application") as application,
        ):
            show_process_view(events)

        self.assertTrue(application.call_args.kwargs["full_screen"])
        self.assertTrue(application.call_args.kwargs["erase_when_done"])
        application.return_value.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
