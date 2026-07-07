"""Build LLM adapters from runtime model profiles."""

from __future__ import annotations

from OpenCAI.llm_adapter import FakeLLMAdapter, GeminiAdapter, LLMAdapter, LLMAdapterError
from OpenCAI.model_registry import ModelProfile


def profile_from_adapter_name(adapter_name: str) -> ModelProfile:
    """Build a backwards-compatible model profile for legacy adapter names."""
    if adapter_name == "fake":
        return ModelProfile(id="fake", provider="fake", model="fake", label="Fake")
    if adapter_name == "gemini":
        return ModelProfile(
            id="gemini",
            provider="gemini",
            model="gemini-2.5-flash",
            label="Gemini 2.5 Flash",
        )
    raise LLMAdapterError(f"Unknown adapter: {adapter_name}")


class AdapterFactory:
    """Create concrete LLMAdapter instances from model profiles."""

    def build(self, profile: ModelProfile, api_key: str | None) -> LLMAdapter:
        if profile.provider == "fake":
            return FakeLLMAdapter()
        if profile.provider == "gemini":
            return GeminiAdapter(api_key or "", model=profile.model)

        raise LLMAdapterError(f"Unknown model provider: {profile.provider}")
