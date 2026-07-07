"""Load user-defined LLM model profiles from local config."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from OpenCAI.model_registry import ModelProfile, ModelRegistryError


DEFAULT_LLM_CONFIG_PATH = Path(".opencai") / "models.json"
LLM_CONFIG_ENV = "OPENCAI_MODELS_CONFIG"


def resolve_llm_config_path(project_root: Path) -> Path:
    configured_path = os.environ.get(LLM_CONFIG_ENV, "").strip()
    if configured_path:
        return Path(configured_path).expanduser()
    return project_root / DEFAULT_LLM_CONFIG_PATH


def load_model_profiles(path: Path) -> tuple[ModelProfile, ...]:
    if not path.exists():
        return ()

    try:
        raw_config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelRegistryError(f"Invalid model config JSON: {path}") from exc

    models = _models_from_config(raw_config, path)
    return tuple(_profile_from_config(item, path) for item in models)


def save_model_profile(path: Path, profile: ModelProfile) -> None:
    raw_config = _read_config_for_write(path)
    models = _models_from_config(raw_config, path)
    serialized = _profile_to_config(profile)

    for index, raw_profile in enumerate(models):
        if isinstance(raw_profile, dict) and raw_profile.get("id") == profile.id:
            models[index] = serialized
            break
    else:
        models.append(serialized)

    raw_config["models"] = models
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(raw_config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _models_from_config(raw_config: Any, path: Path) -> list[Any]:
    if not isinstance(raw_config, dict):
        raise ModelRegistryError(f"Model config must be a JSON object: {path}")
    models = raw_config.get("models", [])
    if not isinstance(models, list):
        raise ModelRegistryError("Model config field 'models' must be a list.")
    return models


def _read_config_for_write(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"models": []}

    try:
        raw_config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelRegistryError(f"Invalid model config JSON: {path}") from exc
    if not isinstance(raw_config, dict):
        raise ModelRegistryError(f"Model config must be a JSON object: {path}")
    return raw_config


def _profile_from_config(raw_profile: Any, path: Path) -> ModelProfile:
    if not isinstance(raw_profile, dict):
        raise ModelRegistryError(f"Model config entries must be objects: {path}")

    config = raw_profile.get("config", {})
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise ModelRegistryError("Model profile field 'config' must be an object.")

    normalized_config = {str(key): str(value) for key, value in config.items()}
    api_key_env = raw_profile.get("api_key_env")
    if api_key_env:
        normalized_config["api_key_env"] = str(api_key_env)
    base_url = raw_profile.get("base_url")
    if base_url:
        normalized_config["base_url"] = str(base_url)

    return ModelProfile(
        id=str(raw_profile.get("id", "")),
        provider=str(raw_profile.get("provider", "")),
        model=str(raw_profile.get("model", "")),
        label=str(raw_profile.get("label", "")),
        config=normalized_config,
    )


def _profile_to_config(profile: ModelProfile) -> dict[str, Any]:
    config = dict(profile.config)
    raw_profile: dict[str, Any] = {
        "id": profile.id,
        "provider": profile.provider,
        "model": profile.model,
    }
    if profile.label:
        raw_profile["label"] = profile.label
    if "api_key_env" in config:
        raw_profile["api_key_env"] = config.pop("api_key_env")
    if "base_url" in config:
        raw_profile["base_url"] = config.pop("base_url")
    if config:
        raw_profile["config"] = config
    return raw_profile
