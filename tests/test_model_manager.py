from __future__ import annotations

import unittest

from OpenCAI.llm_adapter import FakeLLMAdapter, LLMAdapter, ModelOutput
from OpenCAI.model_manager import ModelManager
from OpenCAI.model_registry import ModelProfile, ModelRegistryError
from OpenCAI.tools import ToolSpec


class RecordingFactory:
    def __init__(self) -> None:
        self.calls: list[tuple[ModelProfile, str | None]] = []

    def build(self, profile: ModelProfile, api_key: str | None) -> LLMAdapter:
        self.calls.append((profile, api_key))
        return FakeLLMAdapter()


class StaticAdapter:
    def call(self, messages: list[object], tools: dict[str, ToolSpec]) -> ModelOutput:
        return {"type": "final_answer", "answer": "done"}


class ModelManagerTests(unittest.TestCase):
    def test_resolve_builds_adapter_lazily_and_caches_it(self) -> None:
        factory = RecordingFactory()
        manager = ModelManager(adapter_factory=factory, api_key="secret")
        manager.register_profile(
            ModelProfile(id="gemini", provider="gemini", model="gemini-2.5-flash")
        )

        first = manager.resolve("gemini")
        second = manager.resolve("gemini")

        self.assertIs(first, second)
        self.assertEqual(len(factory.calls), 1)
        self.assertEqual(factory.calls[0][0].id, "gemini")
        self.assertEqual(factory.calls[0][1], "secret")

    def test_register_adapter_caches_existing_adapter_without_building(self) -> None:
        factory = RecordingFactory()
        manager = ModelManager(adapter_factory=factory)
        adapter = StaticAdapter()

        manager.register_adapter(
            ModelProfile(id="fake", provider="fake", model="fake"),
            adapter,
        )

        self.assertIs(manager.resolve("fake"), adapter)
        self.assertEqual(factory.calls, [])

    def test_unknown_profile_has_clear_error(self) -> None:
        manager = ModelManager()

        with self.assertRaisesRegex(ModelRegistryError, "Unknown model profile: missing"):
            manager.resolve("missing")

    def test_rejects_duplicate_profile_id(self) -> None:
        manager = ModelManager()
        profile = ModelProfile(id="fake", provider="fake", model="fake")
        manager.register_profile(profile)

        with self.assertRaisesRegex(ModelRegistryError, "already registered: fake"):
            manager.register_profile(profile)


if __name__ == "__main__":
    unittest.main()
