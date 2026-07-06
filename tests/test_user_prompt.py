from __future__ import annotations

import unittest
from unittest.mock import patch

from OpenCAI.tui import ask_user_prompt
from OpenCAI.user_prompt import UserPromptOption, UserPromptRequest


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
            patch("OpenCAI.tui.ask_task", return_value="Only update README.") as ask_task,
        ):
            result = ask_user_prompt(request)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual("revise", result.selected_option_id)
        self.assertEqual("revise", result.value)
        self.assertEqual("Only update README.", result.custom_answer)
        self.assertEqual("Only update README.", result.answer)
        ask_task.assert_called_once()


if __name__ == "__main__":
    unittest.main()
