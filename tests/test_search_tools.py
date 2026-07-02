from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from OpenCAI.tools import run_tool


class SearchToolsTests(unittest.TestCase):
    def test_list_files_returns_structured_directory_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "src").mkdir()
            (cwd / "src" / "app.py").write_text("print('hi')", encoding="utf-8")

            result = run_tool("list_files", {"path": "."}, cwd)

        self.assertTrue(result["ok"])
        names = {entry["path"] for entry in result["result"]["entries"]}
        self.assertIn("src", names)
        self.assertTrue(any(entry["is_dir"] for entry in result["result"]["entries"]))

    def test_glob_files_matches_paths_and_skips_common_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "pkg").mkdir()
            (cwd / "node_modules").mkdir()
            (cwd / "pkg" / "a.py").write_text("", encoding="utf-8")
            (cwd / "node_modules" / "skip.py").write_text("", encoding="utf-8")

            result = run_tool("glob_files", {"pattern": "**/*.py"}, cwd)

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["matches"], ["pkg\\a.py"])

    def test_search_files_supports_case_and_include_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "app.py").write_text("Token\n", encoding="utf-8")
            (cwd / "readme.md").write_text("token\n", encoding="utf-8")

            result = run_tool(
                "search_files",
                {
                    "pattern": "token",
                    "include": "*.md",
                    "case_sensitive": False,
                    "max_results": 5,
                },
                cwd,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["result"]["matches"]), 1)
        self.assertEqual(result["result"]["matches"][0]["path"], "readme.md")
        self.assertEqual(result["result"]["matches"][0]["column"], 1)


if __name__ == "__main__":
    unittest.main()
