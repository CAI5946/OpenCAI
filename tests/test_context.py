from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from OpenCAI.context import ContextComposer, ContextProvider
from OpenCAI.demand import DemandBrief
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

    def test_collect_discovers_project_and_user_skill_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_skill = root / ".opencai" / "skills" / "project-skill"
            user_skill_root = root / "AgentSkills"
            user_skill = user_skill_root / "user-skill"
            project_skill.mkdir(parents=True)
            user_skill.mkdir(parents=True)
            (project_skill / "SKILL.md").write_text(
                "---\n"
                "description: Project workflow.\n"
                "---\n\n"
                "# Project Skill\n",
                encoding="utf-8",
            )
            (user_skill / "SKILL.md").write_text(
                "---\n"
                "description: User workflow.\n"
                "---\n\n"
                "# User Skill\n",
                encoding="utf-8",
            )

            snapshot = ContextProvider(
                global_agents_path=root / "missing-global.md",
                user_skills_path=user_skill_root,
            ).collect(
                cwd=root,
                adapter_name="fake",
                permission_profile="approve-safe",
                max_steps=8,
            )

        self.assertEqual(["project-skill", "user-skill"], [skill.name for skill in snapshot.skills.summaries])
        self.assertEqual("Project workflow.", snapshot.skills.summaries[0].description)

    def test_compose_orders_system_project_global_environment_then_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            global_agents = root / "global" / "AGENTS.md"
            global_agents.parent.mkdir()
            global_agents.write_text("global rule", encoding="utf-8")
            (root / "AGENTS.md").write_text("project rule", encoding="utf-8")

            snapshot = ContextProvider(
                global_agents_path=global_agents,
                user_skills_path=root / "missing-skills",
            ).collect(
                cwd=root,
                adapter_name="fake",
                permission_profile="approve-safe",
                max_steps=8,
            )

        messages = ContextComposer().compose(snapshot, "Implement context composer")

        self.assertEqual([message["role"] for message in messages], ["system", "user", "user", "user", "user", "user"])
        self.assertEqual(
            [message["kind"] for message in messages],
            [
                "system_prompt",
                "project_instructions",
                "global_instructions",
                "available_skills",
                "environment_context",
                "user_task",
            ],
        )
        self.assertIn("OpenCAI", messages[0]["content"])
        self.assertIn("<project_instructions", messages[1]["content"])
        self.assertIn("project rule", messages[1]["content"])
        self.assertIn("override global", messages[1]["content"])
        self.assertIn("<global_instructions", messages[2]["content"])
        self.assertIn("global rule", messages[2]["content"])
        self.assertIn("<available_skills", messages[3]["content"])
        self.assertIn("<environment_context>", messages[4]["content"])
        self.assertEqual(messages[5]["content"], "Implement context composer")

    def test_compose_includes_skill_registry_summary_without_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / ".opencai" / "skills" / "doc-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "description: Update docs.\n"
                "---\n\n"
                "# Doc Skill\n",
                encoding="utf-8",
            )

            snapshot = ContextProvider(
                global_agents_path=root / "missing-global.md",
                user_skills_path=root / "missing-skills",
            ).collect(
                cwd=root,
                adapter_name="fake",
                permission_profile="approve-safe",
                max_steps=8,
            )

        messages = ContextComposer().compose(snapshot, "Update docs")
        skills_message = messages[3]["content"]

        self.assertIn("- doc-skill: Update docs.", skills_message)
        self.assertNotIn(str(skill_dir), skills_message)

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
        self.assertEqual(messages[-2]["kind"], "session_context")
        self.assertEqual(messages[-1]["kind"], "user_task")
        self.assertIn("Earlier work: checked README.", messages[-2]["content"])
        self.assertIn("Inspect status", messages[-2]["content"])
        self.assertEqual(messages[-1]["content"], "Continue the work")

    def test_compose_includes_demand_brief_before_current_task(self) -> None:
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

        brief = DemandBrief(
            original_task="Improve docs",
            refined_goal="Update README guided mode docs",
            success_criteria=("README mentions guided mode",),
            scope=("README.md",),
            constraints=("Do not change runtime behavior",),
        )

        messages = ContextComposer().compose(
            snapshot,
            "Execute the demand brief",
            demand_brief=brief,
        )

        self.assertEqual(messages[-2]["kind"], "demand_brief")
        self.assertEqual(messages[-1]["kind"], "user_task")
        self.assertIn("<demand_brief>", messages[-2]["content"])
        self.assertIn("Refined goal:\nUpdate README guided mode docs", messages[-2]["content"])
        self.assertIn("Success criteria:\n- README mentions guided mode", messages[-2]["content"])
        self.assertEqual(messages[-1]["content"], "Execute the demand brief")

    def test_compose_places_demand_brief_after_session_context(self) -> None:
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

        session_context = SessionContext(running_summary="Earlier decision: use guided mode.")
        brief = DemandBrief(
            original_task="Continue",
            refined_goal="Continue guided mode work",
            success_criteria=("Demand brief is injected",),
        )

        messages = ContextComposer().compose(
            snapshot,
            "Execute the demand brief",
            session_context=session_context,
            demand_brief=brief,
        )

        self.assertEqual([message["kind"] for message in messages[-3:]], ["session_context", "demand_brief", "user_task"])


if __name__ == "__main__":
    unittest.main()
