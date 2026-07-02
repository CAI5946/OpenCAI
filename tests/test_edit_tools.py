from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from OpenCAI.tools import run_tool


class EditToolsTests(unittest.TestCase):
    def test_edit_file_replaces_exactly_one_match_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            target = cwd / "demo.txt"
            target.write_text("one two one", encoding="utf-8")

            result = run_tool("edit_file", {"path": "demo.txt", "old": "one", "new": "three"}, cwd)
            content = target.read_text(encoding="utf-8")

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["replacements"], 1)
        self.assertEqual(content, "three two one")

    def test_apply_patch_add_update_delete_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "old.txt").write_text("alpha\nbeta\n", encoding="utf-8")
            patch = """*** Begin Patch
*** Add File: added.txt
+created
*** Update File: old.txt
@@
-alpha
+ALPHA
*** Delete File: delete.txt
*** End Patch
"""
            (cwd / "delete.txt").write_text("remove", encoding="utf-8")

            result = run_tool("apply_patch", {"patch": patch}, cwd)

            added = (cwd / "added.txt").read_text(encoding="utf-8")
            updated = (cwd / "old.txt").read_text(encoding="utf-8")
            deleted_exists = (cwd / "delete.txt").exists()

        self.assertTrue(result["ok"])
        self.assertEqual(added, "created\n")
        self.assertIn("ALPHA", updated)
        self.assertFalse(deleted_exists)
        self.assertEqual(result["result"]["operations"], 3)

    def test_apply_patch_preserves_old_path_schema_for_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            target = cwd / "demo.txt"
            target.write_text("old", encoding="utf-8")

            result = run_tool("apply_patch", {"path": "demo.txt", "old": "old", "new": "new"}, cwd)
            content = target.read_text(encoding="utf-8")

        self.assertTrue(result["ok"])
        self.assertEqual(content, "new")


if __name__ == "__main__":
    unittest.main()
