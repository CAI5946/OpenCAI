from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path

from OpenCAI.llm_adapter import FakeLLMAdapter, LLMAdapter
from OpenCAI.runtime_commands import (
    handle_runtime_command,
    parse_on_off,
    render_runtime_help,
    runtime_command_completion_tree,
)


@dataclass
class DummySession:
    cwd: Path
    adapter_name: str = "fake"
    adapter: LLMAdapter | None = None
    max_steps: int = 3
    allow_write: bool = False
    allow_command: bool = False
    turn_count: int = 0


def build_dummy_adapter(adapter_name: str, api_key: str | None) -> LLMAdapter:
    if adapter_name != "fake":
        raise AssertionError(f"unexpected adapter: {adapter_name}")
    return FakeLLMAdapter()


class RuntimeCommandTests(unittest.TestCase):
    def test_completion_tree_contains_runtime_commands_and_choices(self) -> None:
        tree = runtime_command_completion_tree()

        self.assertIn("/model", tree)
        self.assertIsNone(tree["/model"])
        self.assertEqual(tree["/allow-write"], {"on": None, "off": None})

    def test_parse_on_off(self) -> None:
        self.assertIs(parse_on_off("on"), True)
        self.assertIs(parse_on_off("false"), False)
        self.assertIsNone(parse_on_off("maybe"))

    def test_handle_runtime_command_updates_session(self) -> None:
        session = DummySession(cwd=Path.cwd())

        should_exit = handle_runtime_command(session, "/max-steps 8", None, build_dummy_adapter)
        self.assertFalse(should_exit)
        self.assertEqual(session.max_steps, 8)

        handle_runtime_command(session, "/allow-write on", None, build_dummy_adapter)
        self.assertTrue(session.allow_write)

        handle_runtime_command(session, "/model fake", None, build_dummy_adapter)
        self.assertEqual(session.adapter_name, "fake")
        self.assertIsInstance(session.adapter, FakeLLMAdapter)

    def test_model_command_can_use_choice_provider(self) -> None:
        session = DummySession(cwd=Path.cwd())

        handle_runtime_command(
            session,
            "/model",
            None,
            build_dummy_adapter,
            lambda _label, _choices: "fake",
        )

        self.assertEqual(session.adapter_name, "fake")
        self.assertIsInstance(session.adapter, FakeLLMAdapter)

    def test_exit_command_requests_exit(self) -> None:
        session = DummySession(cwd=Path.cwd())

        self.assertTrue(handle_runtime_command(session, "/exit", None, build_dummy_adapter))

    def test_runtime_help_describes_commands_and_input_modes(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            render_runtime_help()

        text = output.getvalue()
        self.assertIn("/exit - Exit interactive mode.", text)
        self.assertIn("/allow-command on|off - Enable or disable command execution", text)
        self.assertIn("plain text - send a task to the agent loop", text)
        self.assertIn("!command - run a user shell command", text)


if __name__ == "__main__":
    unittest.main()
