"""Session-scoped model-visible context for OpenCAI."""

from __future__ import annotations

from dataclasses import dataclass, field

from OpenCAI.events import Event


DEFAULT_RECENT_TURNS_MAX = 3
DEFAULT_SESSION_CONTEXT_MAX_CHARS = 12000
DEFAULT_RUNNING_SUMMARY_MAX_CHARS = 4000


@dataclass(frozen=True)
class SessionTurnSummary:
    user_task: str
    final_answer: str
    tool_calls: tuple[str, ...] = ()
    invoked_skills: tuple[str, ...] = ()
    verification_results: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def render(self) -> str:
        lines = [
            f"user_task: {self.user_task}",
            f"final_answer: {self.final_answer or '(none)'}",
        ]
        if self.tool_calls:
            lines.append(f"tool_calls: {', '.join(self.tool_calls)}")
        if self.invoked_skills:
            lines.append(f"invoked_skills: {', '.join(self.invoked_skills)}")
        if self.verification_results:
            lines.append("verification:")
            lines.extend(f"- {result}" for result in self.verification_results)
        if self.errors:
            lines.append("errors:")
            lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


@dataclass
class SessionContext:
    running_summary: str = ""
    recent_turns: list[SessionTurnSummary] = field(default_factory=list)
    recent_turns_max: int = DEFAULT_RECENT_TURNS_MAX
    max_chars: int = DEFAULT_SESSION_CONTEXT_MAX_CHARS
    running_summary_max_chars: int = DEFAULT_RUNNING_SUMMARY_MAX_CHARS
    compact_count: int = 0

    def add_turn_events(self, events: list[Event]) -> None:
        summary = summarize_turn_events(events)
        if summary is None:
            return

        self.recent_turns.append(summary)
        while len(self.recent_turns) > self.recent_turns_max:
            oldest = self.recent_turns.pop(0)
            self._append_to_running_summary(oldest.render())

        self._enforce_budget()

    def render(self) -> str:
        if not self.running_summary and not self.recent_turns:
            return ""

        parts = [
            (
                f"<session_context compact_count=\"{self.compact_count}\" "
                f"recent_turns=\"{len(self.recent_turns)}\">"
            )
        ]
        if self.running_summary:
            parts.append("<running_summary>")
            parts.append(self.running_summary)
            parts.append("</running_summary>")
        if self.recent_turns:
            parts.append("<recent_turns>")
            for index, turn in enumerate(self.recent_turns, start=1):
                parts.append(f"<turn index=\"{index}\">")
                parts.append(turn.render())
                parts.append("</turn>")
            parts.append("</recent_turns>")
        parts.append("</session_context>")
        return "\n".join(parts)

    def _append_to_running_summary(self, text: str) -> None:
        self.compact_count += 1
        joined = "\n\n".join(part for part in [self.running_summary, text] if part)
        if len(joined) > self.running_summary_max_chars:
            joined = joined[-self.running_summary_max_chars :].lstrip()
        self.running_summary = joined

    def _enforce_budget(self) -> None:
        while len(self.render()) > self.max_chars and self.recent_turns:
            oldest = self.recent_turns.pop(0)
            self._append_to_running_summary(oldest.render())


def summarize_turn_events(events: list[Event]) -> SessionTurnSummary | None:
    user_task = ""
    final_answer = ""
    tool_calls: list[str] = []
    invoked_skills: list[str] = []
    verification_results: list[str] = []
    errors: list[str] = []

    for event in events:
        event_type = event["type"]
        data = event["data"]
        if event_type == "user_task":
            task = data.get("task")
            if isinstance(task, str):
                user_task = task
        elif event_type == "final_answer":
            answer = data.get("answer")
            if isinstance(answer, str):
                final_answer = answer
        elif event_type == "tool_call":
            tool_name = data.get("tool_name")
            if isinstance(tool_name, str):
                tool_calls.append(tool_name)
        elif event_type == "tool_result":
            tool_name = data.get("tool_name")
            result = data.get("result")
            if tool_name == "invoke_skill" and isinstance(result, dict):
                skill = result.get("skill")
                if isinstance(skill, str):
                    invoked_skills.append(skill)
        elif event_type == "verification":
            command = data.get("command")
            ok = data.get("ok")
            if isinstance(command, str) and isinstance(ok, bool):
                status = "passed" if ok else "failed"
                verification_results.append(f"{status}: {command}")
        elif event_type in {"error", "stop"}:
            errors.append(event["message"])

    if not user_task and not final_answer and not tool_calls and not verification_results and not errors:
        return None

    return SessionTurnSummary(
        user_task=user_task,
        final_answer=final_answer,
        tool_calls=tuple(tool_calls),
        invoked_skills=tuple(invoked_skills),
        verification_results=tuple(verification_results),
        errors=tuple(errors),
    )
