from __future__ import annotations

import unittest

from prompt_toolkit.document import Document

from OpenCAI.tui import RuntimeCommandCompleter


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


if __name__ == "__main__":
    unittest.main()
