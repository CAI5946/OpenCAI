from __future__ import annotations

import unittest

from OpenCAI.model_registry import ModelRegistryError
from OpenCAI.model_setup import build_default_model_profile, next_profile_id


class ModelSetupTests(unittest.TestCase):
    def test_builds_default_openai_profile_without_user_fields(self) -> None:
        profile = build_default_model_profile("openai", ("openai",))

        self.assertEqual(profile.id, "openai/gpt-4o-mini")
        self.assertEqual(profile.provider, "openai")
        self.assertEqual(profile.model, "gpt-4o-mini")
        self.assertEqual(profile.label, "OpenAI gpt-4o-mini")
        self.assertEqual(profile.config["api_key_env"], "OPENAI_API_KEY")
        self.assertEqual(profile.config["base_url"], "https://api.openai.com/v1")

    def test_openai_compatible_requires_model_name(self) -> None:
        with self.assertRaisesRegex(ModelRegistryError, "Model name is required"):
            build_default_model_profile("openai-compatible", ())

    def test_openai_compatible_requires_base_url(self) -> None:
        with self.assertRaisesRegex(ModelRegistryError, "Base URL is required"):
            build_default_model_profile("openai-compatible", (), model="custom-model")

    def test_openai_compatible_accepts_required_fields(self) -> None:
        profile = build_default_model_profile(
            "openai-compatible",
            (),
            model="custom-model",
            base_url="https://example.com/v1",
        )

        self.assertEqual(profile.id, "openai-compatible/custom-model")
        self.assertEqual(profile.model, "custom-model")
        self.assertEqual(profile.config["base_url"], "https://example.com/v1")

    def test_next_profile_id_uses_first_available_suffix(self) -> None:
        self.assertEqual(
            next_profile_id("openai", "gpt-4o-mini", ("openai/gpt-4o-mini", "openai/gpt-4o-mini-2")),
            "openai/gpt-4o-mini-3",
        )


if __name__ == "__main__":
    unittest.main()
