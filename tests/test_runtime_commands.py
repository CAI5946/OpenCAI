from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from OpenCAI.llm_adapter import FakeLLMAdapter, LLMAdapter
from OpenCAI.model_registry import ModelRegistry
from OpenCAI.events import Event, final_answer, user_task
from OpenCAI.safety import PermissionProfile, SafetyPolicy
from OpenCAI.runtime_commands import (
    handle_runtime_command,
    render_keymap_text,
    render_runtime_status,
    render_runtime_help,
    runtime_command_completion_tree,
)


@dataclass
class DummySession:
    cwd: Path
    adapter_name: str = "fake"
    adapter: LLMAdapter | None = None
    max_steps: int = 8
    permission_profile: PermissionProfile = PermissionProfile.APPROVE_SAFE
    execution_mode: str = "agent"
    turn_count: int = 0
    last_task_events: list[Event] | None = None

    def build_policy(self) -> SafetyPolicy:
        return SafetyPolicy(profile=self.permission_profile)


def build_dummy_adapter(adapter_name: str, api_key: str | None) -> LLMAdapter:
    if adapter_name != "fake":
        raise AssertionError(f"unexpected adapter: {adapter_name}")
    return FakeLLMAdapter()


class RuntimeCommandTests(unittest.TestCase):
    def test_completion_tree_contains_runtime_commands_and_choices(self) -> None:
        tree = runtime_command_completion_tree()

        self.assertIn("/model", tree)
        self.assertIsNone(tree["/model"])
        self.assertIn("/keymap", tree)
        self.assertIsNone(tree["/keymap"])
        self.assertIn("/mode", tree)
        self.assertIsNone(tree["/mode"])
        self.assertIn("/process", tree)
        self.assertIsNone(tree["/workflow"])
        self.assertEqual(
            tree["/permission"],
            None,
        )
        self.assertNotIn("/allow-write", tree)
        self.assertNotIn("/allow-command", tree)

    def test_handle_runtime_command_updates_session(self) -> None:
        session = DummySession(cwd=Path.cwd())

        should_exit = handle_runtime_command(session, "/max-steps 8", None, build_dummy_adapter)
        self.assertFalse(should_exit)
        self.assertEqual(session.max_steps, 8)

        handle_runtime_command(session, "/permission approve-safe", None, build_dummy_adapter)
        self.assertEqual(session.permission_profile, PermissionProfile.APPROVE_SAFE)

        handle_runtime_command(session, "/mode workflow", None, build_dummy_adapter)
        self.assertEqual(session.execution_mode, "workflow")

        handle_runtime_command(session, "/mode guided", None, build_dummy_adapter)
        self.assertEqual(session.execution_mode, "guided")

        handle_runtime_command(session, "/model fake", None, build_dummy_adapter)
        self.assertEqual(session.adapter_name, "fake")
        self.assertIsInstance(session.adapter, FakeLLMAdapter)

    def test_mode_command_rejects_unknown_mode(self) -> None:
        session = DummySession(cwd=Path.cwd())
        output = io.StringIO()

        with redirect_stdout(output):
            should_exit = handle_runtime_command(session, "/mode unsafe", None, build_dummy_adapter)

        self.assertFalse(should_exit)
        self.assertEqual(session.execution_mode, "agent")
        self.assertIn("Usage: /mode", output.getvalue())

    def test_mode_command_can_use_choice_provider(self) -> None:
        session = DummySession(cwd=Path.cwd(), execution_mode="agent")
        output = io.StringIO()
        requested_current: list[str | None] = []

        with redirect_stdout(output):
            handle_runtime_command(
                session,
                "/mode",
                None,
                build_dummy_adapter,
                lambda _label, _choices, current: requested_current.append(current) or "guided",
            )

        self.assertEqual(requested_current, ["agent"])
        self.assertEqual(session.execution_mode, "guided")
        self.assertIn("Mode changed to guided", output.getvalue())

    def test_permission_command_rejects_unknown_profile(self) -> None:
        session = DummySession(cwd=Path.cwd())
        output = io.StringIO()

        with redirect_stdout(output):
            should_exit = handle_runtime_command(session, "/permission unsafe", None, build_dummy_adapter)

        self.assertFalse(should_exit)
        self.assertEqual(session.permission_profile, PermissionProfile.APPROVE_SAFE)
        self.assertIn("Usage: /permission", output.getvalue())

    def test_permission_command_can_use_choice_provider(self) -> None:
        session = DummySession(cwd=Path.cwd())
        output = io.StringIO()
        requested_current: list[str | None] = []

        with redirect_stdout(output):
            handle_runtime_command(
                session,
                "/permission",
                None,
                build_dummy_adapter,
                lambda _label, _choices, current: requested_current.append(current) or "full-access",
            )

        self.assertEqual(requested_current, ["approve-safe"])
        self.assertEqual(session.permission_profile, PermissionProfile.FULL_ACCESS)
        self.assertIn("Permission changed to full-access", output.getvalue())

    def test_permission_command_without_choice_provider_shows_usage(self) -> None:
        session = DummySession(cwd=Path.cwd())
        output = io.StringIO()

        with redirect_stdout(output):
            should_exit = handle_runtime_command(session, "/permission", None, build_dummy_adapter)

        self.assertFalse(should_exit)
        self.assertEqual(session.permission_profile, PermissionProfile.APPROVE_SAFE)
        self.assertIn("Usage: /permission [PROFILE]", output.getvalue())

    def test_model_command_can_use_choice_provider(self) -> None:
        session = DummySession(cwd=Path.cwd())
        output = io.StringIO()
        requested_current: list[str | None] = []

        with redirect_stdout(output):
            handle_runtime_command(
                session,
                "/model",
                None,
                build_dummy_adapter,
                lambda _label, _choices, current: requested_current.append(current) or "fake",
            )

        self.assertEqual(requested_current, ["fake"])
        self.assertEqual(session.adapter_name, "fake")
        self.assertIsInstance(session.adapter, FakeLLMAdapter)
        self.assertIn("Model changed to fake", output.getvalue())

    def test_model_command_syncs_active_model_registry_when_present(self) -> None:
        session = DummySession(cwd=Path.cwd())
        session.model_registry = ModelRegistry()
        session.active_model_id = "old"

        handle_runtime_command(session, "/model fake", None, build_dummy_adapter)

        self.assertEqual(session.active_model_id, "fake")
        self.assertIs(session.model_registry.resolve("fake"), session.adapter)

    def test_exit_command_requests_exit(self) -> None:
        session = DummySession(cwd=Path.cwd())

        self.assertTrue(handle_runtime_command(session, "/exit", None, build_dummy_adapter))

    def test_runtime_help_describes_commands_and_input_modes(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            render_runtime_help()

        text = output.getvalue()
        self.assertIn("• Runtime commands", text)
        self.assertIn("• Input modes", text)
        self.assertIn("/exit - Exit interactive mode.", text)
        self.assertIn("/process - Expand the last task process", text)
        self.assertIn("/keymap - Show keyboard shortcuts", text)
        self.assertIn("/workflow TASK - Run the built-in workflow", text)
        self.assertIn("/mode - Switch the default execution mode", text)
        self.assertIn("/permission - Set the permission profile", text)
        self.assertNotIn("/allow-command", text)
        self.assertNotIn("/allow-write", text)
        self.assertIn("plain text - send a task to the current execution mode", text)
        self.assertIn("!command - run a user shell command", text)

    def test_keymap_text_lists_shortcuts_by_context(self) -> None:
        text = render_keymap_text()

        self.assertIn("• Keyboard shortcuts", text)
        self.assertIn("Session", text)
        self.assertIn("Ctrl+D", text)
        self.assertIn("Input editing", text)
        self.assertIn("Home / End", text)
        self.assertIn("Completion and history", text)
        self.assertIn("Ctrl+R", text)
        self.assertIn("Multiline", text)
        self.assertIn("Ctrl+J", text)
        self.assertIn("distinguishable modified Enter", text)
        self.assertIn("Quick entries", text)
        self.assertIn("Shift+Tab", text)
        self.assertIn("Cycle execution mode", text)
        self.assertIn("Process view", text)

    def test_keymap_command_prints_keymap_for_non_tty(self) -> None:
        session = DummySession(cwd=Path.cwd())
        output = io.StringIO()

        with redirect_stdout(output), patch("OpenCAI.tui.sys.stdin.isatty", return_value=False):
            should_exit = handle_runtime_command(session, "/keymap", None, build_dummy_adapter)

        self.assertFalse(should_exit)
        self.assertIn("• Keyboard shortcuts", output.getvalue())
        self.assertIn("Ctrl+O", output.getvalue())

    def test_keymap_command_uses_tty_view_when_available(self) -> None:
        session = DummySession(cwd=Path.cwd())

        with (
            patch("OpenCAI.tui.sys.stdin.isatty", return_value=True),
            patch("OpenCAI.tui.show_keymap_view") as show_keymap,
        ):
            should_exit = handle_runtime_command(session, "/keymap", None, build_dummy_adapter)

        self.assertFalse(should_exit)
        show_keymap.assert_called_once()

    def test_keymap_command_rejects_arguments(self) -> None:
        session = DummySession(cwd=Path.cwd())
        output = io.StringIO()

        with redirect_stdout(output):
            should_exit = handle_runtime_command(session, "/keymap extra", None, build_dummy_adapter)

        self.assertFalse(should_exit)
        self.assertIn("Usage: /keymap", output.getvalue())

    def test_runtime_status_uses_output_title_prefix(self) -> None:
        session = DummySession(cwd=Path.cwd())
        output = io.StringIO()

        with redirect_stdout(output):
            render_runtime_status(session)

        self.assertIn("• Runtime status", output.getvalue())

    def test_workflow_command_runs_builtin_workflow_without_exiting(self) -> None:
        session = DummySession(cwd=Path.cwd(), adapter=FakeLLMAdapter())
        output = io.StringIO()

        with redirect_stdout(output):
            should_exit = handle_runtime_command(
                session,
                "/workflow Read README",
                None,
                build_dummy_adapter,
            )

        text = output.getvalue()
        self.assertFalse(should_exit)
        self.assertIn("• Workflow task: Read README", text)
        self.assertIn("• Workflow: inspect_handoff", text)
        self.assertIn("Final phase: handoff", text)
        self.assertIn("2. handoff (final)", text)
        self.assertIn("• Workflow status: passed", text)
        self.assertIn("• Workflow final answer:", text)
        self.assertIn("Fake loop observed README.md and stopped.", text)

    def test_workflow_command_without_task_prints_workflow_usage(self) -> None:
        session = DummySession(cwd=Path.cwd())
        output = io.StringIO()

        with redirect_stdout(output):
            should_exit = handle_runtime_command(session, "/workflow", None, build_dummy_adapter)

        self.assertFalse(should_exit)
        self.assertIn("No task for workflow. Usage: /workflow TASK", output.getvalue())

    def test_process_command_requires_existing_task_events(self) -> None:
        session = DummySession(cwd=Path.cwd(), last_task_events=[])
        output = io.StringIO()

        with redirect_stdout(output):
            should_exit = handle_runtime_command(session, "/process", None, build_dummy_adapter)

        self.assertFalse(should_exit)
        self.assertIn("No process transcript yet.", output.getvalue())

    def test_process_command_expands_last_task_events(self) -> None:
        session = DummySession(
            cwd=Path.cwd(),
            last_task_events=[user_task(1, "Read README"), final_answer(2, "done")],
        )

        with patch("OpenCAI.tui.show_process_view") as show_process:
            should_exit = handle_runtime_command(session, "/process", None, build_dummy_adapter)

        self.assertFalse(should_exit)
        show_process.assert_called_once_with(session.last_task_events)


if __name__ == "__main__":
    unittest.main()
