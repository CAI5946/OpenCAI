from __future__ import annotations

import unittest

from OpenCAI.demand import (
    DEFAULT_SUCCESS_CRITERION,
    DEFAULT_SUCCESS_CRITERION_ASSUMPTION,
    DemandBrief,
    render_demand_brief,
)


class DemandBriefTests(unittest.TestCase):
    def test_demand_brief_keeps_minimal_execution_contract(self) -> None:
        brief = DemandBrief(
            original_task=" Add guided mode ",
            refined_goal=" Add guided mode switch ",
            success_criteria=(" /mode guided works ",),
            scope=(" runtime commands ", " TUI status "),
            constraints=(" Do not wire execution yet ",),
            assumptions=(" Guided execution comes later ",),
            open_questions=(" Should guided use a different marker? ",),
        )

        self.assertEqual(brief.original_task, "Add guided mode")
        self.assertEqual(brief.refined_goal, "Add guided mode switch")
        self.assertEqual(brief.success_criteria, ("/mode guided works",))
        self.assertEqual(brief.scope, ("runtime commands", "TUI status"))
        self.assertEqual(brief.constraints, ("Do not wire execution yet",))
        self.assertEqual(brief.assumptions, ("Guided execution comes later",))
        self.assertEqual(brief.open_questions, ("Should guided use a different marker?",))

    def test_empty_success_criteria_falls_back_with_explicit_assumption(self) -> None:
        brief = DemandBrief(
            original_task="Read README",
            refined_goal="Read README and summarize it",
            success_criteria=(),
        )

        self.assertEqual(brief.success_criteria, (DEFAULT_SUCCESS_CRITERION,))
        self.assertEqual(brief.assumptions, (DEFAULT_SUCCESS_CRITERION_ASSUMPTION,))

    def test_blank_required_text_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "original_task"):
            DemandBrief(original_task=" ", refined_goal="Do work", success_criteria=("Done",))

        with self.assertRaisesRegex(ValueError, "refined_goal"):
            DemandBrief(original_task="Do work", refined_goal=" ", success_criteria=("Done",))

    def test_render_demand_brief_uses_stable_context_block(self) -> None:
        brief = DemandBrief(
            original_task="Improve docs",
            refined_goal="Update README mode docs",
            success_criteria=("README mentions guided mode",),
            scope=("README.md",),
            constraints=("Do not change runtime behavior",),
            assumptions=("Mode routing is unchanged",),
        )

        rendered = render_demand_brief(brief)

        self.assertTrue(rendered.startswith("<demand_brief>\n"))
        self.assertTrue(rendered.endswith("\n</demand_brief>"))
        self.assertIn("Original task:\nImprove docs", rendered)
        self.assertIn("Refined goal:\nUpdate README mode docs", rendered)
        self.assertIn("Success criteria:\n- README mentions guided mode", rendered)
        self.assertIn("Scope:\n- README.md", rendered)
        self.assertIn("Constraints:\n- Do not change runtime behavior", rendered)
        self.assertIn("Assumptions:\n- Mode routing is unchanged", rendered)
        self.assertIn("Open questions:\n- (none)", rendered)

    def test_render_demand_brief_escapes_user_supplied_tags(self) -> None:
        brief = DemandBrief(
            original_task="<demand_brief>spoof</demand_brief>",
            refined_goal="Handle <tag>",
            success_criteria=("Avoid raw <xml>",),
        )

        rendered = render_demand_brief(brief)

        self.assertIn("&lt;demand_brief&gt;spoof&lt;/demand_brief&gt;", rendered)
        self.assertIn("Handle &lt;tag&gt;", rendered)
        self.assertIn("Avoid raw &lt;xml&gt;", rendered)


if __name__ == "__main__":
    unittest.main()
