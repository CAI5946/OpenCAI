from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

from OpenCAI.demand import DEFAULT_SUCCESS_CRITERION_ASSUMPTION, DemandBrief
from OpenCAI.events import Event, final_answer, user_task
from OpenCAI.guided import demand_brief_from_clarify_result, render_guided_demand_brief, run_guided_task
from OpenCAI.llm_adapter import FakeLLMAdapter
from OpenCAI.safety import PermissionProfile, SafetyPolicy
from OpenCAI.session_context import SessionContext
from OpenCAI.user_prompt import UserPromptResult
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
            events = run_guided_task(
                session,
                "Improve docs",
                execute_task=execute_task,
                review_provider=lambda _brief: "execute",
            )

        self.assertEqual(events[-1]["type"], "final_answer")
        self.assertEqual(received[0][0], "Update README guided docs")
        self.assertIn("Clarify status: complete", output.getvalue())
        self.assertIn("Guided demand brief", output.getvalue())

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
                review_provider=lambda _brief: "execute",
            )

        self.assertIn(
            "Earlier decision: use guided.",
            clarify.call_args.kwargs["session_context_summary"],
        )

    def test_run_guided_task_defaults_to_execute_when_not_tty(self) -> None:
        session = DummySession(cwd=Path.cwd(), adapter=FakeLLMAdapter())
        clarify_run = ClarifyRun(
            original_task="Read README",
            status="complete",
            repo_context_summary="repo",
            result=ClarifyResult.from_task("Read README"),
        )

        with (
            patch("OpenCAI.guided.run_clarify_for_session", return_value=clarify_run),
            patch("OpenCAI.guided.sys.stdin.isatty", return_value=False),
            redirect_stdout(io.StringIO()),
        ):
            events = run_guided_task(
                session,
                "Read README",
                execute_task=lambda task, _brief: [user_task(1, task), final_answer(2, "done")],
            )

        self.assertEqual(events[-1]["type"], "final_answer")

    def test_run_guided_task_stops_when_user_rejects_review(self) -> None:
        session = DummySession(cwd=Path.cwd(), adapter=FakeLLMAdapter())
        clarify_run = ClarifyRun(
            original_task="Improve docs",
            status="complete",
            repo_context_summary="repo",
            result=ClarifyResult.from_task("Improve docs"),
        )

        with (
            patch("OpenCAI.guided.run_clarify_for_session", return_value=clarify_run),
            redirect_stdout(io.StringIO()) as output,
        ):
            events = run_guided_task(
                session,
                "Improve docs",
                execute_task=lambda _task, _brief: [final_answer(1, "should not run")],
                review_provider=lambda _brief: "stop",
            )

        self.assertEqual(events, [])
        self.assertIn("Guided task stopped before execution.", output.getvalue())

    def test_run_guided_task_treats_review_text_as_revision_feedback(self) -> None:
        session = DummySession(cwd=Path.cwd(), adapter=FakeLLMAdapter())
        first_run = ClarifyRun(
            original_task="Improve docs",
            status="complete",
            repo_context_summary="repo",
            result=ClarifyResult(
                original_task="Improve docs",
                refined_task="Update README and status docs",
                acceptance_criteria=("README and status mention guided mode",),
                allowed_changes=("README.md", "docs/status.md"),
            ),
        )
        second_run = ClarifyRun(
            original_task="Improve docs",
            status="complete",
            repo_context_summary="repo",
            result=ClarifyResult(
                original_task="Improve docs",
                refined_task="Update only README guided docs",
                acceptance_criteria=("README mentions guided mode",),
                allowed_changes=("README.md",),
                out_of_scope=("docs/status.md",),
            ),
        )
        review_inputs = iter(["Only update README.", "execute"])
        received: list[tuple[str, DemandBrief]] = []

        def execute_task(task: str, demand_brief: DemandBrief) -> list[Event]:
            received.append((task, demand_brief))
            return [user_task(1, task), final_answer(2, "done")]

        with (
            patch("OpenCAI.guided.run_clarify_for_session", side_effect=[first_run, second_run]) as clarify,
            redirect_stdout(io.StringIO()),
        ):
            events = run_guided_task(
                session,
                "Improve docs",
                execute_task=execute_task,
                review_provider=lambda _brief: next(review_inputs),
            )

        self.assertEqual(events[-1]["type"], "final_answer")
        self.assertEqual(received[0][0], "Update only README guided docs")
        second_context = clarify.call_args_list[1].kwargs["session_context_summary"]
        self.assertIn("Previous guided DemandBrief rejected by user", second_context)
        self.assertIn("Only update README.", second_context)
        self.assertIn("Update README and status docs", second_context)

    def test_run_guided_task_uses_popup_review_provider_by_default(self) -> None:
        session = DummySession(cwd=Path.cwd(), adapter=FakeLLMAdapter())
        first_run = ClarifyRun(
            original_task="Improve docs",
            status="complete",
            repo_context_summary="repo",
            result=ClarifyResult(
                original_task="Improve docs",
                refined_task="Update README and status docs",
                acceptance_criteria=("README and status mention guided mode",),
                allowed_changes=("README.md", "docs/status.md"),
            ),
        )
        second_run = ClarifyRun(
            original_task="Improve docs",
            status="complete",
            repo_context_summary="repo",
            result=ClarifyResult(
                original_task="Improve docs",
                refined_task="Update only README guided docs",
                acceptance_criteria=("README mentions guided mode",),
                allowed_changes=("README.md",),
            ),
        )
        prompt_results = iter(
            [
                UserPromptResult(
                    selected_option_id="revise",
                    selected_label="Revise demand",
                    value="revise",
                    custom_answer="Only update README.",
                ),
                UserPromptResult(
                    selected_option_id="execute",
                    selected_label="Execute",
                    value="execute",
                ),
            ]
        )
        received: list[str] = []

        with (
            patch("OpenCAI.guided.sys.stdin.isatty", return_value=True),
            patch("OpenCAI.tui.ask_user_prompt", side_effect=lambda _request: next(prompt_results)),
            patch("OpenCAI.guided.run_clarify_for_session", side_effect=[first_run, second_run]) as clarify,
            redirect_stdout(io.StringIO()),
        ):
            events = run_guided_task(
                session,
                "Improve docs",
                execute_task=lambda task, _brief: received.append(task) or [final_answer(1, "done")],
            )

        self.assertEqual(events[-1]["type"], "final_answer")
        self.assertEqual(["Update only README guided docs"], received)
        self.assertIn("Only update README.", clarify.call_args_list[1].kwargs["session_context_summary"])

    def test_run_guided_task_stops_after_max_review_rounds(self) -> None:
        session = DummySession(cwd=Path.cwd(), adapter=FakeLLMAdapter())
        clarify_run = ClarifyRun(
            original_task="Improve docs",
            status="complete",
            repo_context_summary="repo",
            result=ClarifyResult.from_task("Improve docs"),
        )

        with (
            patch("OpenCAI.guided.run_clarify_for_session", return_value=clarify_run),
            redirect_stdout(io.StringIO()) as output,
        ):
            events = run_guided_task(
                session,
                "Improve docs",
                execute_task=lambda _task, _brief: [final_answer(1, "should not run")],
                review_provider=lambda _brief: "revise again",
                max_review_rounds=1,
            )

        self.assertEqual(events, [])
        self.assertIn("maximum review rounds reached", output.getvalue())

    def test_render_guided_demand_brief_is_human_readable(self) -> None:
        brief = DemandBrief(
            original_task="Improve docs",
            refined_goal="Update README guided docs",
            success_criteria=("README mentions guided mode",),
            scope=("README.md",),
            constraints=("Do not change runtime behavior",),
            assumptions=("Mode switch exists",),
        )

        rendered = render_guided_demand_brief(brief)

        self.assertIn("• Guided demand brief:", rendered)
        self.assertIn("Refined goal:\nUpdate README guided docs", rendered)
        self.assertIn("Success criteria:\n- README mentions guided mode", rendered)
        self.assertIn("Open questions:\n- (none)", rendered)

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
