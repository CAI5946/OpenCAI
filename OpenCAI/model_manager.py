"""Lazy runtime model manager for registered profiles and adapter cache."""

from __future__ import annotations

from OpenCAI.adapter_factory import AdapterFactory
from OpenCAI.llm_adapter import LLMAdapter
from OpenCAI.model_registry import ModelProfile, ModelRegistryError


class ModelManager:
    """Register model profiles and build adapters lazily on first use."""

    def __init__(
        self,
        *,
        adapter_factory: AdapterFactory | None = None,
        api_key: str | None = None,
    ) -> None:
        self.adapter_factory = adapter_factory or AdapterFactory()
        self.api_key = api_key
        self._profiles: dict[str, ModelProfile] = {}
        self._adapters: dict[str, LLMAdapter] = {}

    def register_profile(self, profile: ModelProfile) -> None:
        if profile.id in self._profiles:
            raise ModelRegistryError(f"Model profile already registered: {profile.id}")
        self._profiles[profile.id] = profile

    def register_adapter(self, profile: ModelProfile, adapter: LLMAdapter) -> None:
        self.register_profile(profile)
        self._adapters[profile.id] = adapter

    def register(self, profile: ModelProfile, adapter: LLMAdapter) -> None:
        self.register_adapter(profile, adapter)

    def resolve(self, model_id: str) -> LLMAdapter:
        if model_id in self._adapters:
            return self._adapters[model_id]
        profile = self.profile(model_id)
        adapter = self.adapter_factory.build(profile, self.api_key)
        self._adapters[model_id] = adapter
        return adapter

    def profile(self, model_id: str) -> ModelProfile:
        try:
            return self._profiles[model_id]
        except KeyError as exc:
            raise ModelRegistryError(f"Unknown model profile: {model_id}") from exc

    def profiles(self) -> tuple[ModelProfile, ...]:
        return tuple(self._profiles.values())

    def has_adapter(self, model_id: str) -> bool:
        return model_id in self._adapters
