from __future__ import annotations

import unittest

from prompt_toolkit.document import Document
from unittest.mock import patch

from OpenCAI.composer import Suggestion
from OpenCAI.tui import RuntimeCommandCompleter, accept_composer_suggestion, has_composer_suggestions


class RuntimeCommandCompleterTests(unittest.TestCase):
    def test_slash_lists_runtime_commands(self) -> None:
        completions = list(RuntimeCommandCompleter().get_completions(Document("/"), None))
        texts = [completion.text for completion in completions]

        self.assertIn("/help", texts)
        self.assertIn("/model", texts)
        self.assertIn("/exit", texts)

    def test_command_prefix_filters_runtime_commands(self) -> None:
        completions = list(RuntimeCommandCompleter().get_completions(Document("/mo"), None))
        texts = [completion.text for completion in completions]

        self.assertEqual(texts, ["/model", "/model-test", "/mode"])

    def test_dollar_prefix_lists_skills(self) -> None:
        with patch(
            "OpenCAI.tui.build_suggestions",
            return_value=[Suggestion("$learn-with-dev", "Teach then implement.")],
        ):
            completions = list(RuntimeCommandCompleter().get_completions(Document("$lea"), None))

        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0].text, "$learn-with-dev")
        self.assertEqual(completions[0].start_position, -4)

    def test_model_command_does_not_list_adapter_choices_inline(self) -> None:
        completions = list(RuntimeCommandCompleter().get_completions(Document("/model "), None))

        self.assertEqual(completions, [])

    def test_exact_command_keeps_matching_completion_visible(self) -> None:
        completions = list(RuntimeCommandCompleter().get_completions(Document("/model"), None))

        model_completion = next(completion for completion in completions if completion.text == "/model ")
        self.assertEqual(model_completion.display_text, "/model")

    def test_permission_command_does_not_list_profile_choices_inline(self) -> None:
        completions = list(RuntimeCommandCompleter().get_completions(Document("/permission "), None))

        self.assertEqual(completions, [])

    def test_tab_accepts_command_suggestion_via_composer(self) -> None:
        self.assertEqual(accept_composer_suggestion("/mo"), "/model")

    def test_tab_accepts_permission_command_without_inline_space(self) -> None:
        self.assertEqual(accept_composer_suggestion("/perm"), "/permission")

    def test_tab_without_composer_suggestion_keeps_text(self) -> None:
        self.assertEqual(accept_composer_suggestion("plain task"), "plain task")

    def test_composer_suggestion_visibility_helper(self) -> None:
        self.assertTrue(has_composer_suggestions("/"))
        self.assertTrue(has_composer_suggestions("/model"))
        self.assertFalse(has_composer_suggestions("/model g"))
        self.assertFalse(has_composer_suggestions("/permission f"))
        self.assertFalse(has_composer_suggestions("plain task"))


if __name__ == "__main__":
    unittest.main()
