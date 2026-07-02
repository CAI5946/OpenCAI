from pathlib import Path
import tempfile
import unittest

from OpenCAI.safety import PermissionProfile, SafetyPolicy
from OpenCAI.tools import TOOLS


class SafetyPolicyTest(unittest.TestCase):
    def test_permission_profile_from_cli_value(self) -> None:
        self.assertEqual(
            PermissionProfile.from_cli_value("read-only"),
            PermissionProfile.READ_ONLY,
        )
        self.assertEqual(
            PermissionProfile.from_cli_value("ask-approval"),
            PermissionProfile.ASK_APPROVAL,
        )
        self.assertEqual(
            PermissionProfile.from_cli_value("approve-safe"),
            PermissionProfile.APPROVE_SAFE,
        )
        self.assertEqual(
            PermissionProfile.from_cli_value("full-access"),
            PermissionProfile.FULL_ACCESS,
        )

    def test_permission_profile_rejects_unknown_cli_value(self) -> None:
        with self.assertRaises(ValueError):
            PermissionProfile.from_cli_value("unsafe")

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
        decision = SafetyPolicy(profile=PermissionProfile.READ_ONLY).check_tool_call(
            TOOLS["apply_patch"],
            {"path": "README.md", "old": "a", "new": "b"},
            Path.cwd(),
        )

        self.assertFalse(decision.allowed)
        self.assertIn("Approval required", decision.reason or "")

    def test_denies_write_file_without_write_permission(self) -> None:
        decision = SafetyPolicy(profile=PermissionProfile.READ_ONLY).check_tool_call(
            TOOLS["write_file"],
            {"path": "demo.txt", "content": "x"},
            Path.cwd(),
        )

        self.assertFalse(decision.allowed)
        self.assertIn("Approval required", decision.reason or "")

    def test_checks_source_and_destination_paths_for_file_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp) / "workspace"
            cwd.mkdir()
            decision = SafetyPolicy().check_tool_call(
                TOOLS["copy_file"],
                {"source": "a.txt", "destination": "..\\b.txt"},
                cwd,
            )

        self.assertFalse(decision.allowed)
        self.assertIn("escapes workspace", decision.reason or "")

    def test_denies_run_command_without_command_permission(self) -> None:
        decision = SafetyPolicy(profile=PermissionProfile.READ_ONLY).check_tool_call(
            TOOLS["run_command"],
            {"command": "python -m unittest"},
            Path.cwd(),
        )

        self.assertFalse(decision.allowed)
        self.assertIn("Approval required", decision.reason or "")

    def test_denies_start_command_without_command_permission(self) -> None:
        decision = SafetyPolicy(profile=PermissionProfile.READ_ONLY).check_tool_call(
            TOOLS["start_command"],
            {"command": "python -m http.server"},
            Path.cwd(),
        )

        self.assertFalse(decision.allowed)
        self.assertIn("Approval required", decision.reason or "")

    def test_denies_command_cwd_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp) / "workspace"
            cwd.mkdir()
            decision = SafetyPolicy().check_tool_call(
                TOOLS["run_command"],
                {"command": "python --version", "cwd": ".."},
                cwd,
            )

        self.assertFalse(decision.allowed)
        self.assertIn("escapes workspace", decision.reason or "")

    def test_approve_safe_allows_write_and_command(self) -> None:
        policy = SafetyPolicy(profile=PermissionProfile.APPROVE_SAFE)

        write_decision = policy.check_tool_call(
            TOOLS["apply_patch"],
            {"path": "README.md", "old": "a", "new": "b"},
            Path.cwd(),
        )
        command_decision = policy.check_tool_call(
            TOOLS["run_command"],
            {"command": "python --version"},
            Path.cwd(),
        )

        self.assertTrue(write_decision.allowed)
        self.assertTrue(command_decision.allowed)

    def test_full_access_allows_write_and_command_but_keeps_dangerous_blocklist(self) -> None:
        policy = SafetyPolicy(profile=PermissionProfile.FULL_ACCESS)

        write_decision = policy.check_tool_call(
            TOOLS["apply_patch"],
            {"path": "README.md", "old": "a", "new": "b"},
            Path.cwd(),
        )
        dangerous_decision = policy.check_tool_call(
            TOOLS["run_command"],
            {"command": "git reset --hard"},
            Path.cwd(),
        )

        self.assertTrue(write_decision.allowed)
        self.assertFalse(dangerous_decision.allowed)
        self.assertIn("Blocked dangerous command", dangerous_decision.reason or "")

    def test_denies_dangerous_command_even_when_commands_allowed(self) -> None:
        decision = SafetyPolicy(profile=PermissionProfile.APPROVE_SAFE).check_tool_call(
            TOOLS["run_command"],
            {"command": "Remove-Item -Recurse ."},
            Path.cwd(),
        )

        self.assertFalse(decision.allowed)
        self.assertIn("Blocked dangerous command", decision.reason or "")


if __name__ == "__main__":
    unittest.main()
