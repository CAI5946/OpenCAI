from __future__ import annotations

import unittest

from prompt_toolkit.document import Document

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

        self.assertEqual(texts, ["/model"])

    def test_model_command_lists_adapter_choices(self) -> None:
        completions = list(RuntimeCommandCompleter().get_completions(Document("/model "), None))
        texts = [completion.text for completion in completions]

        self.assertEqual(texts, ["fake", "gemini"])

    def test_completer_uses_choice_prefix_start_position(self) -> None:
        completions = list(RuntimeCommandCompleter().get_completions(Document("/model g"), None))

        self.assertEqual([completion.text for completion in completions], ["gemini"])
        self.assertEqual(completions[0].start_position, -1)

    def test_tab_accepts_command_suggestion_via_composer(self) -> None:
        self.assertEqual(accept_composer_suggestion("/mo"), "/model ")

    def test_tab_accepts_choice_suggestion_via_composer(self) -> None:
        self.assertEqual(accept_composer_suggestion("/model g"), "/model gemini")

    def test_tab_without_composer_suggestion_keeps_text(self) -> None:
        self.assertEqual(accept_composer_suggestion("plain task"), "plain task")

    def test_composer_suggestion_visibility_helper(self) -> None:
        self.assertTrue(has_composer_suggestions("/"))
        self.assertTrue(has_composer_suggestions("/model g"))
        self.assertFalse(has_composer_suggestions("plain task"))


if __name__ == "__main__":
    unittest.main()
