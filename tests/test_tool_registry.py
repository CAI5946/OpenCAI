from __future__ import annotations

import unittest

from OpenCAI.tooling.registry import DEFAULT_REGISTRY, ToolExposure, ToolRegistry
from OpenCAI.tools import TOOLS


class ToolRegistryTests(unittest.TestCase):
    def test_default_registry_contains_core_claude_style_tool_groups(self) -> None:
        expected = {
            "read_file",
            "write_file",
            "edit_file",
            "apply_patch",
            "list_files",
            "glob_files",
            "search_files",
            "run_command",
            "update_plan",
            "web_fetch",
            "invoke_skill",
        }

        self.assertTrue(expected.issubset(TOOLS))
        self.assertIs(DEFAULT_REGISTRY.get("read_file"), TOOLS["read_file"])

    def test_registry_can_filter_direct_deferred_and_hidden_tools(self) -> None:
        registry = ToolRegistry(TOOLS.values())

        direct = registry.visible_tools(exposure=ToolExposure.DIRECT)
        deferred = registry.visible_tools(exposure=ToolExposure.DEFERRED)

        self.assertIn("read_file", direct)
        self.assertNotIn("call_external_tool", direct)
        self.assertIn("call_external_tool", deferred)


if __name__ == "__main__":
    unittest.main()
