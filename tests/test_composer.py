from __future__ import annotations

import unittest

from OpenCAI.composer import (
    ComposerState,
    RuntimeCommandInput,
    ShellInput,
    TaskInput,
    parse_user_input,
)


class ComposerTests(unittest.TestCase):
    def test_empty_input_returns_none(self) -> None:
        self.assertIsNone(parse_user_input(""))
        self.assertIsNone(parse_user_input("   "))
        self.assertIsNone(parse_user_input("!   "))

    def test_slash_input_is_runtime_command(self) -> None:
        parsed = parse_user_input(" /status ")

        self.assertEqual(parsed, RuntimeCommandInput("/status"))

    def test_bang_input_is_shell_command(self) -> None:
        parsed = parse_user_input(" !python --version ")

        self.assertEqual(parsed, ShellInput("python --version"))

    def test_plain_input_is_task(self) -> None:
        parsed = parse_user_input("exit")

        self.assertEqual(parsed, TaskInput("exit"))

    def test_composer_state_builds_command_suggestions(self) -> None:
        state = ComposerState()

        state.update_text("/")

        values = [suggestion.value for suggestion in state.suggestions]
        self.assertTrue(state.suggestions_visible)
        self.assertIn("/model", values)
        self.assertIn("/exit", values)

    def test_composer_state_filters_command_suggestions(self) -> None:
        state = ComposerState()

        state.update_text("/mo")

        self.assertEqual([suggestion.value for suggestion in state.suggestions], ["/model"])

    def test_composer_state_suggests_workflow_command(self) -> None:
        state = ComposerState()

        state.update_text("/wo")

        self.assertEqual([suggestion.value for suggestion in state.suggestions], ["/workflow"])

    def test_composer_state_hides_exact_command_suggestion(self) -> None:
        state = ComposerState()

        state.update_text("/model")

        self.assertEqual(state.suggestions, [])

    def test_model_command_does_not_build_inline_choice_suggestions(self) -> None:
        state = ComposerState()

        state.update_text("/model ")

        self.assertEqual(state.suggestions, [])

    def test_inline_command_builds_choice_suggestions(self) -> None:
        state = ComposerState()

        state.update_text("/allow-write ")

        self.assertEqual([suggestion.value for suggestion in state.suggestions], ["on", "off"])

    def test_composer_state_accepts_command_suggestion(self) -> None:
        state = ComposerState()
        state.update_text("/mo")

        accepted = state.accept_suggestion()

        self.assertEqual(accepted, "/model")
        self.assertEqual(state.text, "/model")

    def test_composer_state_accepts_choice_suggestion(self) -> None:
        state = ComposerState()
        state.update_text("/allow-command o")

        accepted = state.accept_suggestion()

        self.assertEqual(accepted, "/allow-command on")
        self.assertEqual(state.text, "/allow-command on")

    def test_composer_state_dismisses_suggestions(self) -> None:
        state = ComposerState()
        state.update_text("/")

        state.dismiss_suggestions()

        self.assertFalse(state.suggestions_visible)
        self.assertEqual(state.suggestions, [])

    def test_composer_state_submit_uses_input_parser(self) -> None:
        state = ComposerState()
        state.update_text("!python --version")

        self.assertEqual(state.submit(), ShellInput("python --version"))


if __name__ == "__main__":
    unittest.main()
