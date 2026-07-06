from __future__ import annotations

import unittest
from unittest.mock import patch

from OpenCAI.tui import ask_user_prompt
from OpenCAI.user_prompt import UserPromptOption, UserPromptRequest, UserPromptResult


class UserPromptTests(unittest.TestCase):
    def test_ask_user_prompt_returns_selected_option_info(self) -> None:
        request = UserPromptRequest(
            kind="guided_review",
            title="Review demand",
            question="Proceed?",
            options=(
                UserPromptOption(
                    id="execute",
                    label="Execute",
                    description="Run now.",
                    value="execute",
                ),
                UserPromptOption(
                    id="stop",
                    label="Stop",
                    description="Do not run.",
                    value="stop",
                ),
            ),
        )

        with (
            patch("OpenCAI.tui.sys.stdin.isatty", return_value=True),
            patch("OpenCAI.tui.ask_select", return_value="execute") as select,
        ):
            result = ask_user_prompt(request)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual("execute", result.selected_option_id)
        self.assertEqual("Execute", result.selected_label)
        self.assertEqual("execute", result.value)
        self.assertEqual("execute", result.answer)
        select.assert_called_once()

    def test_ask_user_prompt_collects_required_custom_input(self) -> None:
        request = UserPromptRequest(
            kind="guided_review",
            title="Review demand",
            question="Proceed?",
            options=(
                UserPromptOption(
                    id="revise",
                    label="Revise demand",
                    description="Change the brief.",
                    value="revise",
                    requires_input=True,
                    input_label="Revision feedback",
                ),
            ),
        )

        with (
            patch("OpenCAI.tui.sys.stdin.isatty", return_value=True),
            patch("OpenCAI.tui.ask_select", return_value="revise"),
            patch(
                "OpenCAI.tui.ask_user_prompt_text",
                return_value=UserPromptResult(custom_answer="Only update README."),
            ) as ask_text,
            patch("OpenCAI.tui.ask_task") as ask_task,
        ):
            result = ask_user_prompt(request)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual("revise", result.selected_option_id)
        self.assertEqual("revise", result.value)
        self.assertEqual("Only update README.", result.custom_answer)
        self.assertEqual("Only update README.", result.answer)
        ask_text.assert_called_once_with(
            title="Review demand",
            question="Proceed?",
            label="Revision feedback",
        )
        ask_task.assert_not_called()

    def test_ask_user_prompt_returns_cancelled_when_selection_is_cancelled(self) -> None:
        request = UserPromptRequest(
            kind="clarify_question",
            title="Clarify",
            question="Which scope?",
            options=(
                UserPromptOption(id="readme", label="README", value="README.md"),
                UserPromptOption(id="docs", label="Docs", value="docs/"),
            ),
        )

        with (
            patch("OpenCAI.tui.sys.stdin.isatty", return_value=True),
            patch("OpenCAI.tui.ask_select", return_value=None),
        ):
            result = ask_user_prompt(request)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.cancelled)
        self.assertEqual("", result.answer)

    def test_ask_user_prompt_propagates_custom_input_cancel(self) -> None:
        request = UserPromptRequest(
            kind="clarify_question",
            title="Clarify",
            question="Which scope?",
            options=(
                UserPromptOption(
                    id="custom",
                    label="Custom answer",
                    requires_input=True,
                ),
            ),
        )

        with (
            patch("OpenCAI.tui.sys.stdin.isatty", return_value=True),
            patch("OpenCAI.tui.ask_select", return_value="custom"),
            patch(
                "OpenCAI.tui.ask_user_prompt_text",
                return_value=UserPromptResult(cancelled=True),
            ),
        ):
            result = ask_user_prompt(request)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.cancelled)


if __name__ == "__main__":
    unittest.main()
