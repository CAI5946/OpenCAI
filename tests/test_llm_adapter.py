from __future__ import annotations

import unittest

from OpenCAI.llm_adapter import GeminiAdapter


class GeminiAdapterContextTests(unittest.TestCase):
    def test_system_messages_are_joined_and_excluded_from_contents(self) -> None:
        adapter = object.__new__(GeminiAdapter)

        messages = [
            {"role": "system", "content": "system one"},
            {"role": "user", "content": "task"},
            {"role": "system", "content": "system two"},
        ]

        self.assertEqual(adapter._system_instruction(messages), "system one\n\nsystem two")


if __name__ == "__main__":
    unittest.main()
