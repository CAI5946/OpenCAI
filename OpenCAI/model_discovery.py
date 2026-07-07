"""Discover currently available provider models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib import request
from urllib.error import HTTPError, URLError

from OpenCAI.llm_adapter import LLMAdapterError


JsonGet = Callable[[str, dict[str, str]], dict[str, Any]]


@dataclass(frozen=True)
class DiscoveredModel:
    id: str
    label: str = ""
    provider: str = ""
    source: str = "api"


def list_provider_models(
    provider: str,
    *,
    api_key: str = "",
    base_url: str = "",
    http_get: JsonGet | None = None,
) -> tuple[DiscoveredModel, ...]:
    get_json = http_get or _get_json
    if provider == "openai":
        return _openai_models(api_key, base_url or "https://api.openai.com/v1", get_json)
    if provider == "anthropic":
        return _anthropic_models(api_key, base_url or "https://api.anthropic.com", get_json)
    if provider == "deepseek":
        return _openai_compatible_models(provider, api_key, base_url or "https://api.deepseek.com", get_json)
    if provider == "openai-compatible":
        return _openai_compatible_models(provider, api_key, base_url, get_json)
    if provider == "ollama":
        return _ollama_models(base_url or "http://localhost:11434", get_json)
    raise LLMAdapterError(f"Unknown model provider: {provider}")


def _openai_models(api_key: str, base_url: str, get_json: JsonGet) -> tuple[DiscoveredModel, ...]:
    _require_api_key(api_key, "OPENAI_API_KEY")
    response = get_json(
        f"{base_url.rstrip('/')}/models",
        {"Authorization": f"Bearer {api_key}"},
    )
    return _models_from_data_list("openai", response)


def _anthropic_models(api_key: str, base_url: str, get_json: JsonGet) -> tuple[DiscoveredModel, ...]:
    _require_api_key(api_key, "ANTHROPIC_API_KEY")
    response = get_json(
        f"{base_url.rstrip('/')}/v1/models",
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    return _models_from_data_list("anthropic", response)


def _openai_compatible_models(
    provider: str,
    api_key: str,
    base_url: str,
    get_json: JsonGet,
) -> tuple[DiscoveredModel, ...]:
    _require_api_key(api_key, "API key")
    if not base_url:
        raise LLMAdapterError("Missing model provider base_url")
    response = get_json(
        f"{base_url.rstrip('/')}/models",
        {"Authorization": f"Bearer {api_key}"},
    )
    return _models_from_data_list(provider, response)


def _ollama_models(base_url: str, get_json: JsonGet) -> tuple[DiscoveredModel, ...]:
    response = get_json(f"{base_url.rstrip('/')}/api/tags", {})
    raw_models = response.get("models")
    if not isinstance(raw_models, list):
        raise LLMAdapterError("Ollama models response must contain models list.")
    models: list[DiscoveredModel] = []
    for raw_model in raw_models:
        if not isinstance(raw_model, dict):
            continue
        name = raw_model.get("name")
        if isinstance(name, str) and name:
            models.append(DiscoveredModel(id=name, label=name, provider="ollama"))
    return tuple(models)


def _models_from_data_list(provider: str, response: dict[str, Any]) -> tuple[DiscoveredModel, ...]:
    raw_models = response.get("data")
    if not isinstance(raw_models, list):
        raise LLMAdapterError("Models response must contain data list.")
    models: list[DiscoveredModel] = []
    for raw_model in raw_models:
        if not isinstance(raw_model, dict):
            continue
        model_id = raw_model.get("id")
        if not isinstance(model_id, str) or not model_id:
            continue
        label = raw_model.get("display_name") if isinstance(raw_model.get("display_name"), str) else model_id
        models.append(DiscoveredModel(id=model_id, label=label, provider=provider))
    return tuple(models)


def _require_api_key(api_key: str, label: str) -> None:
    if not api_key:
        raise LLMAdapterError(f"Missing {label}")


def _get_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    req = request.Request(url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raise LLMAdapterError(f"Model discovery failed: HTTP {exc.code}") from exc
    except URLError as exc:
        raise LLMAdapterError(f"Model discovery failed: {type(exc).__name__}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMAdapterError("Model discovery response must be JSON.") from exc
    if not isinstance(parsed, dict):
        raise LLMAdapterError("Model discovery response JSON must be an object.")
    return parsed
