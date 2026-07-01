from __future__ import annotations

import unittest

from OpenCAI.agent_loop import iter_agent_loop, run_agent_loop
from OpenCAI.llm_adapter import FakeLLMAdapter, Message, ModelOutput
from OpenCAI.tools import ToolSpec


class RecordingFinalAnswerAdapter:
    def __init__(self) -> None:
        self.call_count = 0
        self.messages: list[Message] = []

    def call(
        self,
        messages: list[Message],
        tools: dict[str, ToolSpec],
    ) -> ModelOutput:
        self.call_count += 1
        self.messages = list(messages)
        return {
            "type": "final_answer",
            "answer": "done",
        }


class AgentLoopStreamingTests(unittest.TestCase):
    def test_iter_agent_loop_yields_user_task_before_model_call(self) -> None:
        adapter = RecordingFinalAnswerAdapter()
        events = iter_agent_loop("Read README", adapter=adapter)

        first_event = next(events)

        self.assertEqual("user_task", first_event["type"])
        self.assertEqual(0, adapter.call_count)

    def test_run_agent_loop_remains_list_compatible_with_streaming_path(self) -> None:
        streamed_events = list(
            iter_agent_loop(
                "Read README",
                adapter=FakeLLMAdapter(),
                max_steps=3,
            )
        )
        batch_events = run_agent_loop(
            "Read README",
            adapter=FakeLLMAdapter(),
            max_steps=3,
        )

        self.assertEqual(streamed_events, batch_events)
        self.assertEqual(
            [event["type"] for event in streamed_events],
            ["user_task", "assistant_step", "tool_call", "tool_result", "final_answer"],
        )

    def test_iter_agent_loop_uses_initial_messages_when_provided(self) -> None:
        adapter = RecordingFinalAnswerAdapter()
        initial_messages: list[Message] = [
            {"role": "system", "content": "system rules"},
            {"role": "user", "content": "<project_instructions>project</project_instructions>"},
            {"role": "user", "content": "Read README"},
        ]

        events = list(
            iter_agent_loop(
                "Read README",
                adapter=adapter,
                initial_messages=initial_messages,
            )
        )

        self.assertEqual(events[0]["type"], "user_task")
        self.assertEqual(adapter.messages, initial_messages)


if __name__ == "__main__":
    unittest.main()
