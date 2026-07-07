from __future__ import annotations

import unittest

from OpenCAI.composer import (
    ComposerState,
    RuntimeCommandInput,
    ShellInput,
    SkillInvocationInput,
    Suggestion,
    TaskInput,
    WorkflowCommandInput,
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

    def test_workflow_input_is_workflow_command(self) -> None:
        parsed = parse_user_input(" /workflow Read README ")

        self.assertEqual(
            parsed,
            WorkflowCommandInput(
                task="Read README",
                raw_text="/workflow Read README",
            ),
        )

    def test_workflow_input_without_task_returns_empty_workflow_command(self) -> None:
        parsed = parse_user_input(" /workflow ")

        self.assertEqual(
            parsed,
            WorkflowCommandInput(task="", raw_text="/workflow"),
        )

    def test_bang_input_is_shell_command(self) -> None:
        parsed = parse_user_input(" !python --version ")

        self.assertEqual(parsed, ShellInput("python --version"))

    def test_dollar_input_is_skill_invocation(self) -> None:
        parsed = parse_user_input(" $learn-with-dev continue workflow ")

        self.assertEqual(
            parsed,
            SkillInvocationInput(
                skill_name="learn-with-dev",
                args="continue workflow",
                raw_text="$learn-with-dev continue workflow",
            ),
        )

    def test_empty_dollar_input_returns_none(self) -> None:
        self.assertIsNone(parse_user_input("$"))
        self.assertIsNone(parse_user_input("$   "))

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

    def test_composer_state_builds_skill_suggestions(self) -> None:
        state = ComposerState(skill_suggestions=[("learn-with-dev", "Teach then implement.")])

        state.update_text("$lea")

        self.assertEqual(
            state.suggestions,
            [Suggestion("$learn-with-dev", "Teach then implement.")],
        )

    def test_composer_state_filters_command_suggestions(self) -> None:
        state = ComposerState()

        state.update_text("/mo")

        self.assertEqual(
            [suggestion.value for suggestion in state.suggestions],
            ["/model", "/model-add", "/model-test", "/mode"],
        )

    def test_composer_state_suggests_workflow_command(self) -> None:
        state = ComposerState()

        state.update_text("/wo")

        self.assertEqual([suggestion.value for suggestion in state.suggestions], ["/workflow"])

    def test_composer_state_keeps_exact_command_suggestion_visible(self) -> None:
        state = ComposerState()

        state.update_text("/model")

        self.assertEqual(
            [suggestion.value for suggestion in state.suggestions],
            ["/model", "/model-add", "/model-test"],
        )

    def test_model_command_does_not_build_inline_choice_suggestions(self) -> None:
        state = ComposerState()

        state.update_text("/model ")

        self.assertEqual(state.suggestions, [])

    def test_permission_command_does_not_build_inline_choice_suggestions(self) -> None:
        state = ComposerState()

        state.update_text("/permission ")

        self.assertEqual(state.suggestions, [])

    def test_composer_state_accepts_command_suggestion(self) -> None:
        state = ComposerState()
        state.update_text("/mo")

        accepted = state.accept_suggestion()

        self.assertEqual(accepted, "/model")
        self.assertEqual(state.text, "/model")

    def test_composer_state_accepts_skill_suggestion_with_space(self) -> None:
        state = ComposerState(skill_suggestions=[("learn-with-dev", "Teach then implement.")])
        state.update_text("$lea")

        accepted = state.accept_suggestion()

        self.assertEqual(accepted, "$learn-with-dev ")
        self.assertEqual(state.text, "$learn-with-dev ")

    def test_permission_command_accepts_command_suggestion_without_inline_space(self) -> None:
        state = ComposerState()
        state.update_text("/perm")

        accepted = state.accept_suggestion()

        self.assertEqual(accepted, "/permission")
        self.assertEqual(state.text, "/permission")

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
