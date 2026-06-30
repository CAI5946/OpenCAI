from __future__ import annotations

import unittest
from pathlib import Path

from OpenCAI.safety import SafetyPolicy
from OpenCAI.shell_mode import run_user_shell_command


class ShellModeTests(unittest.TestCase):
    def test_user_shell_command_runs_with_default_policy(self) -> None:
        transcript = run_user_shell_command(
            'python -c "print(123)"',
            Path.cwd(),
            SafetyPolicy(),
        )

        self.assertEqual(transcript[0]["type"], "shell_command")
        self.assertEqual(transcript[1]["type"], "verification")
        self.assertTrue(transcript[1]["data"]["ok"])
        self.assertIn("123", transcript[1]["data"]["stdout"])

    def test_user_shell_command_blocks_dangerous_command(self) -> None:
        transcript = run_user_shell_command(
            "git reset --hard",
            Path.cwd(),
            SafetyPolicy(),
        )

        self.assertEqual(transcript[0]["type"], "shell_command")
        self.assertEqual(transcript[1]["type"], "error")
        self.assertIn("Blocked dangerous command", transcript[1]["message"])


if __name__ == "__main__":
    unittest.main()
