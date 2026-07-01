from __future__ import annotations

import unittest
from unittest.mock import patch

from prompt_toolkit.application import Application
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.layout import Layout
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.widgets import TextArea

from OpenCAI.events import final_answer, make_event, tool_call, tool_result, user_task
from OpenCAI.tui import (
    DIVIDER_STYLE,
    create_process_view_key_bindings,
    extract_task_summary,
    live_process_text,
    LiveProcessRenderer,
    process_events,
    process_view_text,
    render_event_process,
    render_event_stream,
    render_rule,
    render_submitted_input,
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
        self.assertIn("• Process", rule_titles)
        self.assertIn("• 2 Tool call", rule_titles)
        self.assertIn("• 3 Tool result", rule_titles)
        self.assertFalse(any("[" in title or "]" in title for title in rule_titles))
        self.assertFalse(any("User task" in title for title in rule_titles))
        self.assertTrue(all(call.kwargs.get("style") == DIVIDER_STYLE for call in rule.call_args_list))
        panel.assert_not_called()

    def test_task_summary_does_not_put_divider_before_final_answer(self) -> None:
        with patch("OpenCAI.tui.console.rule") as rule, patch("OpenCAI.tui.console.print") as print_:
            render_task_summary([user_task(1, "Read README"), final_answer(2, "done")])

        rule.assert_not_called()
        self.assertEqual(print_.call_args_list[0].args[0], "Final answer:")
        self.assertFalse(any(call.args == () for call in print_.call_args_list))

    def test_render_rule_reuses_input_border_style(self) -> None:
        with patch("OpenCAI.tui.console.rule") as rule:
            render_rule("Final answer")

        rule.assert_called_once_with("• Final answer", style=DIVIDER_STYLE)

    def test_render_rule_keeps_empty_divider_unlabeled(self) -> None:
        with patch("OpenCAI.tui.console.rule") as rule:
            render_rule()

        rule.assert_called_once_with("", style=DIVIDER_STYLE)

    def test_submitted_input_has_divider_before_line(self) -> None:
        with patch("OpenCAI.tui.render_rule") as rule, patch("OpenCAI.tui.console.print") as print_:
            render_submitted_input("Read README")

        rule.assert_called_once_with()
        print_.assert_called_once_with("Submitted task:\nRead README", style="dim")

    def test_task_summary_includes_divider_before_submitted_task(self) -> None:
        with patch("OpenCAI.tui.render_rule") as rule, patch("OpenCAI.tui.console.print"):
            render_task_summary(
                [user_task(1, "Read README"), final_answer(2, "done")],
                include_submitted_task=True,
            )

        self.assertEqual(rule.call_args_list[0].args, ())

    def test_process_view_text_includes_collapse_hint_without_user_task(self) -> None:
        text = process_view_text(
            [
                user_task(1, "Read README"),
                tool_call(2, "read_file", {"path": "README.md"}),
            ]
        )

        self.assertIn("Press Ctrl+O, Esc, Enter, or q to collapse.", text)
        self.assertIn("• Process", text)
        self.assertIn("• 2 Tool call", text)
        self.assertNotIn("User task", text)

    def test_live_process_text_shows_recent_process_without_user_task(self) -> None:
        text = live_process_text(
            [
                user_task(1, "Read README"),
                tool_call(2, "read_file", {"path": "README.md"}),
                tool_result(3, "read_file", True, {"content_preview": "done"}),
            ]
        ).plain

        self.assertIn("Process running", text)
        self.assertIn("2. tool call: read_file", text)
        self.assertIn("3. tool result: read_file (ok)", text)
        self.assertNotIn("Read README", text)

    def test_live_process_renderer_uses_transient_live_region(self) -> None:
        with patch("OpenCAI.tui.Live") as live_class:
            with LiveProcessRenderer() as renderer:
                renderer.update([tool_call(2, "read_file", {"path": "README.md"})])

        self.assertTrue(live_class.call_args.kwargs["transient"])
        live_class.return_value.__enter__.assert_called_once()
        live_class.return_value.update.assert_called_once()
        live_class.return_value.__exit__.assert_called_once()

    def test_process_view_ctrl_o_collapses_view(self) -> None:
        with create_pipe_input() as pipe_input:
            app: Application[None] = Application(
                layout=Layout(TextArea(text="process", read_only=True)),
                key_bindings=create_process_view_key_bindings(),
                full_screen=True,
                erase_when_done=True,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("\x0f")

            self.assertIsNone(app.run())

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
