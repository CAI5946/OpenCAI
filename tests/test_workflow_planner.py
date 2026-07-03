from __future__ import annotations

import unittest

from OpenCAI.workflow import WorkflowSpec
from OpenCAI.workflow_planner import compile_workflow


class WorkflowPlannerTests(unittest.TestCase):
    def test_compile_workflow_returns_builtin_inspect_handoff_spec(self) -> None:
        spec = compile_workflow("Read README")

        self.assertIsInstance(spec, WorkflowSpec)
        self.assertEqual(spec.name, "inspect_handoff")
        self.assertEqual(spec.final_phase_id, "handoff")
        self.assertEqual(["inspect", "handoff"], [phase.id for phase in spec.phases])
        self.assertEqual(
            ["inspect_context", "inspect_constraints", "handoff_summary"],
            [task.id for task in spec.tasks],
        )
        self.assertEqual(["inspect", "inspect", "handoff"], [task.phase_id for task in spec.tasks])
        self.assertEqual(("inspect_context", "inspect_constraints"), spec.tasks[-1].depends_on)


if __name__ == "__main__":
    unittest.main()
