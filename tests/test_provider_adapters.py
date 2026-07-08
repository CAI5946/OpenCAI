from __future__ import annotations

import unittest
from unittest.mock import patch

from OpenCAI.llm_adapter import LLMAdapterError, Message
from OpenCAI.provider_adapters import AnthropicAdapter, OllamaAdapter, OpenAICompatibleAdapter, _post_json
from OpenCAI.tools import ToolSpec


def noop_tool(arguments: dict[str, object], cwd: object) -> dict[str, object]:
    return {"tool_name": "lookup", "ok": True, "result": {}, "error": None}


TOOL = ToolSpec(
    name="lookup",
    description="Look up a value.",
    input_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    read_only=True,
    function=noop_tool,
)


class CapturePost:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, str], dict[str, object]]] = []

    def __call__(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append((url, headers, payload))
        return self.response


class ProviderAdapterTests(unittest.TestCase):
    def test_openai_compatible_posts_chat_completion_and_parses_final_answer(self) -> None:
        post = CapturePost({"choices": [{"message": {"content": "done"}}]})
        adapter = OpenAICompatibleAdapter(
            "secret",
            model="gpt-4o-mini",
            base_url="https://api.openai.com/v1",
            http_post=post,
        )

        output = adapter.call([{"role": "user", "content": "hi"}], {"lookup": TOOL})

        self.assertEqual(output, {"type": "final_answer", "answer": "done"})
        url, headers, payload = post.calls[0]
        self.assertEqual(url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(headers["Authorization"], "Bearer secret")
        self.assertEqual(payload["model"], "gpt-4o-mini")
        self.assertEqual(payload["tools"][0]["function"]["name"], "lookup")

    def test_openai_compatible_parses_tool_call(self) -> None:
        post = CapturePost(
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "lookup",
                                        "arguments": '{"query": "README"}',
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        )
        adapter = OpenAICompatibleAdapter("secret", model="gpt-4o-mini", http_post=post)

        output = adapter.call([{"role": "user", "content": "hi"}], {"lookup": TOOL})

        self.assertEqual(
            output,
            {"type": "tool_call", "tool_name": "lookup", "arguments": {"query": "README"}},
        )

    def test_anthropic_posts_messages_request_and_parses_tool_use(self) -> None:
        post = CapturePost(
            {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "lookup",
                        "input": {"query": "README"},
                    }
                ]
            }
        )
        adapter = AnthropicAdapter(
            "secret",
            model="claude-sonnet-4-5",
            http_post=post,
        )

        output = adapter.call(
            [
                {"role": "system", "content": "system rules"},
                {"role": "user", "content": "hi"},
            ],
            {"lookup": TOOL},
        )

        self.assertEqual(
            output,
            {"type": "tool_call", "tool_name": "lookup", "arguments": {"query": "README"}},
        )
        url, headers, payload = post.calls[0]
        self.assertEqual(url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(headers["x-api-key"], "secret")
        self.assertEqual(payload["system"], "system rules")
        self.assertEqual(payload["tools"][0]["input_schema"], TOOL.input_schema)

    def test_ollama_posts_local_chat_request_and_parses_final_answer(self) -> None:
        post = CapturePost({"message": {"content": "done"}})
        adapter = OllamaAdapter(model="llama3.1", http_post=post)

        output = adapter.call([{"role": "user", "content": "hi"}], {"lookup": TOOL})

        self.assertEqual(output, {"type": "final_answer", "answer": "done"})
        url, headers, payload = post.calls[0]
        self.assertEqual(url, "http://localhost:11434/api/chat")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(payload["stream"], False)
        self.assertEqual(payload["tools"][0]["function"]["name"], "lookup")

    def test_openai_compatible_rejects_malformed_response(self) -> None:
        adapter = OpenAICompatibleAdapter(
            "secret",
            model="gpt-4o-mini",
            http_post=CapturePost({"choices": []}),
        )

        with self.assertRaisesRegex(LLMAdapterError, "must contain choices"):
            adapter.call([{"role": "user", "content": "hi"}], {})

    def test_post_json_wraps_timeout_error(self) -> None:
        with patch("OpenCAI.provider_adapters.request.urlopen", side_effect=TimeoutError):
            with self.assertRaisesRegex(LLMAdapterError, "Provider request timed out"):
                _post_json("https://example.test", {}, {})


if __name__ == "__main__":
    unittest.main()
