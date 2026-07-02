from pathlib import Path
import tempfile
import unittest

from OpenCAI.tools import TOOLS, run_tool


class SkillToolsTest(unittest.TestCase):
    def test_list_skills_discovers_skill_directories_under_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            skill_root = cwd / "skills"
            skill_dir = skill_root / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo-skill\ndescription: Demo skill.\n---\n\n# Demo\n",
                encoding="utf-8",
            )

            result = run_tool("list_skills", {"root": "skills"}, cwd)

        self.assertTrue(result["ok"])
        self.assertEqual(
            [
                {
                    "name": "demo-skill",
                    "path": str(Path("skills") / "demo-skill"),
                    "description": "Demo skill.",
                }
            ],
            result["result"]["skills"],
        )

    def test_read_skill_returns_entrypoint_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            skill_dir = cwd / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Demo\n\nUse this skill.\n", encoding="utf-8")

            result = run_tool("read_skill", {"name": "demo-skill", "root": "skills"}, cwd)

        self.assertTrue(result["ok"])
        self.assertEqual("demo-skill", result["result"]["name"])
        self.assertIn("Use this skill.", result["result"]["content"])

    def test_read_skill_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "skills").mkdir()

            result = run_tool("read_skill", {"name": "..\\secret", "root": "skills"}, cwd)

        self.assertFalse(result["ok"])
        self.assertIn("Invalid skill name", result["error"] or "")

    def test_invoke_skill_loads_project_skill_as_meta_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            skill_dir = cwd / ".opencai" / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo-skill\ndescription: Demo skill.\n---\n\n# Demo\n\nUse this skill.",
                encoding="utf-8",
            )

            result = run_tool("invoke_skill", {"skill": "demo-skill", "args": "now"}, cwd)

        self.assertTrue(result["ok"])
        self.assertEqual("demo-skill", result["result"]["skill"])
        self.assertEqual("now", result["result"]["args"])
        self.assertIn("Use this skill.", result["result"]["content"])
        self.assertEqual(
            result["result"]["messages"][0]["kind"],
            "invoked_skill",
        )
        self.assertIn("<invoked_skill", result["result"]["messages"][0]["content"])

    def test_invoke_skill_finds_project_skill_from_repo_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git").mkdir()
            cwd = repo / "src"
            cwd.mkdir()
            skill_dir = repo / ".opencai" / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Demo\n\nUse this skill.", encoding="utf-8")

            result = run_tool("invoke_skill", {"skill": "demo-skill"}, cwd)

        self.assertTrue(result["ok"])
        self.assertEqual("demo-skill", result["result"]["skill"])

    def test_invoke_skill_rejects_unknown_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = run_tool("invoke_skill", {"skill": "missing"}, cwd)

        self.assertFalse(result["ok"])
        self.assertIn("Skill not found", result["error"] or "")

    def test_skill_tools_are_registered_as_read_only(self) -> None:
        self.assertTrue(TOOLS["list_skills"].read_only)
        self.assertTrue(TOOLS["read_skill"].read_only)
        self.assertTrue(TOOLS["invoke_skill"].read_only)


if __name__ == "__main__":
    unittest.main()
