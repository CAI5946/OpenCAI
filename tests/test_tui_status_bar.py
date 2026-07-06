from __future__ import annotations

import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.output import DummyOutput

from OpenCAI import __version__
from OpenCAI.safety import PermissionProfile
from OpenCAI.tui import (
    DEFAULT_STATUS_BAR_ITEMS,
    EXIT_SHORTCUT_COMMAND,
    INPUT_BORDER_CHAR,
    INPUT_MARKER_COMMAND,
    INPUT_MARKER_DEFAULT,
    INPUT_MARKER_GUIDED,
    INPUT_MARKER_SHELL,
    INPUT_MARKER_WORKFLOW,
    INPUT_PLACEHOLDER,
    INPUT_PROMPT_LABEL,
    MODEL_SHORTCUT_COMMAND,
    PROCESS_SHORTCUT_COMMAND,
    MODE_SHORTCUT_COMMANDS,
    TASK_COMPLETER,
    TASK_PROMPT_STYLE,
    TASK_PROMPT_STYLE_RULES,
    SELECT_PROMPT_STYLE_RULES,
    _choice_items,
    _select_label_text,
    create_keymap_view_key_bindings,
    create_task_input_layout,
    create_task_key_bindings,
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
    permission_profile: PermissionProfile | None = PermissionProfile.APPROVE_SAFE
    execution_mode: str = "agent"


class StatusBarTests(unittest.TestCase):
    def test_default_status_bar_items_are_ordered_for_future_configuration(self) -> None:
        self.assertEqual(
            DEFAULT_STATUS_BAR_ITEMS,
            ("execution_mode", "version", "model", "cwd", "permissions", "max_steps"),
        )

    def test_input_prompt_has_composer_label_and_placeholder(self) -> None:
        self.assertEqual(INPUT_PROMPT_LABEL, "")
        self.assertIn("/", INPUT_PLACEHOLDER)
        self.assertIn("!", INPUT_PLACEHOLDER)

    def test_completion_menu_uses_select_prompt_highlight_style(self) -> None:
        self.assertEqual(TASK_PROMPT_STYLE_RULES["completion-menu"], "fg:default bg:default")
        self.assertEqual(TASK_PROMPT_STYLE_RULES["completion-menu.completion"], "fg:default bg:default")
        self.assertEqual(
            TASK_PROMPT_STYLE_RULES["completion-menu.completion.current"],
            "bold ansibrightcyan bg:default noreverse",
        )
        self.assertEqual(
            TASK_PROMPT_STYLE_RULES["completion-menu.meta.completion"],
            "ansibrightblack bg:default",
        )
        self.assertEqual(
            TASK_PROMPT_STYLE_RULES["completion-menu.meta.completion.current"],
            "bold ansibrightcyan bg:default noreverse",
        )

    def test_select_prompt_uses_terminal_adaptive_style(self) -> None:
        self.assertEqual(SELECT_PROMPT_STYLE_RULES["item"], "fg:default bg:default")
        self.assertEqual(SELECT_PROMPT_STYLE_RULES["description"], "ansibrightblack bg:default")
        self.assertEqual(
            SELECT_PROMPT_STYLE_RULES["opencai-selected"],
            "bold ansibrightcyan bg:default noreverse",
        )
        self.assertEqual(
            SELECT_PROMPT_STYLE_RULES["opencai-selected-description"],
            "bold ansibrightcyan bg:default noreverse",
        )

    def test_choice_items_mark_current_value(self) -> None:
        items = _choice_items("Model", ("fake", "gemini"), current="gemini")

        self.assertFalse(items[0].current)
        self.assertTrue(items[1].current)
        self.assertEqual(items[1].label, "Gemini 2.5 Flash")

    def test_select_label_text_includes_current_marker_for_alignment(self) -> None:
        items = _choice_items("Model", ("fake", "gemini"), current="fake")
        label_texts = tuple(_select_label_text(index, item, index == 0) for index, item in enumerate(items))

        self.assertIn("(current)", label_texts[0])
        self.assertNotIn("(current)", label_texts[1])
        self.assertGreater(len(label_texts[0]), len("› 1. Fake"))

    def test_input_border_has_stable_minimum_width(self) -> None:
        self.assertEqual(render_input_border(5), INPUT_BORDER_CHAR * 20)
        self.assertEqual(render_input_border(24), INPUT_BORDER_CHAR * 24)

    def test_input_status_line_renders_below_input_with_status(self) -> None:
        status_line = render_input_status_line("agent · 0.0.0-dev · fake · Claude_Learn · read-only · step 5")

        self.assertEqual(
            status_line,
            [("class:input-status", "task mode · agent · 0.0.0-dev · fake · Claude_Learn · read-only · step 5")],
        )

    def test_workflow_mode_status_line_has_special_style_for_plain_task(self) -> None:
        status_line = render_input_status_line("workflow · fake", input_text="Read README", execution_mode="workflow")

        self.assertEqual(status_line, [("class:input-status-workflow", "workflow mode · workflow · fake")])

    def test_guided_mode_status_line_has_special_style_for_plain_task(self) -> None:
        status_line = render_input_status_line("guided · fake", input_text="Read README", execution_mode="guided")

        self.assertEqual(status_line, [("class:input-status-guided", "guided mode · guided · fake")])

    def test_input_status_line_changes_mode_by_input_text(self) -> None:
        command_status = render_input_status_line("fake", input_text="/status")
        shell_status = render_input_status_line("fake", input_text="!python --version")

        self.assertEqual(command_status, [("class:input-status", "command mode · fake")])
        self.assertEqual(shell_status, [("class:input-status", "shell mode · fake")])

    def test_input_marker_keeps_one_visible_prompt_symbol_with_mode_color(self) -> None:
        self.assertEqual(input_marker_for_text("read README"), (INPUT_MARKER_DEFAULT, "class:input-marker"))
        self.assertEqual(
            input_marker_for_text("read README", execution_mode="workflow"),
            (INPUT_MARKER_WORKFLOW, "class:input-marker-workflow"),
        )
        self.assertEqual(
            input_marker_for_text("read README", execution_mode="guided"),
            (INPUT_MARKER_GUIDED, "class:input-marker-guided"),
        )
        self.assertEqual(input_marker_for_text("/status"), (INPUT_MARKER_COMMAND, "class:input-marker-command"))
        self.assertEqual(input_marker_for_text("!python --version"), (INPUT_MARKER_SHELL, "class:input-marker-shell"))

    def test_input_mode_changes_by_input_text(self) -> None:
        self.assertEqual(input_mode_for_text("read README"), "task")
        self.assertEqual(input_mode_for_text("read README", execution_mode="guided"), "guided")
        self.assertEqual(input_mode_for_text("read README", execution_mode="workflow"), "workflow")
        self.assertEqual(input_mode_for_text("/status"), "command")
        self.assertEqual(input_mode_for_text("!python --version"), "shell")

    def test_submitted_input_line_is_concise_and_mode_aware(self) -> None:
        self.assertEqual(render_submitted_input_line("Read README"), "• Submitted task:\nRead README")
        self.assertEqual(
            render_submitted_input_line("Read README", execution_mode="workflow"),
            "• Submitted workflow:\nRead README",
        )
        self.assertEqual(
            render_submitted_input_line("Read README", execution_mode="guided"),
            "• Submitted guided:\nRead README",
        )
        self.assertEqual(render_submitted_input_line("/status"), "• Submitted command:\n/status")
        self.assertEqual(render_submitted_input_line("!python --version"), "• Submitted shell:\n!python --version")

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
                key_bindings=create_task_key_bindings(),
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("/status\r")

            self.assertEqual(app.run(), "/status")

    def test_task_input_layout_allows_multiline_input_to_remain_visible(self) -> None:
        buffer = Buffer(multiline=True)
        layout = create_task_input_layout(buffer, "model fake")
        input_window = next(
            window for window in layout.find_all_windows() if isinstance(window.content, BufferControl)
        )

        self.assertTrue(input_window.wrap_lines())
        self.assertTrue(input_window.dont_extend_height())
        self.assertEqual(input_window.height.min, 1)
        self.assertGreaterEqual(input_window.height.max, 4)

    def test_ctrl_o_exits_composer_with_process_command_handoff(self) -> None:
        with create_pipe_input() as pipe_input:
            app = Application(
                layout=create_task_input_layout(Buffer(multiline=False), "model fake"),
                key_bindings=create_task_key_bindings(),
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("\x0f")

            self.assertEqual(app.run(), PROCESS_SHORTCUT_COMMAND)

    def test_ctrl_d_exits_composer_with_exit_command_handoff(self) -> None:
        with create_pipe_input() as pipe_input:
            app = Application(
                layout=create_task_input_layout(Buffer(multiline=False), "model fake"),
                key_bindings=create_task_key_bindings(),
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("\x04")

            self.assertEqual(app.run(), EXIT_SHORTCUT_COMMAND)

    def test_ctrl_c_exits_empty_composer_with_exit_command_handoff(self) -> None:
        with create_pipe_input() as pipe_input:
            app = Application(
                layout=create_task_input_layout(Buffer(multiline=False), "model fake"),
                key_bindings=create_task_key_bindings(),
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("\x03")

            self.assertEqual(app.run(), EXIT_SHORTCUT_COMMAND)

    def test_ctrl_c_clears_input_draft_before_submit(self) -> None:
        with create_pipe_input() as pipe_input:
            app: Application[str] | None = None

            def accept_input(buffer: Buffer) -> bool:
                if app is not None:
                    app.exit(result=buffer.text)
                return True

            buffer = Buffer(accept_handler=accept_input, multiline=True)
            app = Application(
                layout=create_task_input_layout(buffer, "model fake"),
                key_bindings=create_task_key_bindings(),
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("draft\x03final\r")

            self.assertEqual(app.run(), "final")

    def test_alt_p_exits_composer_with_model_command_handoff(self) -> None:
        with create_pipe_input() as pipe_input:
            app = Application(
                layout=create_task_input_layout(Buffer(multiline=False), "model fake"),
                key_bindings=create_task_key_bindings(),
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("\x1bp")

            self.assertEqual(app.run(), MODEL_SHORTCUT_COMMAND)

    def test_shift_tab_cycles_execution_mode_with_command_handoff(self) -> None:
        with create_pipe_input() as pipe_input:
            app = Application(
                layout=create_task_input_layout(Buffer(multiline=False), "model fake"),
                key_bindings=create_task_key_bindings("agent"),
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("\x1b[Z")

            self.assertEqual(app.run(), "/mode guided")
            self.assertEqual(MODE_SHORTCUT_COMMANDS, ("/mode agent", "/mode guided", "/mode workflow"))

    def test_ctrl_j_inserts_newline_and_enter_submits_multiline_input(self) -> None:
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
                multiline=True,
            )
            app = Application(
                layout=create_task_input_layout(buffer, "model fake"),
                key_bindings=create_task_key_bindings(),
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("first\x0asecond\r")

            self.assertEqual(app.run(), "first\nsecond")

    def test_shift_enter_csi_u_inserts_newline_and_enter_submits(self) -> None:
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
                multiline=True,
            )
            app = Application(
                layout=create_task_input_layout(buffer, "model fake"),
                key_bindings=create_task_key_bindings(),
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("first\x1b[13;2usecond\r")

            self.assertEqual(app.run(), "first\nsecond")

    def test_shift_enter_xterm_modified_enter_inserts_newline_and_enter_submits(self) -> None:
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
                multiline=True,
            )
            app = Application(
                layout=create_task_input_layout(buffer, "model fake"),
                key_bindings=create_task_key_bindings(),
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("first\x1b[27;2;13~second\r")

            self.assertEqual(app.run(), "first\nsecond")

    def test_shift_enter_windows_console_event_maps_to_newline(self) -> None:
        from prompt_toolkit.input.win32 import ConsoleInputReader
        from prompt_toolkit.keys import Keys
        from prompt_toolkit.win32_types import KEY_EVENT_RECORD

        reader = ConsoleInputReader.__new__(ConsoleInputReader)
        event = KEY_EVENT_RECORD()
        event.KeyDown = True
        event.VirtualKeyCode = 13
        event.uChar.UnicodeChar = "\r"
        event.ControlKeyState = ConsoleInputReader.SHIFT_PRESSED

        key_presses = reader._event_to_key_presses(event)

        self.assertEqual(tuple(key.key for key in key_presses), (Keys.ControlJ,))

    def test_history_arrows_browse_history_when_suggestions_are_hidden(self) -> None:
        with create_pipe_input() as pipe_input:
            app: Application[str] | None = None

            def accept_input(buffer: Buffer) -> bool:
                if app is not None:
                    app.exit(result=buffer.text)
                return True

            buffer = __import__("OpenCAI.tui", fromlist=["create_task_buffer"]).create_task_buffer(
                accept_input,
                history_entries=["Read README"],
            )
            app = Application(
                layout=create_task_input_layout(buffer, "model fake"),
                key_bindings=create_task_key_bindings(),
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("\x1b[A\r")

            self.assertEqual(app.run(), "Read README")

    def test_ctrl_r_searches_prompt_history(self) -> None:
        with create_pipe_input() as pipe_input:
            app: Application[str] | None = None

            def accept_input(buffer: Buffer) -> bool:
                if app is not None:
                    app.exit(result=buffer.text)
                return True

            buffer = __import__("OpenCAI.tui", fromlist=["create_task_buffer"]).create_task_buffer(
                accept_input,
                history_entries=["Read README", "Run tests"],
            )
            app = Application(
                layout=create_task_input_layout(buffer, "model fake"),
                key_bindings=create_task_key_bindings(),
                full_screen=False,
                erase_when_done=False,
                style=TASK_PROMPT_STYLE,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("read\x12\r")

            self.assertEqual(app.run(), "Read README")

    def test_keymap_view_key_bindings_exit_without_selection(self) -> None:
        for key in ("\x1b", "\r", "q", "\x03"):
            with create_pipe_input() as pipe_input:
                app: Application[None] = Application(
                    layout=create_task_input_layout(Buffer(multiline=False), "model fake"),
                    key_bindings=create_keymap_view_key_bindings(),
                    full_screen=False,
                    erase_when_done=True,
                    style=TASK_PROMPT_STYLE,
                    input=pipe_input,
                    output=DummyOutput(),
                )
                pipe_input.send_text(key)

                self.assertIsNone(app.run())

    def test_ask_task_does_not_echo_process_shortcut_handoff(self) -> None:
        with (
            patch("OpenCAI.tui.sys.stdin.isatty", return_value=True),
            patch("OpenCAI.tui.Application") as application,
            patch("OpenCAI.tui.render_submitted_input") as render_submitted,
        ):
            application.return_value.run.return_value = PROCESS_SHORTCUT_COMMAND

            self.assertEqual(
                __import__("OpenCAI.tui", fromlist=["ask_task"]).ask_task(),
                PROCESS_SHORTCUT_COMMAND,
            )

        render_submitted.assert_not_called()

    def test_status_bar_renders_default_session_fields(self) -> None:
        session = DummySession(cwd=Path("D:/AI-Agent/Claude_Learn"))

        self.assertEqual(
            render_status_bar(session),
            f"agent · {__version__} · fake · Claude_Learn · approve-safe · step 3",
        )

    def test_status_bar_renders_permission_profile(self) -> None:
        session = DummySession(
            cwd=Path("D:/AI-Agent/Claude_Learn"),
            adapter_name="gemini",
            max_steps=8,
            permission_profile=PermissionProfile.APPROVE_SAFE,
        )

        self.assertEqual(
            render_status_bar(session),
            f"agent · {__version__} · gemini · Claude_Learn · approve-safe · step 8",
        )

    def test_status_bar_renders_workflow_mode(self) -> None:
        session = DummySession(cwd=Path("D:/AI-Agent/Claude_Learn"), execution_mode="workflow")

        self.assertEqual(
            render_status_bar(session),
            f"workflow · {__version__} · fake · Claude_Learn · approve-safe · step 3",
        )

    def test_status_bar_renders_guided_mode(self) -> None:
        session = DummySession(cwd=Path("D:/AI-Agent/Claude_Learn"), execution_mode="guided")

        self.assertEqual(
            render_status_bar(session),
            f"guided · {__version__} · fake · Claude_Learn · approve-safe · step 3",
        )


if __name__ == "__main__":
    unittest.main()
