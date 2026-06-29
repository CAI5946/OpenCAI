from __future__ import annotations

import unittest
from dataclasses import dataclass
from pathlib import Path

from OpenCAI import __version__
from OpenCAI.tui import DEFAULT_STATUS_BAR_ITEMS, render_status_bar


@dataclass
class DummySession:
    cwd: Path
    adapter_name: str = "fake"
    allow_write: bool = False
    allow_command: bool = False


class StatusBarTests(unittest.TestCase):
    def test_default_status_bar_items_are_ordered_for_future_configuration(self) -> None:
        self.assertEqual(
            DEFAULT_STATUS_BAR_ITEMS,
            ("version", "model", "cwd", "permissions"),
        )

    def test_status_bar_renders_default_session_fields(self) -> None:
        session = DummySession(cwd=Path("D:/AI-Agent/Claude_Learn"))

        self.assertEqual(
            render_status_bar(session),
            f"OpenCAI {__version__} · model fake · cwd Claude_Learn · read-only",
        )

    def test_status_bar_summarizes_write_and_command_permissions(self) -> None:
        session = DummySession(
            cwd=Path("D:/AI-Agent/Claude_Learn"),
            adapter_name="gemini",
            allow_write=True,
            allow_command=True,
        )

        self.assertEqual(
            render_status_bar(session),
            f"OpenCAI {__version__} · model gemini · cwd Claude_Learn · write+command",
        )


if __name__ == "__main__":
    unittest.main()
