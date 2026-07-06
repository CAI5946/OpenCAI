"""Runtime-owned clarify phase for workflow mode."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Callable, Literal, Protocol

from OpenCAI.llm_adapter import LLMAdapter, LLMAdapterError, Message
from OpenCAI.output_format import format_output_title
from OpenCAI.safety import PermissionProfile, SafetyPolicy
from OpenCAI.tools import ToolResult, ToolSpec, run_tool
from OpenCAI.tooling.file_tools import FILE_TOOLS
from OpenCAI.tooling.search_tools import SEARCH_TOOLS
from OpenCAI.tooling.web_tools import WEB_TOOLS


DEFAULT_MAX_CLARIFY_ROUNDS = 8
DEFAULT_MAX_CLARIFY_MODEL_TURNS = 8

ClarifyDecisionType = Literal["ask_question", "complete", "blocked"]
ClarifyStatus = Literal["complete", "blocked"]
AnswerProvider = Callable[["ClarifyQuestion"], str]


@dataclass(frozen=True)
class ClarifyQuestion:
    question: str
    reason: str
    impact_if_unanswered: str
    default_assumption: str = ""


@dataclass(frozen=True)
class ClarifyResult:
    original_task: str
    refined_task: str
    acceptance_criteria: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    allowed_changes: tuple[str, ...] = ()
    out_of_scope: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    research_notes: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    confidence: float = 0.5

    @classmethod
    def from_task(
        cls,
        task: str,
        *,
        acceptance_criteria: tuple[str, ...] = (),
        constraints: tuple[str, ...] = (),
        allowed_changes: tuple[str, ...] = (),
        out_of_scope: tuple[str, ...] = (),
        assumptions: tuple[str, ...] = (),
        risks: tuple[str, ...] = (),
        open_questions: tuple[str, ...] = (),
        research_notes: tuple[str, ...] = (),
        sources: tuple[str, ...] = (),
        confidence: float = 0.5,
    ) -> "ClarifyResult":
        return cls(
            original_task=task,
            refined_task=task,
            acceptance_criteria=acceptance_criteria,
            constraints=constraints,
            allowed_changes=allowed_changes,
            out_of_scope=out_of_scope,
            assumptions=assumptions,
            risks=risks,
            open_questions=open_questions,
            research_notes=research_notes,
            sources=sources,
            confidence=confidence,
        )


@dataclass(frozen=True)
class ClarifyDecision:
    type: ClarifyDecisionType
    question: ClarifyQuestion | None = None
    result: ClarifyResult | None = None
    reason: str | None = None


@dataclass
class ClarifyRun:
    original_task: str
    status: ClarifyStatus
    repo_context_summary: str
    questions: list[ClarifyQuestion] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    result: ClarifyResult | None = None
    blocked_reason: str | None = None


class ClarifyAgent(Protocol):
    def decide(
        self,
        task: str,
        *,
        cwd: Path,
        answers: list[str],
        repo_context_summary: str,
    ) -> ClarifyDecision:
        ...


class DeterministicClarifyAgent:
    """Safe fallback for deterministic tests and fake-adapter workflow runs."""

    def decide(
        self,
        task: str,
        *,
        cwd: Path,
        answers: list[str],
        repo_context_summary: str,
    ) -> ClarifyDecision:
        return ClarifyDecision(
            type="complete",
            result=ClarifyResult.from_task(
                task,
                assumptions=("Clarify completed without asking user questions.",),
                confidence=0.6,
            ),
        )


class LLMClarifyAgent:
    """Clarify agent that may inspect the repo through read-only tools."""

    def __init__(
        self,
        *,
        adapter: LLMAdapter,
        max_model_turns: int = DEFAULT_MAX_CLARIFY_MODEL_TURNS,
    ) -> None:
        self.adapter = adapter
        self.max_model_turns = max_model_turns

    def decide(
        self,
        task: str,
        *,
        cwd: Path,
        answers: list[str],
        repo_context_summary: str,
    ) -> ClarifyDecision:
        messages = self._initial_messages(task, answers, repo_context_summary)
        tools = read_only_clarify_tools()
        safety_policy = SafetyPolicy(profile=PermissionProfile.READ_ONLY)

        for _ in range(self.max_model_turns):
            try:
                output = self.adapter.call(messages, tools)
            except LLMAdapterError as exc:
                return ClarifyDecision(type="blocked", reason=f"Clarify LLM failed: {exc}")

            if output["type"] == "final_answer":
                return clarify_decision_from_json(output["answer"], original_task=task)

            tool_name = output["tool_name"]
            arguments = output["arguments"]
            messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_name": tool_name,
                    "arguments": arguments,
                }
            )
            spec = tools.get(tool_name)
            if spec is None:
                result: ToolResult = {
                    "tool_name": tool_name,
                    "ok": False,
                    "result": {},
                    "error": f"Tool is not allowed in clarify phase: {tool_name}",
                }
            else:
                decision = safety_policy.check_tool_call(spec, arguments, cwd)
                if decision.allowed:
                    result = run_tool(tool_name, arguments, cwd)
                else:
                    result = {
                        "tool_name": tool_name,
                        "ok": False,
                        "result": {},
                        "error": decision.reason,
                    }
            messages.append(_format_tool_observation(result))

        return ClarifyDecision(
            type="blocked",
            reason=f"Clarify model exceeded {self.max_model_turns} model turns.",
        )

    def _initial_messages(
        self,
        task: str,
        answers: list[str],
        repo_context_summary: str,
    ) -> list[Message]:
        rendered_answers = "\n".join(
            f"{index}. {answer}" for index, answer in enumerate(answers, start=1)
        ) or "(none)"
        return [
            {
                "role": "system",
                "content": (
                    "You are the OpenCAI Workflow Clarify Agent. "
                    "You are a runtime clarify gate, not a general assistant. "
                    "Use only read-only repo and public web research tools when inspection is necessary. "
                    "Use repo tools for current project facts. "
                    "Use web tools only for external APIs, official docs, current public information, "
                    "industry conventions, or explicit external references that the repo cannot answer. "
                    "Prefer primary sources. Do not access private, logged-in, paywalled, or untrusted local resources. "
                    "Return only JSON. Do not use markdown fences. "
                    "You may return exactly one of these shapes: "
                    '{"type":"ask_question","question":{"question":"...","reason":"...",'
                    '"impact_if_unanswered":"...","default_assumption":"..."}} '
                    'or {"type":"complete","result":{"refined_task":"...",'
                    '"acceptance_criteria":[],"constraints":[],"allowed_changes":[],'
                    '"out_of_scope":[],"assumptions":[],"risks":[],"open_questions":[],'
                    '"research_notes":[],"sources":[],'
                    '"confidence":0.0}} '
                    'or {"type":"blocked","reason":"..."}. '
                    "Ask at most one necessary user question. "
                    "Ask only when the answer changes execution correctness."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Original task:\n"
                    f"{task}\n\n"
                    "Repo context summary:\n"
                    f"{repo_context_summary}\n\n"
                    "Previous user answers:\n"
                    f"{rendered_answers}"
                ),
            },
        ]


class ClarifyPhaseRunner:
    """Runs the clarify ask-user loop until complete, blocked, or max rounds."""

    def __init__(
        self,
        *,
        agent: ClarifyAgent,
        answer_provider: AnswerProvider | None = None,
        max_rounds: int = DEFAULT_MAX_CLARIFY_ROUNDS,
    ) -> None:
        self.agent = agent
        self.answer_provider = answer_provider or _prompt_for_answer
        self.max_rounds = max_rounds

    def run(self, task: str, *, cwd: Path) -> ClarifyRun:
        repo_context_summary = collect_clarify_repo_context(cwd)
        questions: list[ClarifyQuestion] = []
        answers: list[str] = []

        while True:
            decision = self.agent.decide(
                task,
                cwd=cwd,
                answers=list(answers),
                repo_context_summary=repo_context_summary,
            )
            if decision.type == "complete":
                if decision.result is None:
                    return ClarifyRun(
                        original_task=task,
                        status="blocked",
                        repo_context_summary=repo_context_summary,
                        questions=questions,
                        answers=answers,
                        blocked_reason="Clarify complete decision did not include a result.",
                    )
                return ClarifyRun(
                    original_task=task,
                    status="complete",
                    repo_context_summary=repo_context_summary,
                    questions=questions,
                    answers=answers,
                    result=decision.result,
                )

            if decision.type == "blocked":
                return ClarifyRun(
                    original_task=task,
                    status="blocked",
                    repo_context_summary=repo_context_summary,
                    questions=questions,
                    answers=answers,
                    blocked_reason=decision.reason or "Clarify blocked.",
                )

            if decision.question is None:
                return ClarifyRun(
                    original_task=task,
                    status="blocked",
                    repo_context_summary=repo_context_summary,
                    questions=questions,
                    answers=answers,
                    blocked_reason="Clarify ask_question decision did not include a question.",
                )

            if len(questions) >= self.max_rounds:
                return ClarifyRun(
                    original_task=task,
                    status="blocked",
                    repo_context_summary=repo_context_summary,
                    questions=questions,
                    answers=answers,
                    blocked_reason=f"Clarify reached max clarify rounds: {self.max_rounds}.",
                )

            questions.append(decision.question)
            answer = self.answer_provider(decision.question).strip()
            if not answer and decision.question.default_assumption:
                answer = decision.question.default_assumption
            answers.append(answer)


def render_clarify_run(run: ClarifyRun) -> str:
    lines = [
        format_output_title(f"Clarify status: {run.status}"),
        f"questions: {len(run.questions)}",
    ]
    if run.result is not None:
        lines.append(f"refined_task: {run.result.refined_task}")
        if run.result.acceptance_criteria:
            lines.append("acceptance_criteria:")
            lines.extend(f"- {item}" for item in run.result.acceptance_criteria)
        if run.result.assumptions:
            lines.append("assumptions:")
            lines.extend(f"- {item}" for item in run.result.assumptions)
    if run.blocked_reason:
        lines.append(f"blocked_reason: {run.blocked_reason}")
    return "\n".join(lines)


def collect_clarify_repo_context(cwd: Path) -> str:
    entries: list[str] = []
    for relative in ("README.md", "AGENTS.md", "docs/status.md", "docs/roadmap.md"):
        path = cwd / relative
        if path.exists():
            entries.append(relative)
    if not entries:
        return f"cwd: {cwd}\nNo standard repo context files were found."
    return f"cwd: {cwd}\nFound context files: " + ", ".join(entries)


def read_only_clarify_tools() -> dict[str, ToolSpec]:
    names = (
        "read_file",
        "list_files",
        "glob_files",
        "search_files",
        "web_search",
        "web_fetch",
        "web_extract",
    )
    all_tools = {**FILE_TOOLS, **SEARCH_TOOLS, **WEB_TOOLS}
    return {name: all_tools[name] for name in names}


def clarify_decision_from_json(text: str, *, original_task: str) -> ClarifyDecision:
    try:
        raw = json.loads(_strip_json_wrapper(text))
    except json.JSONDecodeError as exc:
        return ClarifyDecision(type="blocked", reason=f"Clarify returned invalid JSON: {exc}")
    if not isinstance(raw, dict):
        return ClarifyDecision(type="blocked", reason="Clarify JSON must be an object.")

    decision_type = raw.get("type")
    if decision_type == "ask_question":
        question = raw.get("question")
        if not isinstance(question, dict):
            return ClarifyDecision(type="blocked", reason="Clarify question must be an object.")
        try:
            return ClarifyDecision(
                type="ask_question",
                question=ClarifyQuestion(
                    question=_required_string(question, "question"),
                    reason=_required_string(question, "reason"),
                    impact_if_unanswered=_required_string(question, "impact_if_unanswered"),
                    default_assumption=_optional_string(question.get("default_assumption")),
                ),
            )
        except ValueError as exc:
            return ClarifyDecision(type="blocked", reason=str(exc))

    if decision_type == "complete":
        result = raw.get("result")
        if not isinstance(result, dict):
            return ClarifyDecision(type="blocked", reason="Clarify result must be an object.")
        try:
            return ClarifyDecision(
                type="complete",
                result=ClarifyResult(
                    original_task=original_task,
                    refined_task=_required_string(result, "refined_task"),
                    acceptance_criteria=_string_tuple(result.get("acceptance_criteria", [])),
                    constraints=_string_tuple(result.get("constraints", [])),
                    allowed_changes=_string_tuple(result.get("allowed_changes", [])),
                    out_of_scope=_string_tuple(result.get("out_of_scope", [])),
                    assumptions=_string_tuple(result.get("assumptions", [])),
                    risks=_string_tuple(result.get("risks", [])),
                    open_questions=_string_tuple(result.get("open_questions", [])),
                    research_notes=_string_tuple(result.get("research_notes", [])),
                    sources=_string_tuple(result.get("sources", [])),
                    confidence=_confidence(result.get("confidence")),
                ),
            )
        except ValueError as exc:
            return ClarifyDecision(type="blocked", reason=str(exc))

    if decision_type == "blocked":
        return ClarifyDecision(
            type="blocked",
            reason=_optional_string(raw.get("reason")) or "Clarify blocked.",
        )

    return ClarifyDecision(type="blocked", reason=f"Unsupported clarify decision type: {decision_type}")


def _format_tool_observation(result: ToolResult) -> Message:
    if not result["ok"]:
        return {
            "role": "tool",
            "content": f"Tool {result['tool_name']} failed.\nError: {result['error']}",
            "tool_name": result["tool_name"],
            "tool_result": result["result"],
            "tool_error": result["error"],
        }

    tool_payload = result["result"]
    if "content" in tool_payload and isinstance(tool_payload["content"], str):
        content = tool_payload["content"]
    else:
        content = json.dumps(tool_payload, ensure_ascii=False, indent=2, default=str)
    if len(content) > 1000:
        content = content[:1000].rstrip() + "\n\n[truncated]"
    path = result["result"].get("path", "")
    return {
        "role": "tool",
        "content": f"Tool {result['tool_name']} succeeded.\nPath: {path}\nContent:\n{content}",
        "tool_name": result["tool_name"],
        "tool_result": result["result"],
        "tool_error": result["error"],
    }


def _prompt_for_answer(question: ClarifyQuestion) -> str:
    print("Clarify:")
    print(question.question)
    print(f"Reason: {question.reason}")
    if question.default_assumption:
        print(f"Default assumption: {question.default_assumption}")
    return input("Answer: ")


def _strip_json_wrapper(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def _required_string(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Clarify JSON requires string field: {key}")
    return value.strip()


def _optional_string(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        return ""
    return value.strip()


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        return ()
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


def _confidence(value: object) -> float:
    if isinstance(value, int | float):
        return min(1.0, max(0.0, float(value)))
    return 0.5
