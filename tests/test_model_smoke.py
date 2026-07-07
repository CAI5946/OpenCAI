from __future__ import annotations

import unittest

from OpenCAI.llm_adapter import LLMAdapterError, Message, ModelOutput
from OpenCAI.model_smoke import SMOKE_PROMPT, run_model_smoke
from OpenCAI.tools import ToolSpec


class FinalAnswerAdapter:
    def __init__(self) -> None:
        self.messages: list[Message] = []
        self.tools: dict[str, ToolSpec] = {}

    def call(self, messages: list[Message], tools: dict[str, ToolSpec]) -> ModelOutput:
        self.messages = messages
        self.tools = tools
        return {"type": "final_answer", "answer": "ok"}


class FailingAdapter:
    def call(self, messages: list[Message], tools: dict[str, ToolSpec]) -> ModelOutput:
        raise LLMAdapterError("boom")


class InvalidAdapter:
    def call(self, messages: list[Message], tools: dict[str, ToolSpec]) -> ModelOutput:
        return {"type": "unknown"}  # type: ignore[typeddict-item]


class ModelSmokeTests(unittest.TestCase):
    def test_smoke_calls_adapter_without_tools(self) -> None:
        adapter = FinalAnswerAdapter()

        result = run_model_smoke(adapter)

        self.assertTrue(result.ok)
        self.assertEqual(result.output_type, "final_answer")
        self.assertEqual(adapter.messages, [{"role": "user", "content": SMOKE_PROMPT}])
        self.assertEqual(adapter.tools, {})

    def test_smoke_reports_adapter_error(self) -> None:
        result = run_model_smoke(FailingAdapter())

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "boom")

    def test_smoke_rejects_invalid_output_type(self) -> None:
        result = run_model_smoke(InvalidAdapter())

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Model returned invalid output type.")


if __name__ == "__main__":
    unittest.main()
