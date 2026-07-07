from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from OpenCAI.llm_config import (
    DEFAULT_LLM_CONFIG_PATH,
    LLM_CONFIG_ENV,
    load_model_profiles,
    resolve_llm_config_path,
    save_model_profile,
)
from OpenCAI.model_registry import ModelProfile, ModelRegistryError


class LLMConfigTests(unittest.TestCase):
    def test_missing_config_returns_no_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profiles = load_model_profiles(Path(temp_dir) / "missing.json")

        self.assertEqual(profiles, ())

    def test_loads_profiles_from_json_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "models.json"
            path.write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "id": "openai-fast",
                                "provider": "openai",
                                "model": "gpt-4o-mini",
                                "label": "OpenAI fast",
                                "api_key_env": "OPENAI_API_KEY",
                                "base_url": "https://api.openai.com/v1",
                                "config": {"timeout": "30"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            profiles = load_model_profiles(path)

        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].id, "openai-fast")
        self.assertEqual(profiles[0].provider, "openai")
        self.assertEqual(profiles[0].model, "gpt-4o-mini")
        self.assertEqual(profiles[0].label, "OpenAI fast")
        self.assertEqual(profiles[0].config["api_key_env"], "OPENAI_API_KEY")
        self.assertEqual(profiles[0].config["base_url"], "https://api.openai.com/v1")
        self.assertEqual(profiles[0].config["timeout"], "30")

    def test_rejects_invalid_config_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "models.json"
            path.write_text(json.dumps({"models": {}}), encoding="utf-8")

            with self.assertRaisesRegex(ModelRegistryError, "models' must be a list"):
                load_model_profiles(path)

    def test_saves_new_profile_to_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / ".opencai" / "models.json"

            save_model_profile(
                path,
                ModelProfile(
                    id="openai/gpt-4o-mini",
                    provider="openai",
                    model="gpt-4o-mini",
                    label="OpenAI gpt-4o-mini",
                    config={
                        "api_key_env": "OPENAI_API_KEY",
                        "base_url": "https://api.openai.com/v1",
                    },
                ),
            )

            profiles = load_model_profiles(path)

        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].id, "openai/gpt-4o-mini")
        self.assertEqual(profiles[0].config["api_key_env"], "OPENAI_API_KEY")

    def test_loads_provider_model_ref_when_id_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "models.json"
            path.write_text(
                json.dumps({"models": [{"provider": "openai", "model": "gpt-4o-mini"}]}),
                encoding="utf-8",
            )

            profiles = load_model_profiles(path)

        self.assertEqual(profiles[0].id, "openai/gpt-4o-mini")

    def test_save_profile_replaces_existing_profile_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "models.json"
            save_model_profile(path, ModelProfile(id="openai", provider="openai", model="old"))
            save_model_profile(path, ModelProfile(id="openai", provider="openai", model="new"))

            profiles = load_model_profiles(path)

        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].model, "new")

    def test_resolves_default_or_env_config_path(self) -> None:
        project_root = Path("project").resolve()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_llm_config_path(project_root), project_root / DEFAULT_LLM_CONFIG_PATH)

        with patch.dict(os.environ, {LLM_CONFIG_ENV: "custom-models.json"}, clear=True):
            self.assertEqual(resolve_llm_config_path(project_root), Path("custom-models.json"))


if __name__ == "__main__":
    unittest.main()
