from __future__ import annotations

import unittest
from unittest.mock import patch

from OpenCAI.adapter_factory import AdapterFactory, profile_from_adapter_name
from OpenCAI.llm_adapter import FakeLLMAdapter, LLMAdapterError
from OpenCAI.model_registry import ModelProfile


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

    def test_unknown_provider_has_clear_error(self) -> None:
        with self.assertRaisesRegex(LLMAdapterError, "Unknown model provider: missing"):
            AdapterFactory().build(
                ModelProfile(id="missing", provider="missing", model="missing"),
                api_key=None,
            )

    def test_legacy_adapter_names_map_to_default_profiles(self) -> None:
        fake = profile_from_adapter_name("fake")
        gemini = profile_from_adapter_name("gemini")

        self.assertEqual((fake.id, fake.provider, fake.model), ("fake", "fake", "fake"))
        self.assertEqual(
            (gemini.id, gemini.provider, gemini.model),
            ("gemini", "gemini", "gemini-2.5-flash"),
        )

    def test_unknown_legacy_adapter_name_has_clear_error(self) -> None:
        with self.assertRaisesRegex(LLMAdapterError, "Unknown adapter: missing"):
            profile_from_adapter_name("missing")


if __name__ == "__main__":
    unittest.main()
