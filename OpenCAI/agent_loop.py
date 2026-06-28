"""Minimal Agent Loop for the learning-first prototype."""

from __future__ import annotations

from pathlib import Path

from OpenCAI.events import Event, final_answer, make_event, tool_call, tool_result, user_task, verification
from OpenCAI.llm_adapter import FakeLLMAdapter, LLMAdapter, LLMAdapterError, Message
from OpenCAI.safety import SafetyPolicy
from OpenCAI.tools import TOOLS, ToolResult, run_tool


def _format_observation(result: ToolResult, max_chars: int = 1000) -> Message:
    if not result["ok"]:
        return {
            "role": "tool",
            "content": f"Tool {result['tool_name']} failed.\nError: {result['error']}",
            "tool_name": result["tool_name"],
            "tool_result": result["result"],
            "tool_error": result["error"],
        }

    if result["tool_name"] == "run_command":
        command_result = result["result"]
        command = command_result.get("command", "")
        exit_code = command_result.get("exit_code", "")
        stdout = command_result.get("stdout", "")
        stderr = command_result.get("stderr", "")
        return {
            "role": "tool",
            "content": (
                f"Tool run_command succeeded.\n"
                f"Command: {command}\n"
                f"Exit code: {exit_code}\n"
                f"Stdout:\n{stdout}\n"
                f"Stderr:\n{stderr}"
            ),
            "tool_name": result["tool_name"],
            "tool_result": result["result"],
            "tool_error": result["error"],
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
        "tool_name": result["tool_name"],
        "tool_result": result["result"],
        "tool_error": result["error"],
    }


def _verification_event_from_result(seq: int, result: ToolResult) -> Event | None:
    if result["tool_name"] != "run_command" or not result["ok"]:
        return None

    command_result = result["result"]
    command = command_result.get("command")
    exit_code = command_result.get("exit_code")
    stdout = command_result.get("stdout", "")
    stderr = command_result.get("stderr", "")

    if not isinstance(command, str) or not isinstance(exit_code, int):
        return None

    return verification(
        seq,
        command,
        exit_code,
        stdout if isinstance(stdout, str) else repr(stdout),
        stderr if isinstance(stderr, str) else repr(stderr),
    )


def run_agent_loop(
    task: str,
    cwd: Path | None = None,
    max_steps: int = 3,
    adapter: LLMAdapter | None = None,
    require_verification: bool = False,
    policy: SafetyPolicy | None = None,
) -> list[Event]:
    """Run a model -> tool -> observation loop with an injectable LLM adapter."""
    events: list[Event] = []
    messages: list[Message] = [{"role": "user", "content": task}]
    llm_adapter = adapter or FakeLLMAdapter()
    seq = 1
    step = 0
    working_dir = cwd or Path.cwd()
    last_verification_ok: bool | None = None
    safety_policy = policy or SafetyPolicy()

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
            if require_verification and last_verification_ok is not True:
                events.append(
                    make_event(
                        "error",
                        seq,
                        "Final answer rejected: verification has not passed.",
                        {
                            "step": step,
                            "require_verification": require_verification,
                            "last_verification_ok": last_verification_ok,
                        },
                    )
                )
                return events
            events.append(final_answer(seq, model_output["answer"]))
            return events

        tool_name = model_output["tool_name"]
        arguments = model_output["arguments"]
        messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_name": tool_name,
                "arguments": arguments,
            }
        )
        events.append(
            make_event(
                "assistant_step",
                seq,
                f"Model chose tool call: {tool_name}.",
                {"step": step, "max_steps": max_steps},
            )
        )
        seq += 1

        events.append(tool_call(seq, tool_name, arguments))
        seq += 1

        spec = TOOLS.get(tool_name)
        if spec is None:
            result = {
                "tool_name": tool_name,
                "ok": False,
                "result": {},
                "error": f"Unknown tool: {tool_name}",
            }
        else:
            decision = safety_policy.check_tool_call(spec, arguments, working_dir)
            if decision.allowed:
                result = run_tool(tool_name, arguments, working_dir)
            else:
                result = {
                    "tool_name": tool_name,
                    "ok": False,
                    "result": {},
                    "error": decision.reason,
                }
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

        verification_event = _verification_event_from_result(seq, result)
        if verification_event is not None:
            events.append(verification_event)
            last_verification_ok = verification_event["data"]["ok"]
            seq += 1

        messages.append(_format_observation(result))

    events.append(final_answer(seq, "Agent loop stopped: max_steps reached."))

    return events


def run_fake_loop(
    task: str,
    cwd: Path | None = None,
    max_steps: int = 3,
    adapter: LLMAdapter | None = None,
    require_verification: bool = False,
    policy: SafetyPolicy | None = None,
) -> list[Event]:
    """Backward-compatible alias for the original Phase 4 function name."""
    return run_agent_loop(
        task,
        cwd=cwd,
        max_steps=max_steps,
        adapter=adapter,
        require_verification=require_verification,
        policy=policy,
    )
