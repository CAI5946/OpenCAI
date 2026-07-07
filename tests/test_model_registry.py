from __future__ import annotations

import unittest

from OpenCAI.llm_adapter import FakeLLMAdapter
from OpenCAI.model_registry import ModelProfile, ModelRegistry, ModelRegistryError


class ModelRegistryTests(unittest.TestCase):
    def test_registers_and_resolves_multiple_model_profiles(self) -> None:
        registry = ModelRegistry()
        fake_adapter = FakeLLMAdapter()
        gemini_adapter = FakeLLMAdapter()

        registry.register(
            ModelProfile(
                id="fake",
                provider="fake",
                model="fake",
                label="Local fake model",
            ),
            fake_adapter,
        )
        registry.register(
            ModelProfile(
                id="gemini-flash",
                provider="gemini",
                model="gemini-2.5-flash",
                label="Gemini Flash",
            ),
            gemini_adapter,
        )

        self.assertIs(registry.resolve("fake"), fake_adapter)
        self.assertIs(registry.resolve("gemini-flash"), gemini_adapter)
        self.assertEqual(
            [profile.id for profile in registry.profiles()],
            ["fake", "gemini-flash"],
        )

    def test_rejects_duplicate_profile_id(self) -> None:
        registry = ModelRegistry()
        profile = ModelProfile(id="fake", provider="fake", model="fake")

        registry.register(profile, FakeLLMAdapter())

        with self.assertRaisesRegex(ModelRegistryError, "already registered: fake"):
            registry.register(profile, FakeLLMAdapter())

    def test_unknown_model_id_has_clear_error(self) -> None:
        registry = ModelRegistry()

        with self.assertRaisesRegex(ModelRegistryError, "Unknown model profile: missing"):
            registry.resolve("missing")

    def test_profile_fields_must_be_non_empty(self) -> None:
        with self.assertRaisesRegex(ModelRegistryError, "id must be non-empty"):
            ModelProfile(id="", provider="fake", model="fake")

        with self.assertRaisesRegex(ModelRegistryError, "provider must be non-empty"):
            ModelProfile(id="fake", provider="", model="fake")

        with self.assertRaisesRegex(ModelRegistryError, "model must be non-empty"):
            ModelProfile(id="fake", provider="fake", model="")


if __name__ == "__main__":
    unittest.main()
