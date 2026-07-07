from __future__ import annotations

import unittest
from unittest.mock import patch

from OpenCAI.__main__ import build_adapter
from OpenCAI.adapter_factory import AdapterFactory, profile_from_adapter_name
from OpenCAI.llm_adapter import FakeLLMAdapter, LLMAdapterError
from OpenCAI.model_registry import ModelProfile
from OpenCAI.provider_adapters import AnthropicAdapter, OllamaAdapter, OpenAICompatibleAdapter


class AdapterFactoryTests(unittest.TestCase):
    def test_builds_fake_adapter_from_fake_profile(self) -> None:
        adapter = AdapterFactory().build(
            ModelProfile(id="fake", provider="fake", model="fake"),
            api_key=None,
        )

        self.assertIsInstance(adapter, FakeLLMAdapter)

    def test_builds_gemini_adapter_with_profile_model_name(self) -> None:
        profile = ModelProfile(
            id="gemini-pro",
            provider="gemini",
            model="gemini-2.5-pro",
        )

        with patch("OpenCAI.adapter_factory.GeminiAdapter") as gemini_adapter:
            adapter = AdapterFactory().build(profile, api_key="secret")

        self.assertIs(adapter, gemini_adapter.return_value)
        gemini_adapter.assert_called_once_with("secret", model="gemini-2.5-pro")

    def test_builds_google_adapter_with_gemini_adapter(self) -> None:
        profile = ModelProfile(
            id="google/gemini-dynamic",
            provider="google",
            model="gemini-dynamic",
        )

        with patch("OpenCAI.adapter_factory.GeminiAdapter") as gemini_adapter:
            adapter = AdapterFactory().build(profile, api_key="secret")

        self.assertIs(adapter, gemini_adapter.return_value)
        gemini_adapter.assert_called_once_with("secret", model="gemini-dynamic")

    def test_unknown_provider_has_clear_error(self) -> None:
        with self.assertRaisesRegex(LLMAdapterError, "Unknown model provider: missing"):
            AdapterFactory().build(
                ModelProfile(id="missing", provider="missing", model="missing"),
                api_key=None,
            )

    def test_builds_openai_adapter_from_openai_profile(self) -> None:
        adapter = AdapterFactory().build(
            ModelProfile(id="openai", provider="openai", model="gpt-4o-mini"),
            api_key="secret",
        )

        self.assertIsInstance(adapter, OpenAICompatibleAdapter)
        self.assertEqual(adapter.model, "gpt-4o-mini")
        self.assertEqual(adapter.base_url, "https://api.openai.com/v1")

    def test_builds_deepseek_adapter_with_deepseek_base_url(self) -> None:
        adapter = AdapterFactory().build(
            ModelProfile(id="deepseek", provider="deepseek", model="deepseek-chat"),
            api_key="secret",
        )

        self.assertIsInstance(adapter, OpenAICompatibleAdapter)
        self.assertEqual(adapter.base_url, "https://api.deepseek.com")

    def test_builds_glm_adapter_with_bigmodel_base_url(self) -> None:
        adapter = AdapterFactory().build(
            ModelProfile(id="glm/glm-dynamic", provider="glm", model="glm-dynamic"),
            api_key="secret",
        )

        self.assertIsInstance(adapter, OpenAICompatibleAdapter)
        self.assertEqual(adapter.model, "glm-dynamic")
        self.assertEqual(adapter.base_url, "https://open.bigmodel.cn/api/paas/v4")

    def test_builds_anthropic_and_ollama_adapters(self) -> None:
        anthropic = AdapterFactory().build(
            ModelProfile(id="anthropic", provider="anthropic", model="claude-sonnet-4-5"),
            api_key="secret",
        )
        ollama = AdapterFactory().build(
            ModelProfile(id="ollama", provider="ollama", model="llama3.1"),
            api_key=None,
        )

        self.assertIsInstance(anthropic, AnthropicAdapter)
        self.assertIsInstance(ollama, OllamaAdapter)

    def test_only_fake_legacy_adapter_name_maps_to_default_profile(self) -> None:
        fake = profile_from_adapter_name("fake")

        self.assertEqual((fake.id, fake.provider, fake.model), ("fake/fake", "fake", "fake"))

    def test_provider_model_ref_maps_to_profile(self) -> None:
        profile = profile_from_adapter_name("openai/gpt-4o-mini")

        self.assertEqual(profile.id, "openai/gpt-4o-mini")
        self.assertEqual(profile.provider, "openai")
        self.assertEqual(profile.model, "gpt-4o-mini")

    def test_unknown_legacy_adapter_name_has_clear_error(self) -> None:
        with self.assertRaisesRegex(LLMAdapterError, "Unknown adapter: missing"):
            profile_from_adapter_name("missing")

    def test_runtime_build_adapter_uses_provider_env_for_model_refs(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "openai-secret"}, clear=False):
            adapter = build_adapter("openai/gpt-dynamic", api_key="wrong-gemini-key")

        self.assertIsInstance(adapter, OpenAICompatibleAdapter)
        self.assertEqual(adapter.api_key, "openai-secret")
        self.assertEqual(adapter.model, "gpt-dynamic")


if __name__ == "__main__":
    unittest.main()
