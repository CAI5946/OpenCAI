from __future__ import annotations

import unittest
from dataclasses import dataclass
from pathlib import Path

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput

from OpenCAI import __version__
from OpenCAI.tui import (
    DEFAULT_STATUS_BAR_ITEMS,
    INPUT_BORDER_CHAR,
    INPUT_MARKER_COMMAND,
    INPUT_MARKER_DEFAULT,
    INPUT_MARKER_SHELL,
    INPUT_PLACEHOLDER,
    INPUT_PROMPT_LABEL,
    TASK_COMPLETER,
    TASK_KEY_BINDINGS,
    TASK_PROMPT_STYLE,
    create_task_input_layout,
    input_mode_for_text,
    input_marker_for_text,
    render_input_border,
    render_input_status_line,
    render_submitted_input_line,
    render_status_bar,
)


@dataclass
class DummySession:
    cwd: Path
    adapter_name: str = "fake"
    max_steps: int = 3
    allow_write: bool = False
    allow_command: bool = False


class StatusBarTests(unittest.TestCase):
    def test_default_status_bar_items_are_ordered_for_future_configuration(self) -> None:
        self.assertEqual(
            DEFAULT_STATUS_BAR_ITEMS,
            ("version", "model", "cwd", "permissions", "max_steps"),
        )

    def test_input_prompt_has_composer_label_and_placeholder(self) -> None:
        self.assertEqual(INPUT_PROMPT_LABEL, "")
        self.assertIn("/", INPUT_PLACEHOLDER)
        self.assertIn("!", INPUT_PLACEHOLDER)

    def test_input_border_has_stable_minimum_width(self) -> None:
        self.assertEqual(render_input_border(5), INPUT_BORDER_CHAR * 20)
        self.assertEqual(render_input_border(24), INPUT_BORDER_CHAR * 24)

    def test_input_status_line_renders_below_input_with_status(self) -> None:
        status_line = render_input_status_line("0.0.0-dev · fake · Claude_Learn · read-only · step 5")

        self.assertEqual(
            status_line,
            [("class:input-status", "task mode · 0.0.0-dev · fake · Claude_Learn · read-only · step 5")],
        )

    def test_input_status_line_changes_mode_by_input_text(self) -> None:
        command_status = render_input_status_line("fake", input_text="/status")
        shell_status = render_input_status_line("fake", input_text="!python --version")

        self.assertEqual(command_status, [("class:input-status", "command mode · fake")])
        self.assertEqual(shell_status, [("class:input-status", "shell mode · fake")])

    def test_input_marker_keeps_one_visible_prompt_symbol_with_mode_color(self) -> None:
        self.assertEqual(input_marker_for_text("read README"), (INPUT_MARKER_DEFAULT, "class:input-marker"))
        self.assertEqual(input_marker_for_text("/status"), (INPUT_MARKER_COMMAND, "class:input-marker-command"))
        self.assertEqual(input_marker_for_text("!python --version"), (INPUT_MARKER_SHELL, "class:input-marker-shell"))

    def test_input_mode_changes_by_input_text(self) -> None:
        self.assertEqual(input_mode_for_text("read README"), "task")
        self.assertEqual(input_mode_for_text("/status"), "command")
        self.assertEqual(input_mode_for_text("!python --version"), "shell")

    def test_submitted_input_line_is_concise_and_mode_aware(self) -> None:
        self.assertEqual(render_submitted_input_line("Read README"), "Submitted task: Read README")
        self.assertEqual(render_submitted_input_line("/status"), "Submitted command: /status")
        self.assertEqual(render_submitted_input_line("!python --version"), "Submitted shell: !python --version")

    def test_submitted_input_line_is_empty_for_blank_input(self) -> None:
        self.assertEqual(render_submitted_input_line("   "), "")

    def test_task_input_layout_accepts_enter_submission(self) -> None:
        with create_pipe_input() as pipe_input:
            app: Application[str] | None = None

            def accept_input(buffer: Buffer) -> bool:
                if app is not None:
                    app.exit(result=buffer.text)
                return True

            buffer = Buffer(
                completer=TASK_COMPLETER,
                complete_while_typing=True,
                accept_handler=accept_input,
                multiline=False,
            )
            app = Application(
                layout=create_task_input_layout(buffer, "model fake"),
                key_bindings=TASK_KEY_BINDINGS,
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("/status\r")

            self.assertEqual(app.run(), "/status")

    def test_status_bar_renders_default_session_fields(self) -> None:
        session = DummySession(cwd=Path("D:/AI-Agent/Claude_Learn"))

        self.assertEqual(
            render_status_bar(session),
            f"{__version__} · fake · Claude_Learn · read-only · step 3",
        )

    def test_status_bar_summarizes_write_and_command_permissions(self) -> None:
        session = DummySession(
            cwd=Path("D:/AI-Agent/Claude_Learn"),
            adapter_name="gemini",
            max_steps=8,
            allow_write=True,
            allow_command=True,
        )

        self.assertEqual(
            render_status_bar(session),
            f"{__version__} · gemini · Claude_Learn · write+command · step 8",
        )


if __name__ == "__main__":
    unittest.main()
