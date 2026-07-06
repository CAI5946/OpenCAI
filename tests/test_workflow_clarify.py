from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from OpenCAI.llm_adapter import Message, ModelOutput
from OpenCAI.tools import ToolSpec
from OpenCAI.workflow.clarify import (
    DEFAULT_MAX_CLARIFY_ROUNDS,
    ClarifyDecision,
    ClarifyPhaseRunner,
    ClarifyQuestion,
    ClarifyResult,
    DeterministicClarifyAgent,
    LLMClarifyAgent,
    clarify_decision_from_json,
)
from OpenCAI.user_prompt import UserPromptOption, UserPromptResult


class StaticClarifyAgent:
    def __init__(self, decisions: list[ClarifyDecision]) -> None:
        self.decisions = decisions
        self.calls: list[list[str]] = []

    def decide(
        self,
        task: str,
        *,
        cwd: Path,
        answers: list[str],
        repo_context_summary: str,
        session_context_summary: str = "",
    ) -> ClarifyDecision:
        self.calls.append(list(answers))
        if self.decisions:
            return self.decisions.pop(0)
        return ClarifyDecision(
            type="complete",
            result=ClarifyResult.from_task(task, assumptions=("No more scripted decisions.",)),
        )


class SequencedAdapter:
    def __init__(self, outputs: list[ModelOutput]) -> None:
        self.outputs = outputs
        self.messages: list[Message] = []
        self.tools: dict[str, ToolSpec] = {}

    def call(self, messages: list[Message], tools: dict[str, ToolSpec]) -> ModelOutput:
        self.messages = list(messages)
        self.tools = tools
        if not self.outputs:
            return {
                "type": "final_answer",
                "answer": json.dumps(
                    {
                        "type": "complete",
                        "result": {
                            "refined_task": "done",
                            "acceptance_criteria": [],
                            "constraints": [],
                            "allowed_changes": [],
                            "out_of_scope": [],
                            "assumptions": ["fallback"],
                            "risks": [],
                            "open_questions": [],
                            "research_notes": [],
                            "sources": [],
                            "confidence": 0.5,
                        },
                    }
                ),
            }
        return self.outputs.pop(0)


class WorkflowClarifyTests(unittest.TestCase):
    def test_default_max_clarify_rounds_is_eight(self) -> None:
        self.assertEqual(DEFAULT_MAX_CLARIFY_ROUNDS, 8)

    def test_deterministic_agent_completes_without_user_question(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path(temp_dir)
            (cwd / "README.md").write_text("# Demo\n", encoding="utf-8")
            runner = ClarifyPhaseRunner(agent=DeterministicClarifyAgent())

            run = runner.run("Read README", cwd=cwd)

        self.assertEqual("complete", run.status)
        self.assertIsNotNone(run.result)
        self.assertEqual("Read README", run.result.original_task)
        self.assertEqual("Read README", run.result.refined_task)
        self.assertIn("README.md", run.repo_context_summary)
        self.assertEqual([], run.questions)

    def test_runner_asks_one_question_at_a_time_and_records_answer(self) -> None:
        result = ClarifyResult.from_task(
            "Fix bug",
            acceptance_criteria=("Bug is fixed.",),
            assumptions=("User confirmed target file.",),
        )
        agent = StaticClarifyAgent(
            [
                ClarifyDecision(
                    type="ask_question",
                    question=ClarifyQuestion(
                        question="Which file should be changed?",
                        reason="The task does not name a target file.",
                        impact_if_unanswered="The implementation may touch the wrong module.",
                        default_assumption="Use the most relevant failing module.",
                    ),
                ),
                ClarifyDecision(type="complete", result=result),
            ]
        )
        runner = ClarifyPhaseRunner(agent=agent, answer_provider=lambda question: "OpenCAI/workflow/core.py")

        run = runner.run("Fix bug", cwd=Path.cwd())

        self.assertEqual("complete", run.status)
        self.assertEqual(["Which file should be changed?"], [question.question for question in run.questions])
        self.assertEqual(["OpenCAI/workflow/core.py"], run.answers)
        self.assertEqual([[], ["OpenCAI/workflow/core.py"]], agent.calls)
        self.assertEqual(result, run.result)

    def test_runner_uses_prompt_option_answer_for_choice_question(self) -> None:
        result = ClarifyResult.from_task(
            "Fix bug",
            assumptions=("User selected the README scope.",),
        )
        agent = StaticClarifyAgent(
            [
                ClarifyDecision(
                    type="ask_question",
                    question=ClarifyQuestion(
                        question="Which scope should be changed?",
                        reason="The task does not name a scope.",
                        impact_if_unanswered="The implementation may touch the wrong files.",
                        options=(
                            UserPromptOption(
                                id="readme",
                                label="README only",
                                description="Limit work to README.md.",
                                value="README.md",
                            ),
                            UserPromptOption(
                                id="docs",
                                label="Docs folder",
                                description="Limit work to docs/.",
                                value="docs/",
                            ),
                        ),
                    ),
                ),
                ClarifyDecision(type="complete", result=result),
            ]
        )
        runner = ClarifyPhaseRunner(agent=agent)

        with patch(
            "OpenCAI.tui.ask_user_prompt",
            return_value=UserPromptResult(
                selected_option_id="readme",
                selected_label="README only",
                value="README.md",
            ),
        ):
            run = runner.run("Fix bug", cwd=Path.cwd())

        self.assertEqual("complete", run.status)
        self.assertEqual(["README.md"], run.answers)
        self.assertEqual([[], ["README.md"]], agent.calls)

    def test_runner_blocks_after_max_question_rounds(self) -> None:
        agent = StaticClarifyAgent(
            [
                ClarifyDecision(
                    type="ask_question",
                    question=ClarifyQuestion(
                        question=f"Question {index}",
                        reason="Need more detail.",
                        impact_if_unanswered="Cannot plan safely.",
                        default_assumption="No safe assumption.",
                    ),
                )
                for index in range(DEFAULT_MAX_CLARIFY_ROUNDS + 1)
            ]
        )
        runner = ClarifyPhaseRunner(agent=agent, answer_provider=lambda question: "answer")

        run = runner.run("Large task", cwd=Path.cwd())

        self.assertEqual("blocked", run.status)
        self.assertEqual(DEFAULT_MAX_CLARIFY_ROUNDS, len(run.questions))
        self.assertIn("max clarify rounds", run.blocked_reason or "")

    def test_llm_agent_can_use_read_only_repo_tools_before_completing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path(temp_dir)
            (cwd / "README.md").write_text("# Demo\n", encoding="utf-8")
            adapter = SequencedAdapter(
                [
                    {"type": "tool_call", "tool_name": "read_file", "arguments": {"path": "README.md"}},
                    {
                        "type": "final_answer",
                        "answer": json.dumps(
                            {
                                "type": "complete",
                                "result": {
                                    "refined_task": "Read README and summarize constraints.",
                                    "acceptance_criteria": ["Summary mentions README."],
                                    "constraints": ["Do not edit files."],
                                    "allowed_changes": [],
                                    "out_of_scope": ["Code changes"],
                                    "assumptions": ["README is the relevant source."],
                                    "risks": [],
                                    "open_questions": [],
                                    "research_notes": ["README confirms this is a demo repository."],
                                    "sources": ["README.md"],
                                    "confidence": 0.9,
                                },
                            }
                        ),
                    },
                ]
            )
            agent = LLMClarifyAgent(adapter=adapter, max_model_turns=3)

            decision = agent.decide(
                "Read README",
                cwd=cwd,
                answers=[],
                repo_context_summary="repo has README.md",
            )

        self.assertEqual("complete", decision.type)
        self.assertIsNotNone(decision.result)
        self.assertEqual("Read README and summarize constraints.", decision.result.refined_task)
        self.assertEqual(
            {
                "read_file",
                "list_files",
                "glob_files",
                "search_files",
                "web_search",
                "web_fetch",
                "web_extract",
            },
            set(adapter.tools.keys()),
        )
        self.assertTrue(all(spec.read_only for spec in adapter.tools.values()))
        self.assertEqual(("README.md",), decision.result.sources)
        self.assertEqual(("README confirms this is a demo repository.",), decision.result.research_notes)
        self.assertIn("Tool read_file succeeded", adapter.messages[-1]["content"])

    def test_llm_agent_receives_session_context_summary(self) -> None:
        adapter = SequencedAdapter(
            [
                {
                    "type": "final_answer",
                    "answer": json.dumps(
                        {
                            "type": "complete",
                            "result": {
                                "refined_task": "Continue guided mode design.",
                                "acceptance_criteria": [],
                                "constraints": [],
                                "allowed_changes": [],
                                "out_of_scope": [],
                                "assumptions": ["Use prior session context."],
                                "risks": [],
                                "open_questions": [],
                                "research_notes": [],
                                "sources": [],
                                "confidence": 0.7,
                            },
                        }
                    ),
                },
            ]
        )
        agent = LLMClarifyAgent(adapter=adapter, max_model_turns=1)

        decision = agent.decide(
            "Continue",
            cwd=Path.cwd(),
            answers=[],
            repo_context_summary="repo context",
            session_context_summary="<session_context>Earlier decision: use guided.</session_context>",
        )

        self.assertEqual("complete", decision.type)
        self.assertIn("Session context summary:", adapter.messages[1]["content"])
        self.assertIn("Earlier decision: use guided.", adapter.messages[1]["content"])

    def test_llm_agent_observes_structured_repo_tool_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path(temp_dir)
            (cwd / "README.md").write_text("# Demo\n", encoding="utf-8")
            adapter = SequencedAdapter(
                [
                    {"type": "tool_call", "tool_name": "list_files", "arguments": {"path": "."}},
                    {
                        "type": "final_answer",
                        "answer": json.dumps(
                            {
                                "type": "complete",
                                "result": {
                                    "refined_task": "Use repo file listing before planning.",
                                    "acceptance_criteria": [],
                                    "constraints": [],
                                    "allowed_changes": [],
                                    "out_of_scope": [],
                                    "assumptions": ["README.md is visible in the repo listing."],
                                    "risks": [],
                                    "open_questions": [],
                                    "research_notes": ["list_files returned the repository root entries."],
                                    "sources": ["list_files:."],
                                    "confidence": 0.8,
                                },
                            }
                        ),
                    },
                ]
            )
            agent = LLMClarifyAgent(adapter=adapter, max_model_turns=3)

            decision = agent.decide(
                "Inspect repo",
                cwd=cwd,
                answers=[],
                repo_context_summary="repo has README.md",
            )

        self.assertEqual("complete", decision.type)
        self.assertIn("Tool list_files succeeded", adapter.messages[-1]["content"])
        self.assertIn("README.md", adapter.messages[-1]["content"])
        self.assertIn('"entries"', adapter.messages[-1]["content"])

    def test_llm_agent_can_use_read_only_web_tools_before_completing(self) -> None:
        adapter = SequencedAdapter(
            [
                {
                    "type": "tool_call",
                    "tool_name": "web_extract",
                    "arguments": {"html": "<html><title>Codex docs</title><p>Docs content</p></html>"},
                },
                {
                    "type": "final_answer",
                    "answer": json.dumps(
                        {
                            "type": "complete",
                            "result": {
                                "refined_task": "Check current Codex docs before planning.",
                                "acceptance_criteria": ["Planner accounts for current docs."],
                                "constraints": ["Use primary sources."],
                                "allowed_changes": [],
                                "out_of_scope": [],
                                "assumptions": [],
                                "risks": ["External docs may change."],
                                "open_questions": [],
                                "research_notes": ["External docs are relevant to clarify the task."],
                                "sources": ["web_search: OpenAI Codex docs"],
                                "confidence": 0.8,
                            },
                        }
                    ),
                },
            ]
        )
        agent = LLMClarifyAgent(adapter=adapter, max_model_turns=3)

        decision = agent.decide(
            "Compare OpenCAI workflow with Codex",
            cwd=Path.cwd(),
            answers=[],
            repo_context_summary="repo does not contain current Codex docs",
        )

        self.assertEqual("complete", decision.type)
        self.assertIsNotNone(decision.result)
        self.assertEqual(("web_search: OpenAI Codex docs",), decision.result.sources)
        self.assertIn("Tool web_extract", adapter.messages[-1]["content"])

    def test_llm_agent_retries_when_final_answer_contains_extra_json(self) -> None:
        invalid_answer = (
            json.dumps(
                {
                    "type": "ask_question",
                    "question": {
                        "question": "Which target file?",
                        "reason": "The task is ambiguous.",
                        "impact_if_unanswered": "The wrong file may be changed.",
                    },
                }
            )
            + json.dumps({"type": "blocked", "reason": "duplicate decision"})
        )
        adapter = SequencedAdapter(
            [
                {"type": "final_answer", "answer": invalid_answer},
                {
                    "type": "final_answer",
                    "answer": json.dumps(
                        {
                            "type": "complete",
                            "result": {
                                "refined_task": "Fix the clarify JSON retry path.",
                                "acceptance_criteria": ["Invalid clarify JSON is retried."],
                                "constraints": [],
                                "allowed_changes": ["OpenCAI/workflow/clarify.py"],
                                "out_of_scope": [],
                                "assumptions": [],
                                "risks": [],
                                "open_questions": [],
                                "research_notes": [],
                                "sources": [],
                                "confidence": 0.7,
                            },
                        }
                    ),
                },
            ]
        )
        agent = LLMClarifyAgent(adapter=adapter, max_model_turns=3)

        decision = agent.decide(
            "Fix clarify JSON handling",
            cwd=Path.cwd(),
            answers=[],
            repo_context_summary="repo has workflow clarify code",
        )

        self.assertEqual("complete", decision.type)
        self.assertIsNotNone(decision.result)
        self.assertEqual("Fix the clarify JSON retry path.", decision.result.refined_task)
        self.assertIn("Previous clarify answer was invalid JSON", adapter.messages[-1]["content"])

    def test_clarify_parser_accepts_question_options(self) -> None:
        decision = clarify_decision_from_json(
            json.dumps(
                {
                    "type": "ask_question",
                    "question": {
                        "question": "Which target?",
                        "reason": "The target is ambiguous.",
                        "impact_if_unanswered": "The wrong file may be changed.",
                        "options": [
                            {
                                "id": "readme",
                                "label": "README",
                                "description": "Only README.md.",
                                "value": "README.md",
                            },
                            {
                                "id": "status",
                                "label": "Status",
                                "description": "Only docs/status.md.",
                                "value": "docs/status.md",
                            },
                        ],
                    },
                }
            ),
            original_task="Fix docs",
        )

        self.assertEqual("ask_question", decision.type)
        self.assertIsNotNone(decision.question)
        assert decision.question is not None
        self.assertEqual(2, len(decision.question.options))
        self.assertEqual("readme", decision.question.options[0].id)
        self.assertEqual("README.md", decision.question.options[0].value)

    def test_clarify_parser_blocks_on_missing_required_result_fields(self) -> None:
        decision = clarify_decision_from_json(
            json.dumps({"type": "complete", "result": {"confidence": 0.8}}),
            original_task="Fix bug",
        )

        self.assertEqual("blocked", decision.type)
        self.assertIn("refined_task", decision.reason or "")


if __name__ == "__main__":
    unittest.main()
