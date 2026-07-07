from __future__ import annotations

import unittest

from OpenCAI.llm_adapter import LLMAdapterError
from OpenCAI.model_discovery import list_provider_models


class ModelDiscoveryTests(unittest.TestCase):
    def test_lists_openai_models(self) -> None:
        calls: list[tuple[str, dict[str, str]]] = []

        models = list_provider_models(
            "openai",
            api_key="secret",
            http_get=lambda url, headers: calls.append((url, headers)) or {"data": [{"id": "gpt-x"}]},
        )

        self.assertEqual(models[0].id, "gpt-x")
        self.assertEqual(calls[0][0], "https://api.openai.com/v1/models")
        self.assertEqual(calls[0][1]["Authorization"], "Bearer secret")

    def test_lists_anthropic_models(self) -> None:
        models = list_provider_models(
            "anthropic",
            api_key="secret",
            http_get=lambda _url, _headers: {"data": [{"id": "claude-x", "display_name": "Claude X"}]},
        )

        self.assertEqual(models[0].id, "claude-x")
        self.assertEqual(models[0].label, "Claude X")

    def test_lists_ollama_models(self) -> None:
        models = list_provider_models(
            "ollama",
            http_get=lambda url, _headers: {"models": [{"name": "llama3.1:latest"}]},
        )

        self.assertEqual(models[0].id, "llama3.1:latest")

    def test_requires_key_for_remote_provider(self) -> None:
        with self.assertRaisesRegex(LLMAdapterError, "Missing OPENAI_API_KEY"):
            list_provider_models("openai")


if __name__ == "__main__":
    unittest.main()
