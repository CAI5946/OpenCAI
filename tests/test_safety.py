from pathlib import Path
import tempfile
import unittest

from OpenCAI.safety import SafetyPolicy
from OpenCAI.tools import TOOLS


class SafetyPolicyTest(unittest.TestCase):
    def test_allows_read_file_inside_cwd_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            decision = SafetyPolicy().check_tool_call(
                TOOLS["read_file"],
                {"path": "README.md"},
                cwd,
            )

        self.assertTrue(decision.allowed)
        self.assertIsNone(decision.reason)

    def test_denies_read_file_outside_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp) / "workspace"
            cwd.mkdir()
            decision = SafetyPolicy().check_tool_call(
                TOOLS["read_file"],
                {"path": "..\\secret.txt"},
                cwd,
            )

        self.assertFalse(decision.allowed)
        self.assertIn("escapes workspace", decision.reason or "")

    def test_denies_apply_patch_without_write_permission(self) -> None:
        decision = SafetyPolicy().check_tool_call(
            TOOLS["apply_patch"],
            {"path": "README.md", "old": "a", "new": "b"},
            Path.cwd(),
        )

        self.assertFalse(decision.allowed)
        self.assertIn("Write operations are disabled", decision.reason or "")

    def test_denies_run_command_without_command_permission(self) -> None:
        decision = SafetyPolicy().check_tool_call(
            TOOLS["run_command"],
            {"command": "python -m unittest"},
            Path.cwd(),
        )

        self.assertFalse(decision.allowed)
        self.assertIn("Command execution is disabled", decision.reason or "")

    def test_denies_dangerous_command_even_when_commands_allowed(self) -> None:
        decision = SafetyPolicy(allow_command=True).check_tool_call(
            TOOLS["run_command"],
            {"command": "Remove-Item -Recurse ."},
            Path.cwd(),
        )

        self.assertFalse(decision.allowed)
        self.assertIn("Blocked dangerous command", decision.reason or "")


if __name__ == "__main__":
    unittest.main()
