"""Minimal fake Agent Loop for the learning-first prototype."""

from __future__ import annotations

from pathlib import Path

from OpenCAI.events import Event, final_answer, make_event, tool_call, tool_result, user_task
from OpenCAI.llm_adapter import FakeLLMAdapter, LLMAdapter, LLMAdapterError, Message
from OpenCAI.tools import TOOLS, ToolResult, run_tool


def _format_observation(result: ToolResult, max_chars: int = 1000) -> Message:
    if not result["ok"]:
        return {
            "role": "tool",
            "content": f"Tool {result['tool_name']} failed.\nError: {result['error']}",
        }

    path = result["result"].get("path", "")
    content = result["result"].get("content", "")
    if not isinstance(content, str):
        content = repr(content)

    truncated = len(content) > max_chars
    preview = content[:max_chars].rstrip()
    if truncated:
        preview += "\n\n[truncated: use a narrower tool call if more context is needed.]"

    return {
        "role": "tool",
        "content": f"Tool {result['tool_name']} succeeded.\nPath: {path}\nContent:\n{preview}",
    }


def run_fake_loop(
    task: str,
    cwd: Path | None = None,
    max_steps: int = 3,
    adapter: LLMAdapter | None = None,
) -> list[Event]:
    """Run a fixed multi-step model -> tool -> observation loop without a real LLM."""
    events: list[Event] = []
    messages: list[Message] = [{"role": "user", "content": task}]
    llm_adapter = adapter or FakeLLMAdapter()
    seq = 1
    step = 0
    working_dir = cwd or Path.cwd()

    events.append(user_task(seq, task))
    seq += 1

    while step < max_steps:
        step += 1
        try:
            model_output = llm_adapter.call(messages, TOOLS)
        except LLMAdapterError as exc:
            events.append(
                make_event(
                    "error",
                    seq,
                    f"LLM adapter failed: {exc}",
                    {"step": step, "error": str(exc)},
                )
            )
            return events

        if model_output["type"] == "final_answer":
            events.append(final_answer(seq, model_output["answer"]))
            return events

        tool_name = model_output["tool_name"]
        arguments = model_output["arguments"]
        events.append(
            make_event(
                "assistant_step",
                seq,
                f"Fake model chose tool call: {tool_name}.",
                {"step": step, "max_steps": max_steps},
            )
        )
        seq += 1

        events.append(tool_call(seq, tool_name, arguments))
        seq += 1

        result = run_tool(tool_name, arguments, working_dir)
        events.append(
            tool_result(
                seq,
                result["tool_name"],
                result["ok"],
                result["result"],
                result["error"],
            )
        )
        seq += 1

        messages.append(_format_observation(result))

    events.append(final_answer(seq, "Fake loop stopped: max_steps reached."))

    return events
