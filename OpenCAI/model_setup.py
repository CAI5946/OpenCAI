"""Build user model profiles from provider defaults."""

from __future__ import annotations

from dataclasses import dataclass

from OpenCAI.model_registry import ModelProfile, ModelRegistryError


@dataclass(frozen=True)
class ProviderDefaults:
    provider: str
    model: str
    label_prefix: str
    api_key_env: str = ""
    base_url: str = ""
    requires_model: bool = False
    requires_base_url: bool = False


PROVIDER_DEFAULTS: dict[str, ProviderDefaults] = {
    "openai": ProviderDefaults(
        provider="openai",
        model="gpt-4o-mini",
        label_prefix="OpenAI",
        api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
    ),
    "anthropic": ProviderDefaults(
        provider="anthropic",
        model="claude-sonnet-4-5",
        label_prefix="Anthropic",
        api_key_env="ANTHROPIC_API_KEY",
        base_url="https://api.anthropic.com",
    ),
    "ollama": ProviderDefaults(
        provider="ollama",
        model="llama3.1",
        label_prefix="Ollama",
        base_url="http://localhost:11434",
    ),
    "deepseek": ProviderDefaults(
        provider="deepseek",
        model="deepseek-chat",
        label_prefix="DeepSeek",
        api_key_env="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com",
    ),
    "openai-compatible": ProviderDefaults(
        provider="openai-compatible",
        model="",
        label_prefix="OpenAI-compatible",
        api_key_env="OPENAI_API_KEY",
        requires_model=True,
        requires_base_url=True,
    ),
}

MODEL_ADD_PROVIDER_CHOICES = tuple(PROVIDER_DEFAULTS)


def build_default_model_profile(
    provider: str,
    existing_ids: tuple[str, ...],
    *,
    model: str = "",
    base_url: str = "",
) -> ModelProfile:
    try:
        defaults = PROVIDER_DEFAULTS[provider]
    except KeyError as exc:
        raise ModelRegistryError(f"Unknown model provider: {provider}") from exc

    resolved_model = model.strip() or defaults.model
    if not resolved_model:
        raise ModelRegistryError(f"Model name is required for provider: {provider}")

    config: dict[str, str] = {}
    if defaults.api_key_env:
        config["api_key_env"] = defaults.api_key_env
    resolved_base_url = base_url.strip() or defaults.base_url
    if defaults.requires_base_url and not resolved_base_url:
        raise ModelRegistryError(f"Base URL is required for provider: {provider}")
    if resolved_base_url:
        config["base_url"] = resolved_base_url

    profile_id = next_profile_id(provider, existing_ids)
    return ModelProfile(
        id=profile_id,
        provider=provider,
        model=resolved_model,
        label=f"{defaults.label_prefix} {resolved_model}",
        config=config,
    )


def next_profile_id(provider: str, existing_ids: tuple[str, ...]) -> str:
    existing = set(existing_ids)
    if provider not in existing:
        return provider

    index = 2
    while f"{provider}-{index}" in existing:
        index += 1
    return f"{provider}-{index}"
