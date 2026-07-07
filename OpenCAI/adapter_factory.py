"""Build LLM adapters from runtime model profiles."""

from __future__ import annotations

import os

from OpenCAI.llm_adapter import FakeLLMAdapter, GeminiAdapter, LLMAdapter, LLMAdapterError
from OpenCAI.model_registry import ModelProfile, model_profile_id
from OpenCAI.provider_adapters import AnthropicAdapter, OllamaAdapter, OpenAICompatibleAdapter


DEFAULT_API_KEY_ENVS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openai-compatible": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def profile_from_adapter_name(adapter_name: str) -> ModelProfile:
    """Build a backwards-compatible model profile for legacy adapter names."""
    if "/" in adapter_name:
        provider, model = adapter_name.split("/", 1)
        if not provider or not model:
            raise LLMAdapterError(f"Unknown adapter: {adapter_name}")
        label = f"{provider} {model}"
        return ModelProfile(id=model_profile_id(provider, model), provider=provider, model=model, label=label)
    if adapter_name == "fake":
        return ModelProfile(id="fake/fake", provider="fake", model="fake", label="Fake")
    if adapter_name == "gemini":
        return ModelProfile(
            id="gemini/gemini-2.5-flash",
            provider="gemini",
            model="gemini-2.5-flash",
            label="Gemini 2.5 Flash",
        )
    if adapter_name == "openai":
        return ModelProfile(
            id="openai/gpt-4o-mini",
            provider="openai",
            model="gpt-4o-mini",
            label="OpenAI",
        )
    if adapter_name == "anthropic":
        return ModelProfile(
            id="anthropic/claude-sonnet-4-5",
            provider="anthropic",
            model="claude-sonnet-4-5",
            label="Anthropic Claude",
        )
    if adapter_name == "ollama":
        return ModelProfile(
            id="ollama/llama3.1",
            provider="ollama",
            model="llama3.1",
            label="Ollama local",
        )
    if adapter_name == "deepseek":
        return ModelProfile(
            id="deepseek/deepseek-chat",
            provider="deepseek",
            model="deepseek-chat",
            label="DeepSeek",
            config={"base_url": "https://api.deepseek.com"},
        )
    raise LLMAdapterError(f"Unknown adapter: {adapter_name}")


class AdapterFactory:
    """Create concrete LLMAdapter instances from model profiles."""

    def build(self, profile: ModelProfile, api_key: str | None) -> LLMAdapter:
        if profile.provider == "fake":
            return FakeLLMAdapter()
        if profile.provider == "gemini":
            return GeminiAdapter(_api_key(profile, api_key), model=profile.model)
        if profile.provider == "openai":
            return OpenAICompatibleAdapter(
                _api_key(profile, api_key),
                model=profile.model,
                base_url=profile.config.get("base_url", "https://api.openai.com/v1"),
            )
        if profile.provider == "openai-compatible":
            return OpenAICompatibleAdapter(
                _api_key(profile, api_key),
                model=profile.model,
                base_url=profile.config.get("base_url", "https://api.openai.com/v1"),
            )
        if profile.provider == "deepseek":
            return OpenAICompatibleAdapter(
                _api_key(profile, api_key),
                model=profile.model,
                base_url=profile.config.get("base_url", "https://api.deepseek.com"),
            )
        if profile.provider == "anthropic":
            max_tokens = int(profile.config.get("max_tokens", "4096"))
            return AnthropicAdapter(
                _api_key(profile, api_key),
                model=profile.model,
                base_url=profile.config.get("base_url", "https://api.anthropic.com"),
                max_tokens=max_tokens,
            )
        if profile.provider == "ollama":
            return OllamaAdapter(
                model=profile.model,
                base_url=profile.config.get("base_url", "http://localhost:11434"),
            )

        raise LLMAdapterError(f"Unknown model provider: {profile.provider}")


def _api_key(profile: ModelProfile, explicit_api_key: str | None) -> str:
    if explicit_api_key:
        return explicit_api_key
    env_name = profile.config.get("api_key_env") or DEFAULT_API_KEY_ENVS.get(profile.provider, "")
    return os.environ.get(env_name, "") if env_name else ""
