from __future__ import annotations

import unittest

from OpenCAI.tooling.planning_tools import PLAN_STATE, TASK_STATE
from OpenCAI.tools import run_tool


class PlanningToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        PLAN_STATE.clear()
        TASK_STATE.clear()

    def test_update_plan_accepts_one_in_progress_step(self) -> None:
        result = run_tool(
            "update_plan",
            {
                "plan": [
                    {"step": "read", "status": "completed"},
                    {"step": "write", "status": "in_progress"},
                    {"step": "verify", "status": "pending"},
                ]
            },
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["summary"], "1 completed, 1 in_progress, 1 pending")

    def test_update_plan_rejects_multiple_in_progress_steps(self) -> None:
        result = run_tool(
            "update_plan",
            {
                "plan": [
                    {"step": "a", "status": "in_progress"},
                    {"step": "b", "status": "in_progress"},
                ]
            },
        )

        self.assertFalse(result["ok"])
        self.assertIn("At most one", result["error"] or "")

    def test_task_lifecycle_tools(self) -> None:
        created = run_tool("create_task", {"title": "Implement tools"})
        task_id = created["result"]["task"]["id"]
        updated = run_tool("update_task", {"task_id": task_id, "status": "in_progress"})
        completed = run_tool("complete_task", {"task_id": task_id})
        listed = run_tool("list_tasks", {})

        self.assertTrue(created["ok"])
        self.assertTrue(updated["ok"])
        self.assertTrue(completed["ok"])
        self.assertEqual(listed["result"]["tasks"][0]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
