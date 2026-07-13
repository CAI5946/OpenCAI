from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import time
import unittest

from OpenCAI.tooling.command_tools import (
    COMMAND_SESSIONS,
    read_command,
    run_command,
    start_command,
    stop_command,
    write_stdin,
)


def _python_command(code: str) -> str:
    return f'"{sys.executable}" -u -c "{code}"'


def _read_until(command_id: str, cwd: Path, needle: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.time() + timeout
    last: dict[str, object] = {}
    while time.time() < deadline:
        result = read_command({"command_id": command_id}, cwd)
        last = result["result"]
        stdout = str(last.get("stdout", ""))
        stderr = str(last.get("stderr", ""))
        if needle in stdout or needle in stderr:
            return last
        time.sleep(0.05)
    return last


class CommandToolsTests(unittest.TestCase):
    def tearDown(self) -> None:
        for command_id in list(COMMAND_SESSIONS):
            stop_command({"command_id": command_id}, Path.cwd())

    def test_run_command_supports_cwd_and_output_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            child = cwd / "child"
            child.mkdir()
            command = _python_command("print('abcdef')")

            result = run_command(
                {
                    "command": command,
                    "cwd": "child",
                    "max_output_chars": 4,
                    "timeout": 5,
                },
                cwd,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["stdout"], "def\n")
        self.assertTrue(result["result"]["stdout_truncated"])
        self.assertEqual(result["result"]["stdout_chars"], 7)
        self.assertTrue(str(result["result"]["cwd"]).endswith("child"))

    def test_run_command_rejects_windows_style_cwd_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp) / "workspace"
            cwd.mkdir()

            result = run_command(
                {"command": _python_command("print('unsafe')"), "cwd": "..\\outside"},
                cwd,
            )

        self.assertFalse(result["ok"])
        self.assertIn("cwd escapes workspace", result["error"] or "")

    def test_run_command_returns_partial_result_on_timeout(self) -> None:
        command = _python_command("import time; print('before'); time.sleep(2)")

        result = run_command({"command": command, "timeout": 1}, Path.cwd())

        self.assertFalse(result["ok"])
        self.assertIn("timed out", result["error"] or "")
        self.assertTrue(result["result"]["timed_out"])

    def test_start_read_write_and_stop_command_session(self) -> None:
        command = _python_command(
            "import sys; print('ready'); sys.stdout.flush(); "
            "line=sys.stdin.readline(); print('got:'+line.strip()); sys.stdout.flush()"
        )
        started = start_command({"command": command}, Path.cwd())
        command_id = str(started["result"]["command_id"])

        ready = _read_until(command_id, Path.cwd(), "ready")
        write_result = write_stdin({"command_id": command_id, "text": "hello\n"}, Path.cwd())
        got = _read_until(command_id, Path.cwd(), "got:hello")

        self.assertTrue(started["ok"])
        self.assertIn("ready", str(ready.get("stdout", "")))
        self.assertTrue(write_result["ok"])
        self.assertIn("got:hello", str(got.get("stdout", "")))
        self.assertNotIn(command_id, COMMAND_SESSIONS)

    def test_read_command_rejects_unknown_session(self) -> None:
        result = read_command({"command_id": "missing"}, Path.cwd())

        self.assertFalse(result["ok"])
        self.assertIn("Unknown command session", result["error"] or "")


if __name__ == "__main__":
    unittest.main()
