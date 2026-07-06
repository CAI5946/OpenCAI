from __future__ import annotations

import json
import unittest

from OpenCAI.llm_adapter import Message, ModelOutput
from OpenCAI.workflow import WorkflowPlan, WorkflowSpec
from OpenCAI.workflow.planner import (
    LLMWorkflowPlanningAgent,
    PlanningError,
    ScriptOpDraft,
    WorkflowPlanDraft,
    WorkflowPlanningAgent,
    compile_workflow,
    render_workflow_plan_draft,
)


class StaticPlanningAdapter:
    def __init__(self, output: ModelOutput) -> None:
        self.output = output
        self.messages: list[Message] = []
        self.tools: dict[str, object] = {}

    def call(self, messages: list[Message], tools: dict[str, object]) -> ModelOutput:
        self.messages = messages
        self.tools = tools
        return self.output


class WorkflowPlannerTests(unittest.TestCase):
    def test_llm_planning_agent_parses_model_json_into_workflow_plan_draft(self) -> None:
        adapter = StaticPlanningAdapter(
            {
                "type": "final_answer",
                "answer": json.dumps(
                    {
                        "selected_template": "inspect_handoff",
                        "rationale": "The task needs inspection before handoff.",
                        "phases": [
                            {"id": "inspect", "role": "inspector"},
                            {"id": "handoff", "role": "handoff"},
                        ],
                        "tasks": [
                            {
                                "id": "inspect_context",
                                "phase_id": "inspect",
                                "role": "inspector",
                                "instruction": "Inspect context.",
                            },
                            {
                                "id": "handoff_summary",
                                "phase_id": "handoff",
                                "role": "handoff",
                                "instruction": "Summarize.",
                                "depends_on": ["inspect_context"],
                            },
                        ],
                        "script_ops": [
                            {"type": "run_phase", "phase_id": "inspect"},
                            {"type": "run_phase", "phase_id": "handoff"},
                            {"type": "handoff", "phase_id": "handoff"},
                        ],
                        "assumptions": ["The repository can be inspected safely."],
                        "risks": ["The planner draft still needs compiler validation."],
                    }
                ),
            }
        )
        agent = LLMWorkflowPlanningAgent(adapter=adapter)

        draft = agent.plan("Read README")

        self.assertEqual("inspect_handoff", draft.selected_template)
        self.assertEqual(["inspect", "handoff"], [phase.id for phase in draft.phases])
        self.assertEqual(("inspect_context",), draft.tasks[1].depends_on)
        self.assertEqual(("The repository can be inspected safely.",), draft.assumptions)
        self.assertEqual({}, adapter.tools)
        self.assertEqual("system", adapter.messages[0]["role"])
        self.assertIn("Return only JSON", adapter.messages[0]["content"])
        self.assertIn("Read README", adapter.messages[1]["content"])

    def test_llm_planning_agent_rejects_non_json_model_answer(self) -> None:
        agent = LLMWorkflowPlanningAgent(
            adapter=StaticPlanningAdapter({"type": "final_answer", "answer": "not json"})
        )

        with self.assertRaises(PlanningError):
            agent.plan("Read README")

    def test_render_workflow_plan_draft_supports_isolated_planner_testing(self) -> None:
        draft = WorkflowPlanningAgent().plan("Read README")

        output = render_workflow_plan_draft(draft)

        self.assertIn("Workflow planner draft: inspect_handoff", output)
        self.assertIn("run_phase inspect", output)
        self.assertIn("assumptions:", output)
        self.assertIn("risks:", output)

    def test_planning_agent_returns_structured_workflow_plan_draft(self) -> None:
        agent = WorkflowPlanningAgent()

        draft = agent.plan("Read README")

        self.assertIsInstance(draft, WorkflowPlanDraft)
        self.assertEqual("inspect_handoff", draft.selected_template)
        self.assertIn("deterministic", draft.rationale)
        self.assertEqual(["inspect", "handoff"], [phase.id for phase in draft.phases])
        self.assertEqual(
            ["inspect_context", "inspect_constraints", "handoff_summary"],
            [task.id for task in draft.tasks],
        )
        self.assertEqual(
            [("run_phase", "inspect"), ("run_phase", "handoff"), ("handoff", "handoff")],
            [(op.type, op.phase_id) for op in draft.script_ops],
        )
        self.assertTrue(draft.assumptions)
        self.assertTrue(draft.risks)

    def test_compile_workflow_returns_builtin_inspect_handoff_spec(self) -> None:
        plan = compile_workflow("Read README")
        spec = plan.spec

        self.assertIsInstance(plan, WorkflowPlan)
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
        self.assertEqual(
            [("run_phase", "inspect"), ("run_phase", "handoff"), ("handoff", "handoff")],
            [(op.type, op.phase_id) for op in plan.script.ops],
        )

    def test_compile_workflow_uses_planning_agent_draft(self) -> None:
        class StubPlanningAgent:
            def __init__(self) -> None:
                self.tasks: list[str] = []

            def plan(self, task: str) -> WorkflowPlanDraft:
                self.tasks.append(task)
                return WorkflowPlanDraft(
                    selected_template="inspect_handoff",
                    rationale="stub planner selected the built-in template",
                    phases=(),
                    tasks=(),
                    script_ops=(ScriptOpDraft(type="run_phase", phase_id="inspect"),),
                    assumptions=("stub",),
                    risks=("stub",),
                )

        planning_agent = StubPlanningAgent()

        plan = compile_workflow("Read README", planning_agent=planning_agent)

        self.assertIsInstance(plan, WorkflowPlan)
        self.assertEqual(["Read README"], planning_agent.tasks)
        self.assertEqual("inspect_handoff", plan.spec.name)


if __name__ == "__main__":
    unittest.main()
