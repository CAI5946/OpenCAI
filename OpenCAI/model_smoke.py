"""Small model connectivity smoke checks."""

from __future__ import annotations

from dataclasses import dataclass

from OpenCAI.llm_adapter import LLMAdapter, LLMAdapterError, Message


SMOKE_PROMPT = "Reply with exactly: ok"


@dataclass(frozen=True)
class ModelSmokeResult:
    ok: bool
    output_type: str = ""
    error: str = ""


def run_model_smoke(adapter: LLMAdapter) -> ModelSmokeResult:
    messages: list[Message] = [{"role": "user", "content": SMOKE_PROMPT}]
    try:
        output = adapter.call(messages, tools={})
    except LLMAdapterError as exc:
        return ModelSmokeResult(ok=False, error=str(exc))

    output_type = output.get("type", "")
    if output_type in {"final_answer", "tool_call"}:
        return ModelSmokeResult(ok=True, output_type=output_type)
    return ModelSmokeResult(ok=False, error="Model returned invalid output type.")
