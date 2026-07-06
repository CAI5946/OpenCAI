from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

from OpenCAI.demand import DEFAULT_SUCCESS_CRITERION_ASSUMPTION, DemandBrief
from OpenCAI.events import Event, final_answer, user_task
from OpenCAI.guided import demand_brief_from_clarify_result, run_guided_task
from OpenCAI.llm_adapter import FakeLLMAdapter
from OpenCAI.safety import PermissionProfile, SafetyPolicy
from OpenCAI.session_context import SessionContext
from OpenCAI.workflow.clarify import ClarifyResult, ClarifyRun


@dataclass
class DummySession:
    cwd: Path
    adapter: FakeLLMAdapter
    max_steps: int = 8
    permission_profile: PermissionProfile = PermissionProfile.APPROVE_SAFE
    session_context: SessionContext = field(default_factory=SessionContext)

    def build_policy(self) -> SafetyPolicy:
        return SafetyPolicy(profile=self.permission_profile)


class GuidedModeTests(unittest.TestCase):
    def test_demand_brief_from_clarify_result_maps_v1_contract(self) -> None:
        result = ClarifyResult(
            original_task="Improve docs",
            refined_task="Update README guided docs",
            acceptance_criteria=("README mentions guided mode",),
            constraints=("Do not change runtime behavior",),
            allowed_changes=("README.md",),
            out_of_scope=("Guided runner",),
            assumptions=("Mode switch already exists",),
            open_questions=("Should docs include screenshots?",),
            risks=("Docs may drift",),
            research_notes=("README checked",),
            sources=("README.md",),
            confidence=0.9,
        )

        brief = demand_brief_from_clarify_result(result)

        self.assertEqual(brief.original_task, "Improve docs")
        self.assertEqual(brief.refined_goal, "Update README guided docs")
        self.assertEqual(brief.success_criteria, ("README mentions guided mode",))
        self.assertEqual(brief.scope, ("README.md",))
        self.assertEqual(
            brief.constraints,
            ("Do not change runtime behavior", "Out of scope: Guided runner"),
        )
        self.assertEqual(brief.assumptions, ("Mode switch already exists",))
        self.assertEqual(brief.open_questions, ("Should docs include screenshots?",))

    def test_demand_brief_falls_back_when_clarify_has_no_acceptance_criteria(self) -> None:
        result = ClarifyResult.from_task("Read README")

        brief = demand_brief_from_clarify_result(result)

        self.assertEqual(brief.refined_goal, "Read README")
        self.assertEqual(brief.assumptions, (DEFAULT_SUCCESS_CRITERION_ASSUMPTION,))

    def test_run_guided_task_executes_refined_goal_after_clarify_complete(self) -> None:
        session = DummySession(
            cwd=Path.cwd(),
            adapter=FakeLLMAdapter(),
            session_context=SessionContext(running_summary="Earlier decision: use guided."),
        )
        clarify_run = ClarifyRun(
            original_task="Improve docs",
            status="complete",
            repo_context_summary="repo",
            result=ClarifyResult(
                original_task="Improve docs",
                refined_task="Update README guided docs",
                acceptance_criteria=("README mentions guided mode",),
            ),
        )
        received: list[tuple[str, DemandBrief]] = []

        def execute_task(task: str, demand_brief: DemandBrief) -> list[Event]:
            received.append((task, demand_brief))
            return [user_task(1, task), final_answer(2, "done")]

        with (
            patch("OpenCAI.guided.run_clarify_for_session", return_value=clarify_run),
            redirect_stdout(io.StringIO()) as output,
        ):
            events = run_guided_task(session, "Improve docs", execute_task=execute_task)

        self.assertEqual(events[-1]["type"], "final_answer")
        self.assertEqual(received[0][0], "Update README guided docs")
        self.assertIn("Clarify status: complete", output.getvalue())

    def test_run_guided_task_passes_session_context_to_clarify(self) -> None:
        session = DummySession(
            cwd=Path.cwd(),
            adapter=FakeLLMAdapter(),
            session_context=SessionContext(running_summary="Earlier decision: use guided."),
        )
        clarify_run = ClarifyRun(
            original_task="Continue",
            status="complete",
            repo_context_summary="repo",
            result=ClarifyResult.from_task("Continue"),
        )

        with (
            patch("OpenCAI.guided.run_clarify_for_session", return_value=clarify_run) as clarify,
            redirect_stdout(io.StringIO()),
        ):
            run_guided_task(
                session,
                "Continue",
                execute_task=lambda _task, _brief: [final_answer(1, "done")],
            )

        self.assertIn(
            "Earlier decision: use guided.",
            clarify.call_args.kwargs["session_context_summary"],
        )

    def test_run_guided_task_stops_when_clarify_blocks(self) -> None:
        session = DummySession(cwd=Path.cwd(), adapter=FakeLLMAdapter())
        clarify_run = ClarifyRun(
            original_task="Improve docs",
            status="blocked",
            repo_context_summary="repo",
            blocked_reason="Need human decision.",
        )

        with (
            patch("OpenCAI.guided.run_clarify_for_session", return_value=clarify_run),
            redirect_stdout(io.StringIO()) as output,
        ):
            events = run_guided_task(
                session,
                "Improve docs",
                execute_task=lambda _task, _brief: [final_answer(1, "should not run")],
            )

        self.assertEqual(events, [])
        self.assertIn("Clarify status: blocked", output.getvalue())
        self.assertIn("Need human decision.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
