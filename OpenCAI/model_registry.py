"""Runtime-level model profile and adapter registry."""

from __future__ import annotations

from dataclasses import dataclass, field

from OpenCAI.llm_adapter import LLMAdapter


class ModelRegistryError(Exception):
    """Raised when a model profile cannot be registered or resolved."""


def model_profile_id(provider: str, model: str) -> str:
    return f"{provider}/{model}"


@dataclass(frozen=True)
class ModelProfile:
    id: str
    provider: str
    model: str
    label: str = ""
    config: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ModelRegistryError("Model profile id must be non-empty.")
        if not self.provider.strip():
            raise ModelRegistryError("Model profile provider must be non-empty.")
        if not self.model.strip():
            raise ModelRegistryError("Model profile model must be non-empty.")
        for key, value in self.config.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ModelRegistryError("Model profile config keys and values must be strings.")


class ModelRegistry:
    """Register available model profiles and resolve them to LLM adapters."""

    def __init__(self) -> None:
        self._profiles: dict[str, ModelProfile] = {}
        self._adapters: dict[str, LLMAdapter] = {}

    def register(self, profile: ModelProfile, adapter: LLMAdapter) -> None:
        if profile.id in self._profiles:
            raise ModelRegistryError(f"Model profile already registered: {profile.id}")

        self._profiles[profile.id] = profile
        self._adapters[profile.id] = adapter

    def resolve(self, model_id: str) -> LLMAdapter:
        try:
            return self._adapters[model_id]
        except KeyError as exc:
            raise ModelRegistryError(f"Unknown model profile: {model_id}") from exc

    def profile(self, model_id: str) -> ModelProfile:
        try:
            return self._profiles[model_id]
        except KeyError as exc:
            raise ModelRegistryError(f"Unknown model profile: {model_id}") from exc

    def profiles(self) -> tuple[ModelProfile, ...]:
        return tuple(self._profiles.values())
