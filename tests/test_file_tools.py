from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from OpenCAI.tools import TOOLS, run_tool


class FileToolsTests(unittest.TestCase):
    def test_write_file_creates_parent_dirs_and_read_file_can_limit_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            written = run_tool(
                "write_file",
                {"path": "src/demo.txt", "content": "abcdef", "create_dirs": True},
                cwd,
            )
            read = run_tool("read_file", {"path": "src/demo.txt", "max_chars": 3}, cwd)

        self.assertTrue(written["ok"])
        self.assertTrue(written["result"]["created"])
        self.assertEqual(written["result"]["bytes_written"], 6)
        self.assertTrue(read["ok"])
        self.assertEqual(read["result"]["content"], "abc")
        self.assertTrue(read["result"]["truncated"])
        self.assertIn("write_file", TOOLS)

    def test_write_file_refuses_overwrite_unless_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "demo.txt").write_text("old", encoding="utf-8")

            refused = run_tool("write_file", {"path": "demo.txt", "content": "new"}, cwd)
            overwritten = run_tool(
                "write_file",
                {"path": "demo.txt", "content": "new", "overwrite": True},
                cwd,
            )

        self.assertFalse(refused["ok"])
        self.assertIn("already exists", refused["error"] or "")
        self.assertTrue(overwritten["ok"])
        self.assertTrue(overwritten["result"]["overwritten"])

    def test_copy_move_and_delete_file_keep_workspace_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "a.txt").write_text("hello", encoding="utf-8")

            copied = run_tool("copy_file", {"source": "a.txt", "destination": "b.txt"}, cwd)
            moved = run_tool("move_file", {"source": "b.txt", "destination": "nested/c.txt"}, cwd)
            deleted = run_tool("delete_file", {"path": "nested/c.txt"}, cwd)

            source_exists = (cwd / "a.txt").exists()
            moved_exists = (cwd / "nested/c.txt").exists()

        self.assertTrue(copied["ok"])
        self.assertTrue(moved["ok"])
        self.assertTrue(deleted["ok"])
        self.assertTrue(source_exists)
        self.assertFalse(moved_exists)

    def test_file_tools_reject_path_escape_when_called_directly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp) / "workspace"
            cwd.mkdir()
            result = run_tool("write_file", {"path": "..\\secret.txt", "content": "x"}, cwd)

        self.assertFalse(result["ok"])
        self.assertIn("escapes workspace", result["error"] or "")


if __name__ == "__main__":
    unittest.main()
