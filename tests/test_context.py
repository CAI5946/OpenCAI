from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from OpenCAI.context import ContextComposer, ContextProvider
from OpenCAI.session_context import SessionContext, SessionTurnSummary


class ContextProviderTests(unittest.TestCase):
    def test_collect_records_context_entry_points_without_reading_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            global_agents = root / "global" / "AGENTS.md"
            global_agents.parent.mkdir()
            global_agents.write_text("global rules", encoding="utf-8")
            (root / "AGENTS.md").write_text("project rules", encoding="utf-8")
            (root / "README.md").write_text("readme", encoding="utf-8")
            docs = root / "docs"
            docs.mkdir()
            (docs / "status.md").write_text("status", encoding="utf-8")

            snapshot = ContextProvider(
                global_agents_path=global_agents,
            ).collect(
                cwd=root,
                adapter_name="fake",
                permission_profile="approve-safe",
                max_steps=8,
            )

        self.assertEqual(snapshot.cwd, root.resolve())
        self.assertEqual(snapshot.repo_root, root.resolve())
        self.assertTrue(snapshot.global_agents.exists)
        self.assertEqual(snapshot.global_agents.path, global_agents.resolve())
        self.assertEqual(snapshot.global_instructions.content, "global rules")
        self.assertTrue(snapshot.project_agents.exists)
        self.assertEqual(snapshot.project_agents.path, (root / "AGENTS.md").resolve())
        self.assertEqual(snapshot.project_instructions.content, "project rules")
        self.assertTrue(snapshot.readme.exists)
        self.assertTrue(snapshot.status_doc.exists)
        self.assertEqual(snapshot.runtime.adapter_name, "fake")
        self.assertEqual(snapshot.runtime.permission_profile, "approve-safe")
        self.assertEqual(snapshot.runtime.max_steps, 8)

    def test_collect_falls_back_cleanly_outside_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            snapshot = ContextProvider(
                global_agents_path=root / "missing-global.md",
            ).collect(
                cwd=root,
                adapter_name="gemini",
                permission_profile="read-only",
                max_steps=3,
            )

        self.assertEqual(snapshot.repo_root, root.resolve())
        self.assertFalse(snapshot.global_agents.exists)
        self.assertFalse(snapshot.project_agents.exists)
        self.assertIsNone(snapshot.git.branch)
        self.assertFalse(snapshot.git.dirty)
        self.assertEqual(snapshot.git.short_status, "")
        self.assertIsNotNone(snapshot.git.warning)

    def test_collect_truncates_instruction_files_without_summarizing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            global_agents = root / "global.md"
            global_agents.write_text("abcdef", encoding="utf-8")

            snapshot = ContextProvider(
                global_agents_path=global_agents,
                max_instruction_chars=3,
            ).collect(
                cwd=root,
                adapter_name="fake",
                permission_profile="approve-safe",
                max_steps=8,
            )

        self.assertEqual(snapshot.global_instructions.content, "abc")
        self.assertTrue(snapshot.global_instructions.truncated)
        self.assertIn("truncated", snapshot.global_instructions.warning or "")

    def test_compose_orders_system_project_global_environment_then_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            global_agents = root / "global" / "AGENTS.md"
            global_agents.parent.mkdir()
            global_agents.write_text("global rule", encoding="utf-8")
            (root / "AGENTS.md").write_text("project rule", encoding="utf-8")

            snapshot = ContextProvider(
                global_agents_path=global_agents,
            ).collect(
                cwd=root,
                adapter_name="fake",
                permission_profile="approve-safe",
                max_steps=8,
            )

        messages = ContextComposer().compose(snapshot, "Implement context composer")

        self.assertEqual([message["role"] for message in messages], ["system", "user", "user", "user", "user"])
        self.assertIn("OpenCAI", messages[0]["content"])
        self.assertIn("<project_instructions", messages[1]["content"])
        self.assertIn("project rule", messages[1]["content"])
        self.assertIn("override global", messages[1]["content"])
        self.assertIn("<global_instructions", messages[2]["content"])
        self.assertIn("global rule", messages[2]["content"])
        self.assertIn("<environment_context>", messages[3]["content"])
        self.assertEqual(messages[4]["content"], "Implement context composer")

    def test_compose_includes_session_context_before_current_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = ContextProvider(
                global_agents_path=root / "missing-global.md",
            ).collect(
                cwd=root,
                adapter_name="fake",
                permission_profile="approve-safe",
                max_steps=8,
            )

        session_context = SessionContext(
            running_summary="Earlier work: checked README.",
            recent_turns=[
                SessionTurnSummary(
                    user_task="Inspect status",
                    final_answer="Status is current.",
                    tool_calls=("read_file",),
                    verification_results=(),
                    errors=(),
                )
            ],
        )

        messages = ContextComposer().compose(
            snapshot,
            "Continue the work",
            session_context=session_context,
        )

        self.assertIn("<session_context", messages[-2]["content"])
        self.assertIn("Earlier work: checked README.", messages[-2]["content"])
        self.assertIn("Inspect status", messages[-2]["content"])
        self.assertEqual(messages[-1]["content"], "Continue the work")


if __name__ == "__main__":
    unittest.main()
